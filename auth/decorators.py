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
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({
                    'success': False,
                    'message': '缺少认证令牌',
                    'error_code': 'MISSING_TOKEN'
                }), 401
            
            token = auth_header.split(' ')[1]
            token_info = auth_manager.verify_token(token, TokenType.ACCESS)
            
            if not token_info:
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
            
            # 检查权限（从数据库或配置中获取用户权限）
            user_permissions = get_user_permissions(token_info.username)
            missing_permissions = [perm for perm in permissions if perm not in user_permissions]
            
            if missing_permissions:
                logging.warning(f"User {token_info.username} lacks permissions: {missing_permissions}")
                return jsonify({
                    'success': False,
                    'message': f'权限不足，缺少权限：{", ".join(missing_permissions)}',
                    'error_code': 'INSUFFICIENT_PERMISSIONS',
                    'missing_permissions': missing_permissions
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def get_user_permissions(username: str) -> List[str]:
    """
    获取用户权限列表
    
    Args:
        username: 用户名
        
    Returns:
        权限列表
    """
    try:
        # 从用户服务获取用户信息
        from services.user_service import UserService
        user_service = UserService()
        user = user_service.get_user(username)
        
        if not user:
            return []
        
        # 基础权限
        permissions = ['read_profile', 'update_profile']
        
        # 管理员权限
        if user.get('admin', False):
            permissions.extend([
                'admin_access',
                'manage_users',
                'view_all_agents',
                'manage_agents',
                'view_system_logs'
            ])
        
        # 普通用户权限
        permissions.extend([
            'use_chat',
            'view_conversations',
            'manage_conversations',
            'access_agents'
        ])
        
        return permissions
        
    except Exception as e:
        logging.error(f"Error getting user permissions for {username}: {e}")
        return []

def check_agent_access(agent_id_param: str = 'agent_id'):
    """
    智能体访问权限检查装饰器
    
    Args:
        agent_id_param: 包含智能体ID的参数名
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 确保用户已认证
            user = getattr(g, 'current_user', None)
            if not user:
                return jsonify({
                    'success': False,
                    'message': '用户未认证',
                    'error_code': 'AUTHENTICATION_REQUIRED'
                }), 401
            
            # 获取智能体ID
            agent_id = None
            
            # 从请求参数获取
            if request.method == 'GET':
                agent_id = request.args.get(agent_id_param)
            elif request.method in ['POST', 'PUT', 'PATCH']:
                if request.is_json:
                    data = request.get_json(silent=True) or {}
                    agent_id = data.get(agent_id_param)
                else:
                    agent_id = request.form.get(agent_id_param)
            
            # 如果没有提供智能体ID，允许访问（可能是获取列表）
            if not agent_id:
                return f(*args, **kwargs)
            
            # 检查用户是否有权访问该智能体
            if not has_agent_access(user['username'], agent_id):
                return jsonify({
                    'success': False,
                    'message': '无权访问该智能体',
                    'error_code': 'AGENT_ACCESS_DENIED',
                    'agent_id': agent_id
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def has_agent_access(username: str, agent_id: str) -> bool:
    """
    检查用户是否有权访问指定智能体
    
    Args:
        username: 用户名
        agent_id: 智能体ID
        
    Returns:
        是否有访问权限
    """
    try:
        from services.dify_service import dify_service
        
        # 获取用户可访问的智能体列表
        user_agents = dify_service.get_user_agents(username)
        agent_ids = [agent['agent_id'] for agent in user_agents]
        
        return agent_id in agent_ids
        
    except Exception as e:
        logging.error(f"Error checking agent access for user {username}, agent {agent_id}: {e}")
def check_device_access(user_id: str, device_id: Optional[str] = None) -> bool:
    """
    检查设备访问权限
    
    Args:
        user_id: 用户ID
        device_id: 设备ID
        
    Returns:
        是否允许访问
    """
    try:
        # 基本的设备访问控制
        # 在生产环境中，这里应该实现：
        # 1. 检查设备是否在用户的信任设备列表中
        # 2. 检查设备是否被锁定或禁用
        # 3. 检查地理位置等安全因素
        
        if not device_id:
            return True  # 允许无设备ID的访问
        
        # 简化实现：所有设备都允许访问
        # 在实际项目中应该查询数据库
        return True
        
    except Exception as e:
        logging.error(f"Error checking device access: {e}")
        return False

def auto_refresh_token():
    """
    自动刷新令牌装饰器
    当access token即将过期时自动刷新
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                return f(*args, **kwargs)
            
            token = auth_header.split(' ')[1]
            
            # 检查令牌是否即将过期（剩余时间少于5分钟）
            from datetime import datetime, timedelta
            import jwt
            
            try:
                # 解码但不验证过期时间
                payload = jwt.decode(token, options={"verify_exp": False}, algorithms=["HS256"])
                exp_time = datetime.fromtimestamp(payload.get('exp', 0))
                current_time = datetime.now()
                
                # 如果令牌在5分钟内过期，尝试刷新
                if exp_time - current_time < timedelta(minutes=5):
                    refresh_token_header = request.headers.get('X-Refresh-Token')
                    if refresh_token_header:
                        try:
                            # 尝试刷新令牌
                            new_tokens = auth_manager.refresh_access_token(refresh_token_header)
                            if new_tokens:
                                # 在响应头中返回新令牌
                                from flask import g
                                g.new_access_token = new_tokens['access_token']
                                g.new_refresh_token = new_tokens.get('refresh_token')
                        except Exception as refresh_error:
                            logging.warning(f"Token refresh failed: {refresh_error}")
                
            except Exception as e:
                logging.debug(f"Token auto-refresh check failed: {e}")
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
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
