"""
认证装饰器
提供API端点的认证保护功能
"""
import logging
from functools import wraps
from flask import request, jsonify, g
from typing import Optional, List, Callable, Any
from auth.auth_manager import auth_manager, TokenType

def require_auth(optional: bool = False, token_type: TokenType = TokenType.ACCESS):
    """
    认证装饰器
    
    Args:
        optional: 是否为可选认证（True时认证失败不会返回错误）
        token_type: 令牌类型（访问令牌或刷新令牌）
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取Authorization头
            auth_header = request.headers.get('Authorization')
            
            if not auth_header:
                if optional:
                    g.current_user = None
                    return f(*args, **kwargs)
                return jsonify({
                    'success': False,
                    'message': '缺少认证令牌',
                    'error_code': 'MISSING_TOKEN'
                }), 401
            
            # 检查Bearer格式
            if not auth_header.startswith('Bearer '):
                if optional:
                    g.current_user = None
                    return f(*args, **kwargs)
                return jsonify({
                    'success': False,
                    'message': '无效的认证格式',
                    'error_code': 'INVALID_TOKEN_FORMAT'
                }), 401
            
            # 提取令牌
            token = auth_header.split(' ')[1]
            
            # 验证令牌
            token_info = auth_manager.verify_token(token, token_type)
            
            if not token_info:
                if optional:
                    g.current_user = None
                    return f(*args, **kwargs)
                return jsonify({
                    'success': False,
                    'message': '无效或过期的令牌',
                    'error_code': 'INVALID_TOKEN'
                }), 401
            
            # 将用户信息存储到Flask上下文
            g.current_user = {
                'user_id': token_info.user_id,
                'username': token_info.username,
                'device_id': token_info.device_id,
                'ip_address': token_info.ip_address,
                'token_info': token_info
            }
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def require_refresh_token():
    """刷新令牌认证装饰器"""
    return require_auth(optional=False, token_type=TokenType.REFRESH)

def optional_auth():
    """可选认证装饰器"""
    return require_auth(optional=True)

def require_permissions(permissions: List[str]):
    """
    权限控制装饰器
    
    Args:
        permissions: 需要的权限列表
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 首先进行认证
            auth_result = require_auth()(f)
            if hasattr(auth_result, 'status_code') and auth_result.status_code != 200:
                return auth_result
            
            # 检查权限（这里简化实现，实际项目中应该从数据库查询用户权限）
            user = getattr(g, 'current_user', None)
            if not user:
                return jsonify({
                    'success': False,
                    'message': '用户信息获取失败',
                    'error_code': 'USER_INFO_ERROR'
                }), 401
            
            # TODO: 实现实际的权限检查逻辑
            # user_permissions = get_user_permissions(user['user_id'])
            # if not all(perm in user_permissions for perm in permissions):
            #     return jsonify({
            #         'success': False,
            #         'message': '权限不足',
            #         'error_code': 'INSUFFICIENT_PERMISSIONS'
            #     }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def check_device_access(user_id: str, device_id: Optional[str] = None) -> bool:
    """
    检查设备访问权限
    
    Args:
        user_id: 用户ID
        device_id: 设备ID
        
    Returns:
        是否允许访问
    """
    # TODO: 实现设备访问控制逻辑
    # 例如：检查设备是否在用户的信任设备列表中
    return True

def rate_limit(max_requests: int = 100, window_minutes: int = 60):
    """
    请求频率限制装饰器
    
    Args:
        max_requests: 时间窗口内最大请求数
        window_minutes: 时间窗口大小（分钟）
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取客户端标识（IP地址或用户ID）
            client_id = None
            
            # 优先使用用户ID
            user = getattr(g, 'current_user', None)
            if user:
                client_id = f"user:{user['user_id']}"
            else:
                # 使用IP地址
                client_id = f"ip:{request.remote_addr}"
            
            # TODO: 实现频率限制逻辑
            # 建议使用Redis的滑动窗口计数器或令牌桶算法
            # 这里简化处理
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def log_api_access(include_request_data: bool = False, include_response_data: bool = False):
    """
    API访问日志装饰器
    
    Args:
        include_request_data: 是否记录请求数据
        include_response_data: 是否记录响应数据
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            # 获取用户信息
            user = getattr(g, 'current_user', None)
            user_id = user['user_id'] if user else 'anonymous'
            
            # 记录请求信息
            log_data = {
                'endpoint': request.endpoint,
                'method': request.method,
                'path': request.path,
                'user_id': user_id,
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', ''),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            if include_request_data:
                log_data['request_data'] = {
                    'args': dict(request.args),
                    'form': dict(request.form),
                    'json': request.get_json(silent=True)
                }
            
            try:
                # 执行原函数
                result = f(*args, **kwargs)
                
                # 记录执行时间
                execution_time = time.time() - start_time
                log_data['execution_time'] = execution_time
                log_data['status'] = 'success'
                
                if include_response_data and hasattr(result, 'get_json'):
                    log_data['response_data'] = result.get_json(silent=True)
                
                logging.info(f"API访问: {log_data}")
                
                return result
                
            except Exception as e:
                # 记录异常
                execution_time = time.time() - start_time
                log_data['execution_time'] = execution_time
                log_data['status'] = 'error'
                log_data['error'] = str(e)
                
                logging.error(f"API访问异常: {log_data}")
                raise
        
        return decorated_function
    return decorator

# 导入必要的模块
import time
from datetime import datetime
