from datetime import datetime
from peewee import Model, CharField, DateTimeField, IntegerField
from .db import db


class AuditLog(Model):
    """Peeweeによる監査ログモデル"""
    timestamp = DateTimeField(
        default=datetime.now, 
        index=True
    )
    client_global_ip = CharField(max_length=45, null=True, help_text="クライアントのグローバルIP")
    proxy_local_ip = CharField(max_length=45, null=True, help_text="直接接続元のプロキシIP")

    user_agent = CharField(max_length=255, null=True)
    action = CharField(max_length=100)
    target_model = CharField(max_length=100, null=True)
    target_id = IntegerField(null=True)
    
    class Meta:
        database = db