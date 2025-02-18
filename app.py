from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import sqlite3
import bcrypt
import os
from werkzeug.security import generate_password_hash


# Flask アプリケーションの作成
app = Flask(__name__)
app.secret_key = os.urandom(24)

# データベース接続を行う関数
def get_db_connection():
    conn = sqlite3.connect('cafe_app.db')
    conn.row_factory = sqlite3.Row
    return conn

# ログイン必須デコレーター
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('register_user'))
        return f(*args, **kwargs)
    return decorated_function

# ホーム画面
@app.route('/')
@login_required
def index():
    return 'Welcome to Cafe App!'

# ユーザー登録・一覧表示
@app.route('/register_user', methods=['GET', 'POST'])
def register_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'staff')  # デフォルトは 'staff'
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 現在時刻を取得

        conn = get_db_connection()
        cursor = conn.cursor()

        # ユーザー名の重複チェック
        cursor.execute('SELECT * FROM User WHERE username = ?', (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return "このユーザー名は既に使用されています。", 400

        # ユーザーを登録（created_at 追加）
        cursor.execute('INSERT INTO User (username, password, role, created_at) VALUES (?, ?, ?, ?)', 
                       (username, hashed_password, role, created_at))
        conn.commit()

        # 登録したユーザー情報を取得
        cursor.execute('SELECT id, role FROM User WHERE username = ?', (username,))
        user = cursor.fetchone()
        user_id = user['id']
        user_role = user['role']

        conn.close()

        # ここでセッションにユーザー情報を保存（自動ログイン）
        session['user_id'] = user_id
        session['username'] = username
        session['role'] = user_role  # 役割もセッションに保存

        # 登録完了後に在庫一覧へリダイレクト
        return redirect(url_for('view_stock'))

    return render_template('register_user.html')

# ログイン
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM User WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
        
    return render_template('login.html')

# ログアウト
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ユーザー情報の編集
@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        new_username = request.form['username']
        new_password = request.form['password']
        new_role = request.form['role']

        # パスワードを更新する場合のみハッシュ化
        if new_password:
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute("UPDATE User SET username = ?, password = ?, role = ? WHERE id = ?", 
                           (new_username, hashed_password.decode('utf-8'), new_role, user_id))
        else:
            cursor.execute("UPDATE User SET username = ?, role = ? WHERE id = ?", 
                           (new_username, new_role, user_id))

        conn.commit()
        conn.close()
        return redirect(url_for('register_user'))

    cursor.execute("SELECT * FROM User WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    return render_template('edit_user.html', user=user)

# ユーザー削除
@app.route('/delete_user/<int:user_id>', methods=['GET'])
@login_required
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM User WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('register_user'))

# 商品登録
@app.route('/register', methods=['GET', 'POST'])
@login_required
def register_product():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        price = request.form['price']

        cursor.execute(
            "INSERT INTO Product (name, description, category, price) VALUES (?, ?, ?, ?)",
            (name, description, category, price)
        )
        product_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO Stock (product_id, quantity, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (product_id, 0)
        )

        conn.commit()

    cursor.execute("SELECT * FROM Product")
    products = cursor.fetchall()
    conn.close()

    return render_template('register_product.html', products=products)

# 在庫一覧
@app.route('/view_stock')
@login_required
def view_stock():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT Product.id AS product_id, Product.name, Product.category, Product.price, 
           COALESCE(Stock.quantity, 0) AS quantity
    FROM Product
    LEFT JOIN Stock ON Product.id = Stock.product_id
    ''')
    products = cursor.fetchall()
    conn.close()
    return render_template('view_stock.html', products=products)


# 在庫編集
@app.route('/edit_stock/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_stock(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        new_quantity = request.form['quantity']
        cursor.execute("UPDATE Stock SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ?",
                       (new_quantity, product_id))
        conn.commit()
        conn.close()
        return redirect(url_for('view_stock'))

    # 商品情報を取得（修正ポイント）
    cursor.execute('''
    SELECT Product.id AS product_id, Product.name, Product.category, Product.price, 
           COALESCE(Stock.quantity, 0) AS quantity
    FROM Product
    LEFT JOIN Stock ON Product.id = Stock.product_id
    WHERE Product.id = ?
    ''', (product_id,))
    
    product = cursor.fetchone()
    conn.close()

    # `product` が `None` の場合（存在しない商品ID）エラーページを返す
    if product is None:
        return "商品が見つかりません", 404

    return render_template('edit_stock.html', product=product)


@app.route('/delete_stock/<int:product_id>', methods=['GET'])
@login_required
def delete_stock(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM Stock WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('view_stock'))

# 取引履歴一覧の表示
@app.route('/transaction_list')
@login_required
def transaction_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT TransactionHistory.id, Product.name AS product_name, User.username AS user_name, 
               TransactionHistory.quantity, TransactionHistory.transaction_type, 
               TransactionHistory.transaction_date, TransactionHistory.notes
        FROM TransactionHistory
        JOIN Product ON TransactionHistory.product_id = Product.id
        JOIN User ON TransactionHistory.user_id = User.id
        ORDER BY TransactionHistory.transaction_date DESC
    ''')
    
    transactions = cursor.fetchall()
    conn.close()
    
    return render_template('transaction_list.html', transactions=transactions)

# 取引登録ページ
@app.route('/register_transaction', methods=['GET', 'POST'])
@login_required
def register_transaction():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        product_id = request.form['product_id']
        user_id = session['user_id']  # 現在ログインしているユーザー
        transaction_type = request.form['transaction_type']
        quantity = request.form['quantity']
        transaction_date = request.form['transaction_date']
        notes = request.form['notes']

        cursor.execute('''
            INSERT INTO TransactionHistory (product_id, user_id, transaction_type, quantity, transaction_date, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (product_id, user_id, transaction_type, quantity, transaction_date, notes))

        conn.commit()
        conn.close()
        return redirect(url_for('transaction_list'))

    # プルダウン用データ取得
    cursor.execute("SELECT id, name FROM Product")
    products = cursor.fetchall()
    
    cursor.execute("SELECT id, username FROM User")
    users = cursor.fetchall()

    conn.close()

    return render_template('register_transaction.html', products=products, users=users)

# 取引編集ページ
@app.route('/edit_transaction/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 編集する取引を取得
    cursor.execute('SELECT * FROM TransactionHistory WHERE id = ?', (transaction_id,))
    transaction = cursor.fetchone()

    if transaction is None:
        conn.close()
        return "取引が見つかりませんでした", 404

    if request.method == 'POST':
        quantity = request.form['quantity']
        transaction_type = request.form['transaction_type']
        notes = request.form['notes']

        cursor.execute('''
            UPDATE TransactionHistory
            SET quantity = ?, transaction_type = ?, notes = ?
            WHERE id = ?
        ''', (quantity, transaction_type, notes, transaction_id))

        conn.commit()
        conn.close()
        return redirect(url_for('transaction_list'))

    conn.close()
    return render_template('edit_transaction.html', transaction=transaction)

# 取引削除
@app.route('/delete_transaction/<int:transaction_id>', methods=['GET'])
@login_required
def delete_transaction(transaction_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM TransactionHistory WHERE id = ?', (transaction_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('transaction_list'))


if __name__ == '__main__':
    app.run(debug=True)
