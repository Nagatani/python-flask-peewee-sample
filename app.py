from flask import Flask, request, render_template, jsonify
from models import initialize_database, db, AuditLog
from routes import blueprints
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

# NGINXなどを1つ経由する想定
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

# データベースの初期化
initialize_database()

# 各Blueprintをアプリケーションに登録
for blueprint in blueprints:
    app.register_blueprint(blueprint)

# ホームページのルート
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logs/', methods=['GET'])
def get_logs_peewee():
    """記録されたログを確認するためのエンドポイント"""
    # Peeweeの .select() を使用
    logs = AuditLog.select().order_by(AuditLog.timestamp.desc())
    
    return jsonify([
        {
            "timestamp": log.timestamp.isoformat(),
            "client_ip_address": log.client_global_ip,
            "proxy_ip_address": log.proxy_local_ip,
            "action": log.action,
            "target": f"{log.target_model} (ID: {log.target_id})",
            "user_agent": log.user_agent
        } for log in logs
    ])

@app.before_request
def before_request():
    db.connect(reuse_if_open=True)


@app.after_request
def after_request(response):
    if not db.is_closed():
        db.close()
    return response


if __name__ == '__main__':
    app.run(port=8080, debug=True)

