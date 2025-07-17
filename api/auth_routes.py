"""
认证相关的API路由
"""
from flask import request, jsonify
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.user_service import UserService

# 创建用户服务实例
user_service = UserService()

def login():
    """用户登录接口"""
    try:
        # 获取请求数据
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                "success": False,
                "message": "用户名和密码不能为空",
                "error_code": "MISSING_CREDENTIALS"
            }), 400
        
        client_ip = request.remote_addr
        logging.info(f"[LOGIN] username={username}, ip={client_ip}")
        
        # 使用带安全检查的认证方法
        auth_result = user_service.authenticate_with_security(username, password)
        
        if auth_result['success']:
            logging.info(f"[LOGIN SUCCESS] user={username}")
            return jsonify({
                "success": True,
                "message": auth_result['message'],
                "user": auth_result['user'],
                "tokens": auth_result['tokens']
            }), 200
        else:
            status_code = 429 if auth_result.get('error_code') == 'ACCOUNT_LOCKED' else 401
            logging.warning(f"[LOGIN FAILED] user={username}, reason={auth_result['message']}")
            return jsonify({
                "success": False,
                "message": auth_result['message'],
                "error_code": auth_result.get('error_code'),
                "attempts_left": auth_result.get('attempts_left')
            }), status_code
            
    except Exception as e:
        logging.error(f"[LOGIN ERROR] {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "登录处理异常",
            "error_code": "INTERNAL_ERROR"
        }), 500

def refresh_token():
    """刷新访问令牌"""
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({
                "success": False,
                "message": "刷新令牌不能为空"
            }), 400
        
        new_tokens = user_service.refresh_access_token(refresh_token)
        
        if new_tokens:
            return jsonify({
                "success": True,
                "message": "令牌刷新成功",
                "tokens": new_tokens
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "刷新令牌无效或已过期"
            }), 401
            
    except Exception as e:
        logging.error(f"[REFRESH TOKEN ERROR] {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "令牌刷新异常"
        }), 500

def logout():
    """用户退出登录"""
    try:
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            # 撤销令牌（加入黑名单）
            user_service.revoke_token(token)
        
        return jsonify({
            "success": True,
            "message": "退出登录成功"
        }), 200
        
    except Exception as e:
        logging.error(f"[LOGOUT ERROR] {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "退出登录异常"
        }), 500

