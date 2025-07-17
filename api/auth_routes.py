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
from auth.utils import get_client_info, validate_password_strength
from auth.decorators import require_auth, optional_auth

# 创建用户服务实例
user_service = UserService()

def login():
    """用户登录接口（增强版）"""
    try:
        # 获取请求数据
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        remember_me = data.get('remember_me', False)
        
        # 参数验证
        if not username or not password:
            return jsonify({
                "success": False,
                "message": "用户名和密码不能为空",
                "error_code": "MISSING_CREDENTIALS"
            }), 400
        
        # 基本字段验证
        if len(username.strip()) == 0 or len(password.strip()) == 0:
            return jsonify({
                "success": False,
                "message": "用户名和密码不能为空",
                "error_code": "EMPTY_CREDENTIALS"
            }), 400
        
        # 获取客户端信息
        client_info = get_client_info()
        
        # 记录登录尝试
        logging.info(f"[LOGIN ATTEMPT] username={username}, ip={client_info['ip_address']}, "
                    f"device_id={client_info['device_id'][:16]}..., remember_me={remember_me}")
        
        # 使用增强的安全认证
        auth_result = user_service.authenticate_with_security(
            username=username,
            password=password,
            client_info=client_info,
            remember_me=remember_me
        )
        
        if auth_result['success']:
            # 登录成功
            response_data = {
                "success": True,
                "message": auth_result['message'],
                "user": auth_result['user'],
                "tokens": auth_result['tokens'],
                "session_info": auth_result['session_info']
            }
            
            # 添加警告信息（如新设备登录）
            if 'warnings' in auth_result:
                response_data['warnings'] = auth_result['warnings']
            
            logging.info(f"[LOGIN SUCCESS] user={username}, active_sessions={auth_result['session_info']['active_sessions']}")
            return jsonify(response_data), 200
            
        else:
            # 登录失败
            status_code = 429 if 'LOCKED' in auth_result.get('error_code', '') else 401
            
            response_data = {
                "success": False,
                "message": auth_result['message'],
                "error_code": auth_result.get('error_code'),
            }
            
            # 添加剩余尝试次数等信息
            if 'attempts_left' in auth_result:
                response_data['attempts_left'] = auth_result['attempts_left']
            if 'remaining_time' in auth_result:
                response_data['remaining_time'] = auth_result['remaining_time']
            if 'password_feedback' in auth_result:
                response_data['password_feedback'] = auth_result['password_feedback']
            
            logging.warning(f"[LOGIN FAILED] user={username}, reason={auth_result['error_code']}, "
                          f"message={auth_result['message']}")
            
            return jsonify(response_data), status_code
            
    except Exception as e:
        logging.error(f"[LOGIN ERROR] {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "登录处理异常，请稍后重试",
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

@require_auth()
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

