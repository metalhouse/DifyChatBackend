"""
认证相关的API路由 (标准化版本)
"""
from flask import request, jsonify, g
import logging

from utils.response_builder import ResponseBuilder, ErrorCode
from utils.request_validator import UserLoginRequest, validate_and_convert, ValidationError
from services.user_service import UserService
from auth.utils import get_client_info
from auth.decorators import require_auth

# 创建用户服务实例
user_service = UserService()

def login():
    """用户登录接口"""
    try:
        # 1. 请求验证
        try:
            login_request = validate_and_convert(request.get_json(), UserLoginRequest)
        except ValidationError as e:
            return ResponseBuilder.validation_error(e.errors)
        
        # 2. 获取客户端信息
        client_info = get_client_info()
        
        # 3. 记录登录尝试
        logging.info(f"[LOGIN ATTEMPT] username={login_request.username}, "
                    f"ip={client_info['ip_address']}, device_id={client_info['device_id'][:16]}...")
        
        # 4. 执行认证
        auth_result = user_service.authenticate_with_security(
            username=login_request.username,
            password=login_request.password,
            client_info=client_info,
            remember_me=login_request.remember_me
        )
        
        # 5. 处理认证结果
        if auth_result['success']:
            # 登录成功
            response_data = {
                "user": auth_result['user'],
                "tokens": auth_result['tokens'],
                "session_info": auth_result['session_info']
            }
            
            # 添加警告信息（如新设备登录）
            if 'warnings' in auth_result:
                response_data['warnings'] = auth_result['warnings']
            
            logging.info(f"[LOGIN SUCCESS] user={login_request.username}, "
                        f"active_sessions={auth_result['session_info']['active_sessions']}")
            
            return ResponseBuilder.success(
                data=response_data,
                message=auth_result['message']
            )
            
        else:
            # 登录失败
            error_code_map = {
                'INVALID_CREDENTIALS': ErrorCode.INVALID_CREDENTIALS,
                'USER_NOT_FOUND': ErrorCode.USER_NOT_FOUND,
                'ACCOUNT_LOCKED': ErrorCode.ACCOUNT_LOCKED,
                'TOO_MANY_ATTEMPTS': ErrorCode.RATE_LIMITED,
                'WEAK_PASSWORD': ErrorCode.WEAK_PASSWORD
            }
            
            error_code = error_code_map.get(auth_result.get('error_code'), ErrorCode.AUTHENTICATION_FAILED)
            
            # 构建错误响应
            error_data = {}
            if 'attempts_left' in auth_result:
                error_data['attempts_left'] = auth_result['attempts_left']
            if 'remaining_time' in auth_result:
                error_data['remaining_time'] = auth_result['remaining_time']
            if 'password_feedback' in auth_result:
                error_data['password_feedback'] = auth_result['password_feedback']
            
            logging.warning(f"[LOGIN FAILED] user={login_request.username}, "
                          f"reason={auth_result['error_code']}")
            
            return ResponseBuilder.error(
                error_code=error_code,
                message=auth_result['message'],
                data=error_data if error_data else None
            )
            
    except Exception as e:
        logging.error(f"[LOGIN ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="登录处理异常，请稍后重试"
        )

def refresh_token():
    """刷新访问令牌"""
    try:
        # 1. 请求验证
        data = request.get_json()
        if not data or not data.get('refresh_token'):
            return ResponseBuilder.error(
                error_code=ErrorCode.MISSING_PARAMETER,
                message="刷新令牌不能为空"
            )
        
        refresh_token_value = data.get('refresh_token')
        
        # 2. 执行令牌刷新
        new_tokens = user_service.refresh_access_token(refresh_token_value)
        
        # 3. 处理刷新结果
        if new_tokens:
            return ResponseBuilder.success(
                data={"tokens": new_tokens},
                message="令牌刷新成功"
            )
        else:
            return ResponseBuilder.error(
                error_code=ErrorCode.INVALID_TOKEN,
                message="刷新令牌无效或已过期"
            )
            
    except Exception as e:
        logging.error(f"[REFRESH TOKEN ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="令牌刷新异常"
        )

@require_auth()
def logout():
    """用户退出登录"""
    try:
        # 1. 获取当前用户信息
        current_user = getattr(g, 'current_user', None)
        if not current_user:
            return ResponseBuilder.error(
                error_code=ErrorCode.AUTHENTICATION_REQUIRED,
                message="用户认证信息缺失"
            )
        
        # 2. 获取令牌并撤销
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user_service.revoke_token(token)
        
        # 3. 记录退出
        logging.info(f"[LOGOUT SUCCESS] user={current_user['username']}")
        
        return ResponseBuilder.success(
            message="退出登录成功"
        )
        
    except Exception as e:
        logging.error(f"[LOGOUT ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="退出登录异常"
        )

def get_current_user():
    """获取当前用户信息"""
    @require_auth()
    def _get_current_user():
        try:
            current_user = getattr(g, 'current_user', None)
            if not current_user:
                return ResponseBuilder.error(
                    error_code=ErrorCode.AUTHENTICATION_REQUIRED,
                    message="用户认证信息缺失"
                )
            
            # 移除敏感信息
            user_info = {
                "username": current_user['username'],
                "display_name": current_user.get('display_name'),
                "email": current_user.get('email'),
                "permissions": current_user.get('permissions', []),
                "last_login": current_user.get('last_login'),
                "active_sessions": current_user.get('active_sessions', 0)
            }
            
            return ResponseBuilder.success(
                data=user_info,
                message="获取用户信息成功"
            )
            
        except Exception as e:
            logging.error(f"[GET USER ERROR] {e}", exc_info=True)
            return ResponseBuilder.error(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="获取用户信息异常"
            )
    
    return _get_current_user()
