"""
用户服务模块
处理用户相关的业务逻辑
"""
import json
import os
import hashlib
from typing import Optional, Dict, Any
import logging

class UserService:
    """用户管理服务"""
    
    def __init__(self, users_file: str = None):
        self.users_file = users_file or os.path.join(os.path.dirname(__file__), '..', 'users.json')
    
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

# 全局用户服务实例
user_service = UserService()
