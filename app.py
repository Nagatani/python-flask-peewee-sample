from flask import Flask, request, render_template, render_template_string, jsonify, make_response, g
from models import initialize_database, db, AuditLog, log_audit_peewee, reset_database
from routes import blueprints
from werkzeug.middleware.proxy_fix import ProxyFix
from os import getenv
import uuid


app = Flask(__name__)

# NGINXなどを1つ経由する想定
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

# クライアント識別用Cookieの名前
CLIENT_COOKIE_NAME = 'client_uuid'
# 環境変数からデータベースリセット用パスワードを取得
APP_RESET_PASSWORD = getenv("APP_RESET_PASSWORD") or "default_password_change_me"

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
            "client_uuid": log.client_uuid,
            "target": f"{log.target_model} (ID: {log.target_id})",
            "user_agent": log.user_agent
        } for log in logs
    ])


@app.before_request
def ensure_client_uuid():
    """
    リクエストごとにCookieを確認し、存在しなければセットする。
    HttpOnly属性をつけ、JSからの読み取りを防ぐ。
    """
    db.connect(reuse_if_open=True)
    if CLIENT_COOKIE_NAME not in request.cookies:
        # 新しいUUIDを生成
        new_uuid = str(uuid.uuid4())
        
        # 次回以降のリクエストで使えるようにレスポンスにセットする
        # この処理はリクエストの「後」にレスポンスを構築する際に
        # 実行される必要があるため、g (g.client_uuid) に一時保存する。
        g.client_uuid = new_uuid


@app.after_request
def set_client_uuid_cookie(response):
    """
    リクエスト処理中に g.client_uuid がセットされていたら、
    実際のレスポンスにCookieを焼く。
    """
    if not db.is_closed():
        db.close()

    if hasattr(g, 'client_uuid'):
        response.set_cookie(
            CLIENT_COOKIE_NAME,
            g.client_uuid,
            max_age=60*60*24*365*2, # 2年間有効
            httponly=True,  # JSから読めないようにする (セキュリティ向上)
            samesite='Lax'  # CSRF対策
            # secure=True  # 本番環境 (HTTPS) ではこれをTrueにする
        )
    return response


@app.route('/get_my_uuid', methods=['GET'])
def get_my_uuid():
    """
    (要求) クライアントが自分のUUIDを参照するためのAPI。
    """
    # ブラウザが自動送信してきたCookieをサーバーが読み取り、
    # その値をJSONでクライアントに返す。
    my_uuid = request.cookies.get(CLIENT_COOKIE_NAME)
    
    if my_uuid:
        return jsonify({"my_client_uuid": my_uuid})
    else:
        # このAPIに初めてアクセスした場合、まだCookieがセットされていない
        # 可能性があるので、gにセットされた値を見る
        if hasattr(g, 'client_uuid'):
             return jsonify({"my_client_uuid": g.client_uuid, "status": "just_created"})
        
        return jsonify({"error": "UUID not found or not set yet"}), 404


@app.route('/admin/reset_database', methods=['POST'])
def handle_reset_database():
    """
    データベースを初期化するエンドポイント
    JSONで {"password": "..."} を受け取る
    """
    data = request.json
    
    # 1. パスワードの検証
    if not data or data.get('password') != APP_RESET_PASSWORD:
        # パスワードが間違っている場合は、ログに記録する (オプション)
        log_audit_peewee(action="DB_RESET_ATTEMPT_FAILED")
        
        return jsonify({"error": "Unauthorized"}), 403 # 403 Forbidden

    # 2. パスワードが正しい場合
    try:
        # ログに関係者のIPやUUIDを残すため、先にログを記録
        log_audit_peewee(action="DB_RESET_ATTEMPT_AUTHORIZED")
        
        # データベース初期化関数を実行
        reset_database()

        return jsonify({
            "success": True, 
            "message": "Database has been reset to sample data."
        }), 200
        
    except Exception as e:
        app.logger.error(f"Failed to reset database: {e}")
        return jsonify({"error": "Failed to reset database"}), 500

@app.route('/admin/reset_page', methods=['GET'])
def show_reset_page():
    """
    (要求) データベース初期化用のHTML画面を表示するエンドポイント
    """
    
    # HTMLとJavaScriptをPythonの文字列として定義
    html_template = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>データベース初期化</title>
        <style>
            body { font-family: sans-serif; margin: 2em; background: #f4f4f4; }
            .container { max-width: 500px; margin: 0 auto; padding: 2em; background: #fff; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
            h1 { color: #d9534f; }
            label { display: block; margin-top: 1em; font-weight: bold; }
            input[type="password"] { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
            button { background: #d9534f; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 1em; margin-top: 1.5em; }
            button:hover { background: #c9302c; }
            #result { margin-top: 1.5em; padding: 1em; background: #eee; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; }
            .success { background: #dff0d8; border: 1px solid #d6e9c6; color: #3c763d; }
            .error { background: #f2dede; border: 1px solid #ebccd1; color: #a94442; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>データベース初期化</h1>
            <p><strong>警告:</strong> これを実行すると、データベース内のすべてのデータが削除され、サンプルデータに置き換えられます。</p>
            
            <label for="password">リセット用パスワード:</label>
            <input type="password" id="password" name="password">
            
            <button id="resetButton">初期化を実行</button>
            
            <pre id="result"></pre>
        </div>

        <script>
            document.getElementById('resetButton').addEventListener('click', function() {
                const password = document.getElementById('password').value;
                const resultEl = document.getElementById('result');
                
                // ボタンを無効化
                this.disabled = true;
                this.textContent = '処理中...';
                resultEl.textContent = 'サーバーにリクエストを送信中...';
                resultEl.className = '';

                // リセットのためのAPIエンドポイントを呼び出す
                fetch('/admin/reset_database', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ password: password })
                })
                .then(response => {
                    // HTTPステータスコードに関わらず、レスポンスのJSONを取得
                    return response.json().then(data => ({
                        status: response.status,
                        body: data
                    }));
                })
                .then(res => {
                    // レスポンスを整形して表示
                    resultEl.textContent = JSON.stringify(res.body, null, 2);

                    if (res.status === 200) {
                        resultEl.className = 'success';
                    } else {
                        resultEl.className = 'error';
                    }
                })
                .catch(error => {
                    // ネットワークエラーなど
                    resultEl.textContent = 'リクエスト失敗: ' + error.message;
                    resultEl.className = 'error';
                })
                .finally(() => {
                    // ボタンを再度有効化
                    document.getElementById('resetButton').disabled = false;
                    document.getElementById('resetButton').textContent = '初期化を実行';
                });
            });
        </script>
    </body>
    </html>
    """
    
    # 文字列として定義したHTMLをレンダリングして返す
    return render_template_string(html_template)


if __name__ == '__main__':
    app.run(port=8080, debug=True)

