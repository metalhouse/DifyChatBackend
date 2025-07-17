"""
JWT认证相关工具函数
"""
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from flask import request
from auth.auth_manager import auth_manager

def generate_device_id() -> str:
    """生成设备ID"""
    user_agent = request.headers.get('User-Agent', '')
    ip_address = request.remote_addr or '0.0.0.0'
    timestamp = str(datetime.utcnow().timestamp())
    
    # 使用用户代理、IP地址和时间戳生成设备指纹
    device_string = f"{user_agent}:{ip_address}:{timestamp}"
    device_hash = hashlib.sha256(device_string.encode()).hexdigest()
    
    return device_hash[:16]  # 取前16位作为设备ID

def get_client_info() -> Dict[str, str]:
    """获取客户端信息"""
    return {
        'ip_address': request.remote_addr or '0.0.0.0',
        'user_agent': request.headers.get('User-Agent', ''),
        'device_id': generate_device_id()
    }

def create_session_token(user_id: str, username: str, remember_me: bool = False) -> Dict[str, Any]:
    """
    创建会话令牌
    
    Args:
        user_id: 用户ID
        username: 用户名
        remember_me: 是否记住登录状态（延长刷新令牌有效期）
        
    Returns:
        包含访问令牌和刷新令牌的字典
    """
    client_info = get_client_info()
    
    # 如果选择记住登录，延长刷新令牌有效期
    if remember_me:
        # 临时修改配置（实际项目中应该有更优雅的方式）
        original_refresh_expires = auth_manager.security_config.jwt_refresh_token_expires
        auth_manager.security_config.jwt_refresh_token_expires = 30 * 24 * 3600  # 30天
        
        try:
            token_pair = auth_manager.generate_token_pair(
                user_id=user_id,
                username=username,
                device_id=client_info['device_id'],
                ip_address=client_info['ip_address']
            )
        finally:
            # 恢复原始配置
            auth_manager.security_config.jwt_refresh_token_expires = original_refresh_expires
    else:
        token_pair = auth_manager.generate_token_pair(
            user_id=user_id,
            username=username,
            device_id=client_info['device_id'],
            ip_address=client_info['ip_address']
        )
    
    # 添加客户端信息
    token_pair['client_info'] = client_info
    
    logging.info(f"为用户{username}创建会话令牌: device_id={client_info['device_id']}")
    
    return token_pair

def revoke_current_session() -> bool:
    """撤销当前会话"""
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return False
    
    token = auth_header.split(' ')[1]
    return auth_manager.revoke_token(token)

def revoke_all_sessions(user_id: str, except_current: bool = True) -> int:
    """
    撤销用户的所有会话
    
    Args:
        user_id: 用户ID
        except_current: 是否保留当前会话
        
    Returns:
        撤销的会话数量
    """
    except_token = None
    
    if except_current:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            except_token = auth_header.split(' ')[1]
    
    return auth_manager.revoke_user_sessions(user_id, except_token)

def refresh_token_if_needed(current_token: str, threshold_minutes: int = 30) -> Optional[Dict[str, Any]]:
    """
    如果令牌即将过期，自动刷新
    
    Args:
        current_token: 当前访问令牌
        threshold_minutes: 过期阈值（分钟）
        
    Returns:
        新的令牌对（如果需要刷新）或None
    """
    from auth.auth_manager import TokenType
    
    token_info = auth_manager.verify_token(current_token, TokenType.ACCESS)
    if not token_info:
        return None
    
    # 检查是否即将过期
    time_to_expire = token_info.expires_at - datetime.utcnow()
    if time_to_expire.total_seconds() > threshold_minutes * 60:
        return None
    
    # 需要刷新，但我们需要刷新令牌
    # 这里简化处理，实际应用中可能需要从数据库或缓存中获取刷新令牌
    logging.info(f"访问令牌即将过期，建议刷新: user_id={token_info.user_id}")
    
    return None  # 客户端需要主动使用刷新令牌

def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    验证密码强度
    
    Args:
        password: 密码
        
    Returns:
        验证结果
    """
    result = {
        'is_valid': True,
        'score': 0,
        'feedback': []
    }
    
    if len(password) < 8:
        result['is_valid'] = False
        result['feedback'].append('密码长度至少8位')
    else:
        result['score'] += 1
    
    if not any(c.islower() for c in password):
        result['feedback'].append('密码应包含小写字母')
    else:
        result['score'] += 1
    
    if not any(c.isupper() for c in password):
        result['feedback'].append('密码应包含大写字母')
    else:
        result['score'] += 1
    
    if not any(c.isdigit() for c in password):
        result['feedback'].append('密码应包含数字')
    else:
        result['score'] += 1
    
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        result['feedback'].append('密码应包含特殊字符')
    else:
        result['score'] += 1
    
    # 检查常见弱密码
    common_passwords = [
        'password', '123456', 'password123', 'admin', 'root',
        'qwerty', 'abc123', '111111', '000000'
    ]
    
    if password.lower() in common_passwords:
        result['is_valid'] = False
        result['feedback'].append('密码过于简单，请使用更复杂的密码')
        result['score'] = 0
    
    return result

def generate_secure_token(length: int = 32) -> str:
    """生成安全的随机令牌"""
    return secrets.token_urlsafe(length)

def hash_sensitive_data(data: str) -> str:
    """对敏感数据进行哈希处理（用于日志记录）"""
    return hashlib.sha256(data.encode()).hexdigest()[:8]

def get_token_info_from_request() -> Optional[Dict[str, Any]]:
    """从请求中获取令牌信息"""
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    token_info = auth_manager.verify_token(token)
    
    if not token_info:
        return None
    
    return {
        'user_id': token_info.user_id,
        'username': token_info.username,
        'device_id': token_info.device_id,
        'ip_address': token_info.ip_address,
        'issued_at': token_info.issued_at,
        'expires_at': token_info.expires_at
    }

def check_token_permissions(token: str, required_permissions: list) -> bool:
    """
    检查令牌是否具有所需权限
    
    Args:
        token: JWT令牌
        required_permissions: 所需权限列表
        
    Returns:
        是否具有权限
    """
    token_info = auth_manager.verify_token(token)
    if not token_info:
        return False
    
    # TODO: 实现权限检查逻辑
    # 从数据库或缓存中获取用户权限
    # user_permissions = get_user_permissions(token_info.user_id)
    # return all(perm in user_permissions for perm in required_permissions)
    
    return True  # 临时返回True，实际项目中需要实现权限检查

def create_password_reset_token(user_id: str) -> str:
    """创建密码重置令牌"""
    payload = {
        'user_id': user_id,
        'type': 'password_reset',
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=1)  # 1小时有效期
    }
    
    return jwt.encode(
        payload,
        auth_manager.security_config.jwt_secret_key,
        algorithm='HS256'
    )

def verify_password_reset_token(token: str) -> Optional[str]:
    """验证密码重置令牌"""
    try:
        payload = jwt.decode(
            token,
            auth_manager.security_config.jwt_secret_key,
            algorithms=['HS256']
        )
        
        if payload.get('type') != 'password_reset':
            return None
        
        return payload.get('user_id')
        
    except jwt.ExpiredSignatureError:
        logging.info("密码重置令牌已过期")
        return None
    except jwt.InvalidTokenError:
        logging.warning("无效的密码重置令牌")
        return None

# 导入必要的模块
import jwt
