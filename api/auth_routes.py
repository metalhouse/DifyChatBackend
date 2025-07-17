"""
认证相关的API路由
"""
from flask import request, jsonify
from datetime import datetime, timedelta
import threading
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.user_service import user_service

# 登录失败尝试次数和锁定时间（内存实现，适合单机）
login_attempts = {}
LOCK_THRESHOLD = 5  # 允许失败次数
LOCK_TIME = timedelta(minutes=5)  # 锁定时长
attempts_lock = threading.Lock()

def login():
    """用户登录接口"""
    username = request.form.get('username')
    password = request.form.get('password')
    client_ip = request.remote_addr
    key = username or client_ip
    now = datetime.now()
    
    # 检查登录锁定
    with attempts_lock:
        attempt = login_attempts.get(key, {"count": 0, "lock_until": None})
        if attempt["lock_until"] and now < attempt["lock_until"]:
            return jsonify({
                "success": False, 
                "message": "账户或IP已被临时锁定，请稍后再试"
            }), 429
    
    logging.info(f"[LOGIN] username={username}, ip={client_ip}")
    
    # 验证用户
    user_info = user_service.authenticate_user(username, password)
    
    if user_info:
        logging.info(f"[LOGIN SUCCESS] user={username}")
        # 清除登录失败记录
        with attempts_lock:
            if key in login_attempts:
                del login_attempts[key]
        
        return jsonify({
            "success": True,
            "user_id": user_info['user_id'],
            "user_name": user_info['user_name'],
            "avatar_url": user_info['avatar_url']
        })
    else:
        logging.info(f"[LOGIN FAIL] user={username}")
        # 记录登录失败
        with attempts_lock:
            count = attempt["count"] + 1
            lock_until = None
            if count >= LOCK_THRESHOLD:
                lock_until = now + LOCK_TIME
            login_attempts[key] = {"count": count, "lock_until": lock_until}
        
        msg = "用户名或密码错误"
        if count >= LOCK_THRESHOLD:
            msg = f"账户或IP已被临时锁定，请{LOCK_TIME.seconds//60}分钟后再试"
        
        return jsonify({"success": False, "message": msg}), 401
