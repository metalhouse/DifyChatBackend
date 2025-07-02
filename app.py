from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import json
import os
import threading
from utils import hash_password, decode_token
import logging

app = Flask(__name__)

# 配置日志
logging.basicConfig(filename='login.log', level=logging.INFO, format='%(asctime)s %(message)s', encoding='utf-8')

# 从 JSON 文件加载用户数据
def load_users():
    with open(os.path.join(os.path.dirname(__file__), 'users.json'), 'r', encoding='utf-8') as f:
        return json.load(f)

# 登录失败尝试次数和锁定时间（内存实现，适合单机）
login_attempts = {}
LOCK_THRESHOLD = 5  # 允许失败次数
LOCK_TIME = timedelta(minutes=5)  # 锁定时长
attempts_lock = threading.Lock()

@app.route('/api/login', methods=['POST'])
def login():
    users = load_users()
    username = request.form.get('username')
    password = request.form.get('password')
    client_ip = request.remote_addr
    key = username or client_ip
    now = datetime.now()
    
    with attempts_lock:
        attempt = login_attempts.get(key, {"count": 0, "lock_until": None})
        # 检查是否被锁定
        if attempt["lock_until"] and now < attempt["lock_until"]:
            return jsonify({"success": False, "message": "账户或IP已被临时锁定，请稍后再试"})

    logging.info(f"[LOGIN] username={username}, password={password}")
    user = users.get(username)
    if user and user["password"] == hash_password(password):
        logging.info(f"[LOGIN SUCCESS] user={username}")
        with attempts_lock:
            if key in login_attempts:
                del login_attempts[key]
        return jsonify({
            "success": True,
            "dify_token": decode_token(user["dify_token"]),
            "user_id": username,
            "user_name": f"{username}的昵称",
            "avatar_url": f"https://api.dicebear.com/7.x/miniavs/svg?seed={username}"
        })
    else:
        logging.info(f"[LOGIN FAIL] user={username}")
        with attempts_lock:
            count = attempt["count"] + 1
            lock_until = None
            if count >= LOCK_THRESHOLD:
                lock_until = now + LOCK_TIME
            login_attempts[key] = {"count": count, "lock_until": lock_until}
        msg = "用户名或密码错误"
        if count >= LOCK_THRESHOLD:
            msg = f"账户或IP已被临时锁定，请{LOCK_TIME.seconds//60}分钟后再试"
        return jsonify({"success": False, "message": msg})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
