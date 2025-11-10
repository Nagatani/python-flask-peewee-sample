from flask import request
from .db import db
from .user import User
from .product import Product
from .order import Order
from .auditlog import AuditLog


# モデルのリストを定義しておくと、後でまとめて登録しやすくなります
MODELS = [
    User,
    Product,
    Order,
    AuditLog,
]

# データベースの初期化関数
def initialize_database():
    db.connect()
    db.create_tables(MODELS, safe=True)
    db.close()


def reset_database():
    """
    データベースをリセット（全テーブル削除＆再作成）する関数
    """
    # db.connect()
    db.drop_tables(MODELS, safe=True)
    db.create_tables(MODELS, safe=True)

    # サンプルデータの挿入
    log_audit_peewee(action="DB_INITIALIZE_START")

    user1 = User.create(name="Suzuki Taro", age=20)
    user2 = User.create(name="Tanaka Hanako", age=25)
    user3 = User.create(name="Sato Ichiro", age=30)
    product1 = Product.create(name="Laptop", price=2000)
    product2 = Product.create(name="Smartphone", price=500)
    product3 = Product.create(name="Tablet", price=1000)
    order1 = Order.create(user=user1, product=product1, order_date="2025-01-15")
    order2 = Order.create(user=user2, product=product2, order_date="2025-01-20")
    order3 = Order.create(user=user3, product=product3, order_date="2025-01-25")
    
    log_audit_peewee(action="DB_INITIALIZE_COMPLETE")

    # db.close()


def log_audit_peewee(action, target_object=None):
    """
    Peeweeモデルを使用して監査ログを書き出す関数。
    
    注意: この関数は db.atomic() トランザクションブロック内で
    呼び出されることを想定しています。
    """

    try:
        global_ip = request.remote_addr
        local_ip = request.environ.get('REMOTE_ADDR')
        user_agent_str = request.user_agent.string if request.user_agent else request.headers.get('User-Agent', 'N/A')
        client_uuid = request.cookies.get('client_uuid')

    except RuntimeError:
        global_ip = "N/A (CLI)"
        local_ip = "N/A (CLI)"
        user_agent_str = "N/A (CLI)"
        client_uuid = "N/A (CLI)"

    target_model_name = None
    target_obj_id = None

    if target_object and hasattr(target_object, 'id'):
        target_model_name = target_object.__class__.__name__
        target_obj_id = target_object.id

    # 修正したモデルに合わせて .create() を呼び出す
    AuditLog.create(
        client_global_ip=global_ip,
        proxy_local_ip=local_ip,
        user_agent=user_agent_str,
        action=action,
        client_uuid=client_uuid,
        target_model=target_model_name,
        target_id=target_obj_id
    )
