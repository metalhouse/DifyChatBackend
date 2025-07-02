from flask import Flask, request, jsonify
import json
import os
from utils import hash_password, decode_token
import logging

app = Flask(__name__)

# 配置日志
logging.basicConfig(filename='login.log', level=logging.INFO, format='%(asctime)s %(message)s', encoding='utf-8')

# 从 JSON 文件加载用户数据
def load_users():
    with open(os.path.join(os.path.dirname(__file__), 'users.json'), 'r', encoding='utf-8') as f:
        return json.load(f)

@app.route('/api/login', methods=['POST'])
def login():
    users = load_users()
    username = request.form.get('username')
    password = request.form.get('password')
    logging.info(f"[LOGIN] username={username}, password={password}")
    user = users.get(username)
    if user and user["password"] == hash_password(password):
        logging.info(f"[LOGIN SUCCESS] user={username}")
        return jsonify({
            "success": True,
            "dify_token": decode_token(user["dify_token"]),
            "user_id": username,
            "user_name": f"{username}的昵称",
            "avatar_url": f"https://api.dicebear.com/7.x/miniavs/svg?seed={username}"
        })
    else:
        logging.info(f"[LOGIN FAIL] user={username}")
        return jsonify({"success": False, "message": "用户名或密码错误"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
