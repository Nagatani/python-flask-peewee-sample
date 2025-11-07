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


def log_audit_peewee(action, target_object=None):
    """
    Peeweeモデルを使用して監査ログを書き出す関数。
    
    注意: この関数は db.atomic() トランザクションブロック内で
    呼び出されることを想定しています。
    """

    try:
        global_ip = request.remote_addr
        local_ip = request.environ.get('REMOTE_ADDR')
        user_agent_str = request.user_agent.string if request.user_agent else "Unknown"

    except RuntimeError:
        global_ip = "N/A (CLI)"
        local_ip = "N/A (CLI)"
        user_agent_str = "N/A (CLI)"

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
        target_model=target_model_name,
        target_id=target_obj_id
    )
