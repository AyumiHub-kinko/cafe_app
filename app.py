from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text  # 追加
import os

# SQLiteデータベースの設定
app = Flask(__name__, instance_path=None)  # instance_path=Noneを設定

# 絶対パスでデータベースの保存場所を指定
base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, 'cafe_app.db')  # cafe_app.dbをプロジェクトのルートディレクトリに保存
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemyインスタンス
db = SQLAlchemy(app)

# モデルの定義 (データベースのテーブルに対応)
class Product(db.Model):
    __tablename__ = 'Product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    category = db.Column(db.String(50))
    price = db.Column(db.Numeric(10, 2), nullable=False)

    def __repr__(self):
        return f"<Product {self.name}>"

# アプリケーションコンテキスト内でテーブル作成を確認
with app.app_context():
    db.create_all()  # テーブル作成

# データベースに接続されたことを確認するメッセージを表示
@app.route('/')
def index():
    try:
        # SQLAlchemyのtext関数を使用してクエリを実行
        db.session.execute(text('SELECT 1'))
        return "データベース接続成功！"
    except Exception as e:
        return f"データベース接続に失敗しました: {str(e)}"

# 商品登録ページ
@app.route('/product/register', methods=['GET', 'POST'])
def register_product():
    if request.method == 'POST':
        # フォームからデータを取得
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        price = request.form['price']

        # 新しい商品をデータベースに追加
        new_product = Product(
            name=name,
            description=description,
            category=category,
            price=price
        )

        try:
            db.session.add(new_product)
            db.session.commit()
            return redirect(url_for('product_list'))
        except Exception as e:
            db.session.rollback()  # もしエラーがあればロールバック
            print(f"Error occurred: {e}")
            return "エラーが発生しました。"
    return render_template('register_product.html')

# 商品リストページ（登録後に遷移）
@app.route('/products')
def product_list():
    products = Product.query.all()
    return render_template('product_list.html', products=products)

# アプリケーションの実行
if __name__ == '__main__':
    app.run(debug=True)
