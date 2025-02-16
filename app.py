from flask import Flask, render_template, request, redirect, url_for
import sqlite3

# Flask アプリケーションの作成
app = Flask(__name__)

# データベース接続を行う関数
def get_db_connection():
    conn = sqlite3.connect('cafe_app.db')
    conn.row_factory = sqlite3.Row
    return conn

# ホーム画面を表示
@app.route('/')
def index():
    return 'Welcome to Cafe App!'

# ユーザー登録画面を表示
@app.route('/register_user', methods=['GET', 'POST'])
def register_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO User (username, password, role, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (username, password, role)
        )
        conn.commit()
        conn.close()
        
        return redirect(url_for('register_user'))

    return render_template('register_user.html')

# 商品登録画面を表示
@app.route('/register', methods=['GET', 'POST'])
def register_product():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        price = request.form['price']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Product (name, description, category, price) VALUES (?, ?, ?, ?)",
            (name, description, category, price)
        )
        product_id = cursor.lastrowid
        conn.commit()

        cursor.execute(
            "INSERT INTO Stock (product_id, quantity, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (product_id, 0)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('register_product'))

    return render_template('register_product.html')

# 在庫更新処理
@app.route('/update_stock', methods=['GET', 'POST'])
def update_stock():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Product")
    products = cursor.fetchall()

    cursor.execute("SELECT * FROM User")
    users = cursor.fetchall()

    if request.method == 'POST':
        product_id = request.form.get('product_id')
        quantity = request.form.get('quantity')
        transaction_type = request.form.get('transaction_type')
        notes = request.form.get('notes')
        user_id = request.form.get('user_id')

        if not product_id or not quantity or not transaction_type or not user_id:
            return "すべての項目を入力してください。"

        quantity = int(quantity)
        user_id = int(user_id)

        cursor.execute("SELECT * FROM Stock WHERE product_id = ?", (product_id,))
        stock = cursor.fetchone()
        
        if stock:
            if transaction_type == '入庫':
                new_quantity = stock['quantity'] + quantity
            elif transaction_type == '出庫' and stock['quantity'] >= quantity:
                new_quantity = stock['quantity'] - quantity
            else:
                return "出庫数が在庫数を超えています。"
            
            cursor.execute("UPDATE Stock SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ?", (new_quantity, product_id))
        else:
            if transaction_type == '入庫':
                cursor.execute("INSERT INTO Stock (product_id, quantity, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (product_id, quantity))
            else:
                return "在庫が存在しないため、出庫できません。"

        cursor.execute(
            "INSERT INTO TransactionHistory (product_id, user_id, quantity, transaction_type, transaction_date, notes) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)",
            (product_id, user_id, quantity, transaction_type, notes)
        )

        conn.commit()
        conn.close()

        return redirect(url_for('update_stock'))

    return render_template('update_stock.html', products=products, users=users)

# 商品ごとの在庫数を表示する処理
@app.route('/view_stock')
def view_stock():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT Product.name, Product.category, Product.price, Stock.quantity
    FROM Product
    LEFT JOIN Stock ON Product.ID = Stock.product_id
    ''')
    products = cursor.fetchall()
    conn.close()
    return render_template('view_stock.html', products=products)

# 取引履歴の表示
@app.route('/view_transaction_history')
def view_transaction_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT Product.name AS product_name, User.username AS user_name, TransactionHistory.transaction_type, 
           TransactionHistory.quantity, TransactionHistory.transaction_date, TransactionHistory.notes
    FROM TransactionHistory
    JOIN Product ON TransactionHistory.product_id = Product.id
    JOIN User ON TransactionHistory.user_id = User.id
    ''')
    transactions = cursor.fetchall()
    
    # デバッグ用: 取得したデータをターミナルに出力
    print("取得した取引履歴:")
    for transaction in transactions:
        print(dict(transaction))  # ← データを辞書形式で出力
    
    conn.close()
    return render_template('view_transaction_history.html', transactions=transactions)




if __name__ == '__main__':
    app.run(debug=True)
