"""
用户服务模块
处理用户相关的业务逻辑
"""
import json
import hashlib
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
import jwt
from config import get_database_config, get_security_config

class UserService:
    """用户管理服务"""
    
    def __init__(self, users_file: str = None):
        self.db_config = get_database_config()
        self.security_config = get_security_config()
        self.users_file = users_file or self.db_config.users_file
        self.login_attempts = {}  # 登录尝试记录（内存实现）
    
    def load_users(self) -> Dict[str, Any]:
        """加载用户数据"""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.warning(f"Users file not found: {self.users_file}")
            return {}
        except Exception as e:
            logging.error(f"Error loading users: {e}")
            return {}
    
    def save_users(self, users_data: Dict[str, Any]) -> bool:
        """保存用户数据"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logging.error(f"Error saving users: {e}")
            return False
    
    def hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.hash_password(password) == hashed_password
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        users = self.load_users()
        return users.get(username)
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """用户认证"""
        user = self.get_user(username)
        if not user:
            return None
        
        if self.verify_password(password, user['password']):
            return {
                'username': username,
                'user_id': username,
                'user_name': f"{username}的昵称",
                'avatar_url': f"https://api.dicebear.com/7.x/miniavs/svg?seed={username}"
            }
        return None
    
    def create_user(self, username: str, password: str, **kwargs) -> bool:
        """创建用户"""
        users = self.load_users()
        
        if username in users:
            return False
        
        users[username] = {
            'password': self.hash_password(password),
            **kwargs
        }
        
        return self.save_users(users)
    
    def update_user(self, username: str, **kwargs) -> bool:
        """更新用户信息"""
        users = self.load_users()
        
        if username not in users:
            return False
        
        users[username].update(kwargs)
        return self.save_users(users)
    
    def delete_user(self, username: str) -> bool:
        """删除用户"""
        users = self.load_users()
        
        if username not in users:
            return False
        
        del users[username]
        return self.save_users(users)
    
    def is_account_locked(self, username: str) -> bool:
        """检查账户是否被锁定"""
        if username not in self.login_attempts:
            return False
        
        attempts_data = self.login_attempts[username]
        if attempts_data['count'] >= self.security_config.max_login_attempts:
            time_since_last = datetime.now() - attempts_data['last_attempt']
            return time_since_last.total_seconds() < self.security_config.lockout_duration
        
        return False
    
    def record_login_attempt(self, username: str, success: bool = False):
        """记录登录尝试"""
        now = datetime.now()
        
        if username not in self.login_attempts:
            self.login_attempts[username] = {'count': 0, 'last_attempt': now}
        
        if success:
            # 登录成功，清除尝试记录
            del self.login_attempts[username]
        else:
            # 登录失败，增加尝试次数
            self.login_attempts[username]['count'] += 1
            self.login_attempts[username]['last_attempt'] = now
            
        logging.info(f"Login attempt for {username}: success={success}")
    
    def generate_tokens(self, username: str) -> Dict[str, str]:
        """生成JWT访问令牌和刷新令牌"""
        now = datetime.utcnow()
        user = self.get_user(username)
        
        if not user:
            raise ValueError("用户不存在")
        
        # 访问令牌有效载荷
        access_payload = {
            'user_id': username,
            'username': username,
            'type': 'access',
            'iat': now,
            'exp': now + timedelta(seconds=self.security_config.jwt_access_token_expires)
        }
        
        # 刷新令牌有效载荷
        refresh_payload = {
            'user_id': username,
            'username': username,
            'type': 'refresh',
            'iat': now,
            'exp': now + timedelta(seconds=self.security_config.jwt_refresh_token_expires)
        }
        
        try:
            access_token = jwt.encode(
                access_payload, 
                self.security_config.jwt_secret_key, 
                algorithm='HS256'
            )
            refresh_token = jwt.encode(
                refresh_payload, 
                self.security_config.jwt_secret_key, 
                algorithm='HS256'
            )
            
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': self.security_config.jwt_access_token_expires
            }
        except Exception as e:
            logging.error(f"Token generation failed: {e}")
            raise ValueError("令牌生成失败")
    
    def verify_token(self, token: str, token_type: str = 'access') -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(
                token, 
                self.security_config.jwt_secret_key, 
                algorithms=['HS256']
            )
            
            # 检查令牌类型
            if payload.get('type') != token_type:
                return None
            
            # 检查用户是否仍然存在
            username = payload.get('username')
            if not username or not self.get_user(username):
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logging.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logging.warning(f"Invalid token: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """使用刷新令牌生成新的访问令牌"""
        payload = self.verify_token(refresh_token, 'refresh')
        if not payload:
            return None
        
        username = payload.get('username')
        return self.generate_tokens(username)
    
    def revoke_token(self, token: str) -> bool:
        """撤销令牌（需要实现令牌黑名单机制）"""
        # TODO: 实现令牌黑名单，可以使用Redis存储
        # 目前返回True表示操作成功
        return True
    
    def authenticate_with_security(self, username: str, password: str) -> Dict[str, Any]:
        """带安全检查的用户认证"""
        # 检查账户是否被锁定
        if self.is_account_locked(username):
            remaining_time = self.security_config.lockout_duration
            if username in self.login_attempts:
                time_since_last = datetime.now() - self.login_attempts[username]['last_attempt']
                remaining_time = max(0, self.security_config.lockout_duration - time_since_last.total_seconds())
            
            return {
                'success': False,
                'message': f'账户已被锁定，请{int(remaining_time)}秒后重试',
                'error_code': 'ACCOUNT_LOCKED'
            }
        
        # 尝试认证
        user_info = self.authenticate_user(username, password)
        
        if user_info:
            # 认证成功
            self.record_login_attempt(username, success=True)
            tokens = self.generate_tokens(username)
            
            return {
                'success': True,
                'message': '登录成功',
                'user': user_info,
                'tokens': tokens
            }
        else:
            # 认证失败
            self.record_login_attempt(username, success=False)
            attempts_left = self.security_config.max_login_attempts
            if username in self.login_attempts:
                attempts_left = max(0, self.security_config.max_login_attempts - self.login_attempts[username]['count'])
            
            return {
                'success': False,
                'message': f'用户名或密码错误，剩余尝试次数：{attempts_left}',
                'error_code': 'INVALID_CREDENTIALS',
                'attempts_left': attempts_left
            }

# 全局用户服务实例
user_service = UserService()
