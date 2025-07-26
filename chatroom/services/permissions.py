"""
聊天室权限管理系统
"""
from functools import wraps
from flask import request, jsonify, g
from datetime import datetime
from typing import Dict, List
import logging

# 如果系统中有JWT，使用系统的JWT
try:
    import jwt
except ImportError:
    # 如果没有安装PyJWT，可以从系统的auth模块导入
    try:
        from auth.utils import jwt
    except ImportError:
        jwt = None

logger = logging.getLogger(__name__)

# 权限定义
CHATROOM_PERMISSIONS = {
    "admin": {
        "name": "系统管理员",
        "permissions": ["chatroom_admin", "chatroom_access", "user_management"]
    },
    "chatroom_manager": {
        "name": "聊天室管理员", 
        "permissions": ["chatroom_create", "chatroom_manage", "chatroom_access"]
    },
    "chatroom_user": {
        "name": "聊天室用户",
        "permissions": ["chatroom_access"]
    },
    "regular_user": {
        "name": "普通用户",
        "permissions": []
    }
}

class ChatroomPermissionManager:
    """聊天室权限管理器"""
    
    @staticmethod
    def get_user_permissions(user_roles: List[str]) -> List[str]:
        """获取用户权限列表"""
        permissions = set()
        for role in user_roles:
            if role in CHATROOM_PERMISSIONS:
                permissions.update(CHATROOM_PERMISSIONS[role]["permissions"])
        return list(permissions)
    
    @staticmethod
    def has_permission(user_roles: List[str], required_permission: str) -> bool:
        """检查用户是否有指定权限"""
        user_permissions = ChatroomPermissionManager.get_user_permissions(user_roles)
        return required_permission in user_permissions
    
    @staticmethod
    def has_chatroom_access(user_roles: List[str]) -> bool:
        """检查用户是否有聊天室访问权限"""
        return ChatroomPermissionManager.has_permission(user_roles, "chatroom_access")
    
    @staticmethod
    def can_create_chatroom(user_roles: List[str]) -> bool:
        """检查用户是否可以创建聊天室"""
        return (ChatroomPermissionManager.has_permission(user_roles, "chatroom_admin") or 
                ChatroomPermissionManager.has_permission(user_roles, "chatroom_create"))
    
    @staticmethod
    def can_manage_chatroom(user_roles: List[str], chatroom_created_by: str = None, user_id: str = None) -> bool:
        """检查用户是否可以管理聊天室"""
        # 系统管理员可以管理所有聊天室
        if ChatroomPermissionManager.has_permission(user_roles, "chatroom_admin"):
            return True
        
        # 聊天室管理员可以管理自己创建的聊天室
        if (ChatroomPermissionManager.has_permission(user_roles, "chatroom_manage") and 
            chatroom_created_by and user_id and chatroom_created_by == user_id):
            return True
            
        return False


def require_chatroom_permission(permission: str):
    """装饰器：要求特定聊天室权限"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # 从JWT token中获取用户信息
                auth_header = request.headers.get('Authorization')
                if not auth_header or not auth_header.startswith('Bearer '):
                    return jsonify({
                        "success": False,
                        "message": "需要认证令牌",
                        "error_code": "AUTH_TOKEN_REQUIRED"
                    }), 401
                
                token = auth_header.split(' ')[1]
                
                # 导入JWT解码所需的密钥
                try:
                    from config import get_config
                    config = get_config()
                    # 使用jwt_secret_key而不是secret_key
                    secret_key = config.security.jwt_secret_key
                except ImportError:
                    # 备用方案：直接从环境变量获取
                    import os
                    secret_key = os.getenv('JWT_SECRET_KEY', os.getenv('SECRET_KEY', 'dev-secret-key-for-testing'))
                
                # 解码JWT token
                if jwt is None:
                    return jsonify({
                        "success": False,
                        "message": "JWT功能不可用",
                        "error_code": "JWT_UNAVAILABLE"
                    }), 500
                
                payload = jwt.decode(token, secret_key, algorithms=["HS256"])
                
                user_id = payload.get("user_id")
                username = payload.get("username")
                user_roles = payload.get("roles", [])
                
                # 如果JWT中没有roles字段，根据用户ID分配默认角色
                if not user_roles:
                    if user_id == "metalhouse":
                        user_roles = ["admin"]  # metalhouse用户默认为管理员
                        logger.info(f"为用户 {user_id} 分配默认管理员角色")
                    else:
                        user_roles = ["chatroom_user"]  # 其他用户默认为聊天室用户
                        logger.info(f"为用户 {user_id} 分配默认用户角色")
                
                if not user_id:
                    return jsonify({
                        "success": False,
                        "message": "无效的认证令牌",
                        "error_code": "INVALID_TOKEN"
                    }), 401
                
                # 检查权限
                if not ChatroomPermissionManager.has_permission(user_roles, permission):
                    return jsonify({
                        "success": False,
                        "message": "没有足够的权限访问此资源",
                        "error_code": "INSUFFICIENT_PERMISSIONS"
                    }), 403
                
                # 将用户信息存储在全局上下文中
                g.current_user = {
                    "id": user_id,
                    "username": username,
                    "roles": user_roles
                }
                
                return func(*args, **kwargs)
                
            except jwt.ExpiredSignatureError:
                return jsonify({
                    "success": False,
                    "message": "认证令牌已过期",
                    "error_code": "TOKEN_EXPIRED"
                }), 401
            except jwt.InvalidTokenError:
                return jsonify({
                    "success": False,
                    "message": "无效的认证令牌",
                    "error_code": "INVALID_TOKEN"
                }), 401
            except Exception as e:
                logger.error(f"权限检查错误: {e}")
                return jsonify({
                    "success": False,
                    "message": "权限验证失败",
                    "error_code": "PERMISSION_CHECK_ERROR"
                }), 500
        
        return wrapper
    return decorator


def get_current_user():
    """获取当前用户信息"""
    return getattr(g, 'current_user', None)


def verify_chatroom_access(user_id: str, user_roles: List[str], chatroom_id: str) -> bool:
    """验证用户对特定聊天室的访问权限"""
    # 检查基础聊天室权限
    if not ChatroomPermissionManager.has_chatroom_access(user_roles):
        return False
    
    # 这里可以添加更多特定聊天室的权限检查逻辑
    # 比如检查用户是否是聊天室成员等
    
    return True


def log_permission_check(user_id: str, permission: str, granted: bool, resource: str = None):
    """记录权限检查日志"""
    log_data = {
        "user_id": user_id,
        "permission": permission,
        "granted": granted,
        "resource": resource,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if granted:
        logger.info(f"权限检查通过: {log_data}")
    else:
        logger.warning(f"权限检查失败: {log_data}")


def setup_chatroom_permissions(app):
    """设置聊天室权限系统"""
    try:
        logger.info("初始化聊天室权限系统...")
        
        # 注册权限管理器到应用上下文
        app.chatroom_permission_manager = ChatroomPermissionManager()
        
        # 添加权限检查中间件
        @app.before_request
        def check_chatroom_permissions():
            """在请求处理前检查聊天室权限"""
            # 只对聊天室相关的API进行权限检查
            if request.path.startswith('/api/chatroom'):
                # 这里可以添加全局的聊天室权限检查逻辑
                pass
        
        logger.info("✅ 聊天室权限系统初始化成功")
        return True
        
    except Exception as e:
        logger.error(f"❌ 聊天室权限系统初始化失败: {e}")
        return False