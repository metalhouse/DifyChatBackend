"""
用户服务模块 - Task 5.2 现代化增强版
处理用户相关的业务逻辑，包括用户管理、权限控制、密码安全等
"""
import json
import hashlib
import secrets
import string
import os
from typing import Optional, Dict, Any, List, Tuple
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from werkzeug.security import check_password_hash, generate_password_hash
import jwt
from config import get_database_config, get_security_config, get_backup_config
from auth.auth_manager import auth_manager
from auth.utils import validate_password_strength, get_client_info, create_session_token

# Task 5.2 新增：用户状态枚举
class UserStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

# Task 5.2 新增：用户角色枚举
class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"
    GUEST = "guest"

# Task 5.2 新增：用户数据类
@dataclass
class UserData:
    username: str
    password_hash: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    status: UserStatus = UserStatus.ACTIVE
    role: UserRole = UserRole.USER
    created_at: str = None
    updated_at: str = None
    last_login: Optional[str] = None
    login_count: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}

# Task 5.2 新增：密码策略配置
@dataclass
class PasswordPolicy:
    min_length: int = 8
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_numbers: bool = True
    require_special_chars: bool = True
    forbidden_patterns: List[str] = None
    history_limit: int = 5  # 不能重复使用最近几次的密码
    
    def __post_init__(self):
        if self.forbidden_patterns is None:
            self.forbidden_patterns = ["123456", "password", "admin", "user"]

class UserService:
    """
    用户管理服务 - Task 5.2 现代化增强版
    
    提供完整的用户生命周期管理功能：
    - 用户注册、认证、权限管理
    - 密码安全策略和历史管理
    - 登录安全（防暴力破解、设备管理）
    - 用户数据CRUD操作
    - 审计日志和监控
    """
    
    def __init__(self, users_file: str = None):
        self.db_config = get_database_config()
        self.security_config = get_security_config()
        self.users_file = users_file or self.db_config.users_file
        
        # Task 5.2 新增：密码策略
        self.password_policy = PasswordPolicy()
        
        # 登录尝试记录（内存实现，生产环境建议使用Redis）
        self.login_attempts = {}  # {username: {count, last_attempt, ip_attempts: {ip: count}}}
        
        # Task 5.2 新增：密码历史记录
        self.password_history = {}  # {username: [hash1, hash2, ...]}
        
        # 集成JWT认证管理器
        self.auth_manager = auth_manager
        
        # Task 5.2 新增：操作审计日志
        self.audit_log = []
        
        logging.info("[USER SERVICE] Task 5.2 现代化初始化完成 - 支持高级用户管理、密码策略、权限控制")
    
    # ========== Task 5.2 新增：密码安全管理 ==========
    
    def validate_password(self, password: str, username: str = None) -> Tuple[bool, List[str]]:
        """
        验证密码是否符合安全策略
        
        Args:
            password: 待验证的密码
            username: 用户名（用于检查密码历史）
            
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        policy = self.password_policy
        
        # 长度检查
        if len(password) < policy.min_length:
            errors.append(f"密码长度至少需要{policy.min_length}位")
        if len(password) > policy.max_length:
            errors.append(f"密码长度不能超过{policy.max_length}位")
        
        # 字符类型检查
        if policy.require_uppercase and not any(c.isupper() for c in password):
            errors.append("密码必须包含大写字母")
        if policy.require_lowercase and not any(c.islower() for c in password):
            errors.append("密码必须包含小写字母")
        if policy.require_numbers and not any(c.isdigit() for c in password):
            errors.append("密码必须包含数字")
        if policy.require_special_chars and not any(c in string.punctuation for c in password):
            errors.append("密码必须包含特殊字符")
        
        # 弱密码检查
        for pattern in policy.forbidden_patterns:
            if pattern.lower() in password.lower():
                errors.append(f"密码不能包含常见弱密码模式")
                break
        
        # 密码历史检查
        if username and username in self.password_history:
            new_hash = self.hash_password_secure(password)
            history = self.password_history[username]
            if new_hash in history:
                errors.append(f"不能重复使用最近{policy.history_limit}次使用过的密码")
        
        return len(errors) == 0, errors
    
    def hash_password_secure(self, password: str, salt: str = None) -> str:
        """
        安全密码哈希（Task 5.2 增强版）
        使用更安全的哈希算法和盐值
        """
        if salt is None:
            salt = secrets.token_hex(32)  # 生成256位随机盐
        
        # 使用PBKDF2-SHA256进行哈希
        password_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        
        # 100,000次迭代，符合OWASP建议
        hash_bytes = hashlib.pbkdf2_hmac('sha256', password_bytes, salt_bytes, 100000)
        
        # 返回格式：算法$迭代次数$盐$哈希值
        return f"pbkdf2_sha256$100000${salt}${hash_bytes.hex()}"
    
    def verify_password_secure(self, password: str, hashed_password: str) -> bool:
        """
        验证安全哈希密码（Task 5.2 增强版）
        """
        try:
            # 解析哈希格式
            parts = hashed_password.split('$')
            if len(parts) == 4:
                algorithm, iterations, salt, stored_hash = parts
                
                # 重新计算哈希
                calculated_hash = self.hash_password_secure(password, salt)
                
                # 使用恒定时间比较防止时序攻击
                return secrets.compare_digest(calculated_hash, hashed_password)
            else:
                # 兼容旧版本SHA256哈希
                return self.hash_password(password) == hashed_password
                
        except Exception as e:
            logging.error(f"Password verification error: {e}")
            return False
    
    def update_password_history(self, username: str, new_password_hash: str):
        """更新用户密码历史"""
        if username not in self.password_history:
            self.password_history[username] = []
        
        history = self.password_history[username]
        history.append(new_password_hash)
        
        # 只保留最近N次密码
        if len(history) > self.password_policy.history_limit:
            self.password_history[username] = history[-self.password_policy.history_limit:]
    
    # ========== Task 5.2 新增：用户数据管理 ==========
    
    def create_user_advanced(self, username: str, password: str, email: str = None,
                           full_name: str = None, role: UserRole = UserRole.USER,
                           status: UserStatus = UserStatus.ACTIVE, 
                           metadata: Dict[str, Any] = None) -> Tuple[bool, str, Optional[UserData]]:
        """
        高级用户创建功能（Task 5.2 增强版）
        
        Returns:
            (success, message, user_data)
        """
        try:
            # 验证用户名
            if not username or len(username.strip()) == 0:
                return False, "用户名不能为空", None
            
            if len(username) < 3:
                return False, "用户名至少需要3个字符", None
            
            # 检查用户是否已存在
            if self.get_user(username):
                return False, "用户名已存在", None
            
            # 验证密码
            is_valid, password_errors = self.validate_password(password, username)
            if not is_valid:
                return False, "; ".join(password_errors), None
            
            # 验证邮箱（如果提供）
            if email and not self._validate_email(email):
                return False, "邮箱格式不正确", None
            
            # 创建安全密码哈希
            password_hash = self.hash_password_secure(password)
            
            # 创建用户数据
            user_data = UserData(
                username=username,
                password_hash=password_hash,
                email=email,
                full_name=full_name or f"{username}的昵称",
                avatar_url=f"https://api.dicebear.com/7.x/miniavs/svg?seed={username}",
                status=status,
                role=role,
                metadata=metadata or {}
            )
            
            # 保存用户（将枚举转换为字符串）
            users = self.load_users()
            user_dict = asdict(user_data)
            user_dict['status'] = status.value  # 转换枚举为字符串
            user_dict['role'] = role.value      # 转换枚举为字符串
            users[username] = user_dict
            
            if self.save_users(users):
                # 更新密码历史
                self.update_password_history(username, password_hash)
                
                # 记录审计日志
                self._log_audit_event(
                    action="user_created",
                    username=username,
                    details={"role": role.value, "status": status.value}
                )
                
                logging.info(f"User created successfully: {username} (role: {role.value})")
                return True, "用户创建成功", user_data
            else:
                return False, "用户保存失败", None
                
        except Exception as e:
            logging.error(f"Error creating user {username}: {e}")
            return False, f"创建用户时发生错误: {str(e)}", None
    
    def update_user_advanced(self, username: str, **kwargs) -> Tuple[bool, str]:
        """
        高级用户更新功能（Task 5.2 增强版）
        """
        try:
            users = self.load_users()
            
            if username not in users:
                return False, "用户不存在"
            
            current_user = users[username]
            old_values = {}
            
            # 处理特殊字段
            if 'password' in kwargs:
                new_password = kwargs.pop('password')
                is_valid, password_errors = self.validate_password(new_password, username)
                if not is_valid:
                    return False, "; ".join(password_errors)
                
                old_values['password_changed'] = True
                kwargs['password_hash'] = self.hash_password_secure(new_password)
                self.update_password_history(username, kwargs['password_hash'])
            
            if 'email' in kwargs and kwargs['email']:
                if not self._validate_email(kwargs['email']):
                    return False, "邮箱格式不正确"
                old_values['email'] = current_user.get('email')
            
            if 'status' in kwargs:
                if isinstance(kwargs['status'], UserStatus):
                    kwargs['status'] = kwargs['status'].value
                elif isinstance(kwargs['status'], str):
                    try:
                        UserStatus(kwargs['status'])  # 验证状态有效性
                    except ValueError:
                        return False, f"无效的用户状态: {kwargs['status']}"
                old_values['status'] = current_user.get('status')
            
            if 'role' in kwargs:
                if isinstance(kwargs['role'], UserRole):
                    kwargs['role'] = kwargs['role'].value
                elif isinstance(kwargs['role'], str):
                    try:
                        UserRole(kwargs['role'])  # 验证角色有效性
                    except ValueError:
                        return False, f"无效的用户角色: {kwargs['role']}"
                old_values['role'] = current_user.get('role')
            
            # 更新时间戳
            kwargs['updated_at'] = datetime.now().isoformat()
            
            # 更新用户数据
            current_user.update(kwargs)
            users[username] = current_user
            
            if self.save_users(users):
                # 记录审计日志
                self._log_audit_event(
                    action="user_updated",
                    username=username,
                    details={"updated_fields": list(kwargs.keys()), "old_values": old_values}
                )
                
                logging.info(f"User updated successfully: {username}")
                return True, "用户更新成功"
            else:
                return False, "用户保存失败"
                
        except Exception as e:
            logging.error(f"Error updating user {username}: {e}")
            return False, f"更新用户时发生错误: {str(e)}"
    
    def delete_user_safe(self, username: str, soft_delete: bool = True) -> Tuple[bool, str]:
        """
        安全用户删除功能（Task 5.2 增强版）
        
        Args:
            username: 用户名
            soft_delete: 是否软删除（标记为删除而不是物理删除）
        """
        try:
            users = self.load_users()
            
            if username not in users:
                return False, "用户不存在"
            
            # 检查是否是管理员用户
            user_data = users[username]
            if user_data.get('role') == UserRole.ADMIN.value:
                # 检查是否是最后一个管理员
                admin_count = sum(1 for user in users.values() 
                                if user.get('role') == UserRole.ADMIN.value 
                                and user.get('status') == UserStatus.ACTIVE.value)
                
                if admin_count <= 1:
                    return False, "不能删除最后一个管理员用户"
            
            if soft_delete:
                # 软删除：标记状态为已删除
                users[username]['status'] = UserStatus.INACTIVE.value
                users[username]['updated_at'] = datetime.now().isoformat()
                users[username]['metadata'] = users[username].get('metadata', {})
                users[username]['metadata']['deleted_at'] = datetime.now().isoformat()
                
                action = "user_soft_deleted"
                message = "用户已标记为删除"
            else:
                # 硬删除：完全移除用户数据
                del users[username]
                
                # 清理相关数据
                if username in self.login_attempts:
                    del self.login_attempts[username]
                if username in self.password_history:
                    del self.password_history[username]
                
                action = "user_hard_deleted"
                message = "用户已完全删除"
            
            if self.save_users(users):
                # 撤销用户所有会话
                self.revoke_user_sessions(username)
                
                # 记录审计日志
                self._log_audit_event(
                    action=action,
                    username=username,
                    details={"soft_delete": soft_delete}
                )
                
                logging.info(f"User deleted: {username} (soft: {soft_delete})")
                return True, message
            else:
                return False, "用户删除失败"
                
        except Exception as e:
            logging.error(f"Error deleting user {username}: {e}")
            return False, f"删除用户时发生错误: {str(e)}"
    
    # ========== Task 5.2 新增：权限管理 ==========
    
    def check_user_permission(self, username: str, permission: str, resource: str = None) -> bool:
        """
        检查用户权限
        
        Args:
            username: 用户名
            permission: 权限名称 (read, write, delete, admin)
            resource: 资源标识符（可选）
        """
        user = self.get_user(username)
        if not user:
            return False
        
        user_role = UserRole(user.get('role', UserRole.USER.value))
        user_status = UserStatus(user.get('status', UserStatus.ACTIVE.value))
        
        # 检查用户状态
        if user_status != UserStatus.ACTIVE:
            return False
        
        # 管理员拥有所有权限
        if user_role == UserRole.ADMIN:
            return True
        
        # 根据角色和权限检查
        permission_map = {
            UserRole.USER: ['read'],
            UserRole.MODERATOR: ['read', 'write'],
            UserRole.ADMIN: ['read', 'write', 'delete', 'admin']
        }
        
        allowed_permissions = permission_map.get(user_role, [])
        return permission in allowed_permissions
    
    def get_user_roles(self) -> List[str]:
        """获取所有可用角色"""
        return [role.value for role in UserRole]
    
    def get_user_statuses(self) -> List[str]:
        """获取所有可用状态"""
        return [status.value for status in UserStatus]
    
    # ========== Task 5.2 新增：用户查询和统计 ==========
    
    def list_users(self, status: UserStatus = None, role: UserRole = None, 
                   limit: int = None, offset: int = 0) -> Dict[str, Any]:
        """
        获取用户列表（支持过滤和分页）
        """
        users = self.load_users()
        user_list = []
        
        for username, user_data in users.items():
            # 过滤条件
            if status and user_data.get('status') != status.value:
                continue
            if role and user_data.get('role') != role.value:
                continue
            
            # 构建用户信息（不包含敏感信息）
            safe_user_data = {
                'username': username,
                'email': user_data.get('email'),
                'full_name': user_data.get('full_name'),
                'avatar_url': user_data.get('avatar_url'),
                'status': user_data.get('status'),
                'role': user_data.get('role'),
                'created_at': user_data.get('created_at'),
                'updated_at': user_data.get('updated_at'),
                'last_login': user_data.get('last_login'),
                'login_count': user_data.get('login_count', 0)
            }
            user_list.append(safe_user_data)
        
        # 排序（按创建时间倒序）
        user_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # 分页
        total = len(user_list)
        if limit:
            user_list = user_list[offset:offset + limit]
        
        return {
            'users': user_list,
            'total': total,
            'limit': limit,
            'offset': offset
        }
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """获取用户统计信息"""
        users = self.load_users()
        
        stats = {
            'total_users': len(users),
            'by_status': {},
            'by_role': {},
            'recent_registrations': 0,
            'active_sessions': 0
        }
        
        # 统计状态和角色分布
        for user_data in users.values():
            status = user_data.get('status', UserStatus.ACTIVE.value)
            role = user_data.get('role', UserRole.USER.value)
            
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            stats['by_role'][role] = stats['by_role'].get(role, 0) + 1
        
        # 统计最近7天注册用户
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        for user_data in users.values():
            created_at = user_data.get('created_at', '')
            if created_at and created_at > week_ago:
                stats['recent_registrations'] += 1
        
        # 统计活跃会话
        for username in users.keys():
            stats['active_sessions'] += self.get_user_active_sessions(username)
        
        return stats
    
    # ========== Task 5.2 新增：审计和监控 ==========
    
    def _log_audit_event(self, action: str, username: str = None, 
                        details: Dict[str, Any] = None):
        """记录审计事件"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'username': username,
            'details': details or {}
        }
        
        self.audit_log.append(event)
        
        # 只保留最近1000条审计日志
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
        
        logging.info(f"AUDIT: {action} - {username} - {details}")
    
    def get_audit_log(self, username: str = None, action: str = None,
                     limit: int = 100) -> List[Dict[str, Any]]:
        """获取审计日志"""
        filtered_log = self.audit_log
        
        if username:
            filtered_log = [log for log in filtered_log if log.get('username') == username]
        
        if action:
            filtered_log = [log for log in filtered_log if log.get('action') == action]
        
        # 按时间倒序返回
        filtered_log.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return filtered_log[:limit]
    
    # ========== Task 5.2 新增：辅助方法 ==========
    
    def _validate_email(self, email: str) -> bool:
        """简单的邮箱格式验证"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def load_users(self) -> Dict[str, Any]:
        """加载用户数据（Task 5.2 增强版）"""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 数据迁移：将旧格式升级为新格式
            migrated_data = {}
            for username, user_data in data.items():
                if isinstance(user_data, dict):
                    # 确保包含必要字段
                    migrated_user = {
                        'username': username,
                        'password_hash': user_data.get('password_hash') or user_data.get('password', ''),  # 优先使用password_hash，兼容旧字段名password
                        'email': user_data.get('email'),
                        'full_name': user_data.get('full_name', f"{username}的昵称"),
                        'avatar_url': user_data.get('avatar_url', f"https://api.dicebear.com/7.x/miniavs/svg?seed={username}"),
                        'status': user_data.get('status', UserStatus.ACTIVE.value),
                        'role': user_data.get('role', UserRole.USER.value),
                        'created_at': user_data.get('created_at', datetime.now().isoformat()),
                        'updated_at': user_data.get('updated_at', datetime.now().isoformat()),
                        'last_login': user_data.get('last_login'),
                        'login_count': user_data.get('login_count', 0),
                        'metadata': user_data.get('metadata', {})
                    }
                    migrated_data[username] = migrated_user
                else:
                    # 处理非常旧的数据格式
                    migrated_data[username] = {
                        'username': username,
                        'password_hash': str(user_data),
                        'full_name': f"{username}的昵称",
                        'avatar_url': f"https://api.dicebear.com/7.x/miniavs/svg?seed={username}",
                        'status': UserStatus.ACTIVE.value,
                        'role': UserRole.USER.value,
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat(),
                        'login_count': 0,
                        'metadata': {}
                    }
            
            return migrated_data
                
        except FileNotFoundError:
            logging.warning(f"Users file not found: {self.users_file}")
            return {}
        except Exception as e:
            logging.error(f"Error loading users: {e}")
            return {}
    
    def save_users(self, users_data: Dict[str, Any]) -> bool:
        """保存用户数据（Task 5.2 增强版）"""
        try:
            backup_config = get_backup_config()
            
            # 检查是否启用备份
            if backup_config.enabled and backup_config.backup_on_save:
                # 创建备份
                import shutil
                import glob
                backup_file = f"{self.users_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                try:
                    shutil.copy2(self.users_file, backup_file)
                except FileNotFoundError:
                    pass  # 原文件不存在，无需备份
                
                # 清理旧备份文件，根据配置保留指定数量
                backup_pattern = f"{self.users_file}.backup.*"
                backup_files = glob.glob(backup_pattern)
                if len(backup_files) > backup_config.max_backup_files:
                    # 按文件名排序（包含时间戳，自然排序即为时间顺序）
                    backup_files.sort()
                    # 删除最旧的备份文件
                    files_to_delete = backup_files[:-backup_config.max_backup_files]  # 保留最新的指定数量
                    for old_backup in files_to_delete:
                        try:
                            os.remove(old_backup)
                            logging.info(f"Removed old backup: {old_backup}")
                        except OSError as e:
                            logging.warning(f"Failed to remove old backup {old_backup}: {e}")
                            
                logging.info(f"Users data saved successfully, backup created: {backup_file}")
            else:
                logging.info("Users data saved successfully, backup disabled by configuration")
            
            # 保存数据
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logging.error(f"Error saving users: {e}")
            return False
    
    def hash_password(self, password: str) -> str:
        """密码哈希（兼容性方法，建议使用 hash_password_secure）"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """验证密码（兼容性方法，自动选择验证方式）"""
        # 优先使用安全验证方法
        if '$' in hashed_password and len(hashed_password.split('$')) == 4:
            return self.verify_password_secure(password, hashed_password)
        else:
            # 兼容旧版本哈希
            return self.hash_password(password) == hashed_password
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """获取用户信息（Task 5.2 增强版）"""
        users = self.load_users()
        user_data = users.get(username)
        
        if user_data:
            # 确保返回的用户信息不包含密码哈希
            safe_user_data = dict(user_data)
            safe_user_data.pop('password_hash', None)
            safe_user_data.pop('password', None)  # 兼容旧字段名
            return safe_user_data
        
        return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """用户认证（Task 5.2 增强版）"""
        users = self.load_users()
        user_data = users.get(username)
        
        if not user_data:
            return None
        
        # 检查用户状态
        status = UserStatus(user_data.get('status', UserStatus.ACTIVE.value))
        if status != UserStatus.ACTIVE:
            logging.warning(f"Authentication failed for inactive user: {username} (status: {status.value})")
            return None
        
        # 验证密码
        stored_password = user_data.get('password_hash') or user_data.get('password', '')
        if self.verify_password(password, stored_password):
            # 更新登录信息
            user_data['last_login'] = datetime.now().isoformat()
            user_data['login_count'] = user_data.get('login_count', 0) + 1
            users[username] = user_data
            self.save_users(users)
            
            return {
                'username': username,
                'user_id': username,
                'user_name': user_data.get('full_name', f"{username}的昵称"),
                'avatar_url': user_data.get('avatar_url', f"https://api.dicebear.com/7.x/miniavs/svg?seed={username}"),
                'role': user_data.get('role', UserRole.USER.value),
                'email': user_data.get('email')
            }
        
        return None
    
    def create_user(self, username: str, password: str, **kwargs) -> bool:
        """创建用户（兼容性方法，建议使用 create_user_advanced）"""
        success, message, _ = self.create_user_advanced(
            username=username,
            password=password,
            email=kwargs.get('email'),
            full_name=kwargs.get('full_name'),
            role=UserRole(kwargs.get('role', UserRole.USER.value)),
            status=UserStatus(kwargs.get('status', UserStatus.ACTIVE.value)),
            metadata=kwargs.get('metadata')
        )
        
        if not success:
            logging.error(f"Failed to create user {username}: {message}")
        
        return success
    
    def update_user(self, username: str, **kwargs) -> bool:
        """更新用户信息（兼容性方法，建议使用 update_user_advanced）"""
        success, message = self.update_user_advanced(username, **kwargs)
        
        if not success:
            logging.error(f"Failed to update user {username}: {message}")
        
        return success
    
    def delete_user(self, username: str) -> bool:
        """删除用户（兼容性方法，建议使用 delete_user_safe）"""
        success, message = self.delete_user_safe(username, soft_delete=False)
        
        if not success:
            logging.error(f"Failed to delete user {username}: {message}")
        
        return success
    
    def is_account_locked(self, username: str, ip_address: str = None) -> Dict[str, Any]:
        """检查账户是否被锁定（支持用户级和IP级锁定）"""
        result = {
            'locked': False,
            'reason': '',
            'remaining_time': 0,
            'attempts_left': self.security_config.max_login_attempts
        }
        
        if username not in self.login_attempts:
            return result
        
        attempts_data = self.login_attempts[username]
        now = datetime.now()
        
        # 检查用户级锁定
        if attempts_data['count'] >= self.security_config.max_login_attempts:
            time_since_last = now - attempts_data['last_attempt']
            remaining_time = self.security_config.lockout_duration - time_since_last.total_seconds()
            
            if remaining_time > 0:
                result.update({
                    'locked': True,
                    'reason': 'account_locked',
                    'remaining_time': int(remaining_time),
                    'attempts_left': 0
                })
                return result
        
        # 检查IP级锁定
        if ip_address and 'ip_attempts' in attempts_data:
            ip_count = attempts_data['ip_attempts'].get(ip_address, 0)
            if ip_count >= self.security_config.max_login_attempts:
                # IP锁定时间通常更短
                ip_lockout_duration = min(self.security_config.lockout_duration, 900)  # 最多15分钟
                time_since_last = now - attempts_data['last_attempt']
                remaining_time = ip_lockout_duration - time_since_last.total_seconds()
                
                if remaining_time > 0:
                    result.update({
                        'locked': True,
                        'reason': 'ip_locked',
                        'remaining_time': int(remaining_time),
                        'attempts_left': 0
                    })
                    return result
        
        # 计算剩余尝试次数
        result['attempts_left'] = max(0, self.security_config.max_login_attempts - attempts_data['count'])
        
        return result
    
    def record_login_attempt(self, username: str, success: bool = False, ip_address: str = None, 
                            device_info: Dict[str, str] = None):
        """记录登录尝试（包含IP和设备信息）"""
        now = datetime.now()
        
        if username not in self.login_attempts:
            self.login_attempts[username] = {
                'count': 0, 
                'last_attempt': now,
                'ip_attempts': {},
                'device_history': [],
                'successful_logins': []
            }
        
        attempts_data = self.login_attempts[username]
        
        if success:
            # 登录成功，清除失败记录但保留成功记录
            attempts_data['count'] = 0
            attempts_data['ip_attempts'] = {}
            
            # 记录成功登录
            login_record = {
                'timestamp': now.isoformat(),
                'ip_address': ip_address,
                'device_info': device_info or {},
                'success': True
            }
            
            attempts_data['successful_logins'].append(login_record)
            
            # 只保留最近10次成功登录记录
            if len(attempts_data['successful_logins']) > 10:
                attempts_data['successful_logins'] = attempts_data['successful_logins'][-10:]
            
            # 更新设备历史
            if device_info:
                device_record = {
                    'device_id': device_info.get('device_id'),
                    'user_agent': device_info.get('user_agent'),
                    'last_login': now.isoformat(),
                    'ip_address': ip_address
                }
                
                # 更新或添加设备记录
                existing_device = None
                for i, device in enumerate(attempts_data['device_history']):
                    if device.get('device_id') == device_info.get('device_id'):
                        existing_device = i
                        break
                
                if existing_device is not None:
                    attempts_data['device_history'][existing_device] = device_record
                else:
                    attempts_data['device_history'].append(device_record)
                
                # 只保留最近5个设备
                if len(attempts_data['device_history']) > 5:
                    attempts_data['device_history'] = attempts_data['device_history'][-5:]
        else:
            # 登录失败，增加尝试次数
            attempts_data['count'] += 1
            attempts_data['last_attempt'] = now
            
            # 记录IP级别的失败次数
            if ip_address:
                if 'ip_attempts' not in attempts_data:
                    attempts_data['ip_attempts'] = {}
                attempts_data['ip_attempts'][ip_address] = attempts_data['ip_attempts'].get(ip_address, 0) + 1
        
        self.login_attempts[username] = attempts_data
        
        logging.info(f"Login attempt for {username}: success={success}, ip={ip_address}, "
                    f"total_attempts={attempts_data['count']}")
    
    def get_user_login_history(self, username: str) -> Dict[str, Any]:
        """获取用户登录历史"""
        if username not in self.login_attempts:
            return {
                'successful_logins': [],
                'device_history': [],
                'current_failed_attempts': 0
            }
        
        attempts_data = self.login_attempts[username]
        return {
            'successful_logins': attempts_data.get('successful_logins', []),
            'device_history': attempts_data.get('device_history', []),
            'current_failed_attempts': attempts_data.get('count', 0)
        }
    
    def generate_tokens(self, username: str, device_info: Dict[str, str] = None, 
                       remember_me: bool = False) -> Dict[str, Any]:
        """生成JWT访问令牌和刷新令牌（使用新的认证管理器）"""
        user = self.get_user(username)
        if not user:
            raise ValueError("用户不存在")
        
        # 获取客户端信息
        client_info = device_info or get_client_info()
        
        # 使用认证管理器生成令牌
        token_pair = self.auth_manager.generate_token_pair(
            user_id=username,
            username=username,
            device_id=client_info.get('device_id'),
            ip_address=client_info.get('ip_address')
        )
        
        # 如果选择记住登录，可以延长刷新令牌有效期
        if remember_me:
            # 这里可以实现记住登录的逻辑
            # 例如生成更长期的刷新令牌
            pass
        
        return token_pair
    
    def verify_token(self, token: str, token_type: str = 'access') -> Optional[Dict[str, Any]]:
        """验证JWT令牌（使用新的认证管理器）"""
        from auth.auth_manager import TokenType
        
        # 转换令牌类型
        jwt_token_type = TokenType.ACCESS if token_type == 'access' else TokenType.REFRESH
        
        # 使用认证管理器验证令牌
        token_info = self.auth_manager.verify_token(token, jwt_token_type)
        
        if not token_info:
            return None
        
        # 检查用户是否仍然存在
        username = token_info.username
        if not username or not self.get_user(username):
            return None
        
        return {
            'user_id': token_info.user_id,
            'username': token_info.username,
            'device_id': token_info.device_id,
            'ip_address': token_info.ip_address,
            'issued_at': token_info.issued_at,
            'expires_at': token_info.expires_at
        }
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """使用刷新令牌生成新的访问令牌（使用新的认证管理器）"""
        return self.auth_manager.refresh_access_token(refresh_token)
    
    def revoke_token(self, token: str) -> bool:
        """撤销令牌（使用新的认证管理器）"""
        return self.auth_manager.revoke_token(token)
    
    def revoke_user_sessions(self, username: str, except_current_token: str = None) -> int:
        """撤销用户的所有会话"""
        return self.auth_manager.revoke_user_sessions(username, except_current_token)
    
    def get_user_active_sessions(self, username: str) -> int:
        """获取用户活跃会话数量"""
        return self.auth_manager.get_user_active_sessions(username)
    
    def authenticate_with_security(self, username: str, password: str, 
                                  client_info: Dict[str, str] = None,
                                  remember_me: bool = False,
                                  validate_password_strength: bool = False) -> Dict[str, Any]:
        """带安全检查的用户认证（增强版）"""
        
        # 获取客户端信息
        if not client_info:
            client_info = get_client_info()
        
        ip_address = client_info.get('ip_address', 'unknown')
        device_id = client_info.get('device_id', 'unknown')
        user_agent = client_info.get('user_agent', 'unknown')
        
        # 记录登录尝试开始
        logging.info(f"Login attempt started: username={username}, ip={ip_address}, "
                    f"device_id={device_id[:16]}..., user_agent={user_agent[:50]}...")
        
        # 1. 检查账户和IP锁定状态
        lock_status = self.is_account_locked(username, ip_address)
        if lock_status['locked']:
            reason_msg = {
                'account_locked': f'账户已被锁定，请{lock_status["remaining_time"]}秒后重试',
                'ip_locked': f'该IP地址已被锁定，请{lock_status["remaining_time"]}秒后重试'
            }
            
            return {
                'success': False,
                'message': reason_msg.get(lock_status['reason'], '账户已被锁定'),
                'error_code': 'ACCOUNT_LOCKED' if lock_status['reason'] == 'account_locked' else 'IP_LOCKED',
                'remaining_time': lock_status['remaining_time'],
                'attempts_left': 0
            }
        
        # 2. 密码强度验证（可选，通常用于注册或密码修改）
        if validate_password_strength:
            password_result = validate_password_strength(password)
            if not password_result['is_valid']:
                return {
                    'success': False,
                    'message': f'密码强度不足: {", ".join(password_result["feedback"])}',
                    'error_code': 'WEAK_PASSWORD',
                    'password_feedback': password_result['feedback']
                }
        
        # 3. 尝试用户认证
        user_info = self.authenticate_user(username, password)
        
        if user_info:
            # 认证成功
            try:
                # 生成JWT令牌
                tokens = self.generate_tokens(username, client_info, remember_me)
                
                # 记录成功登录
                self.record_login_attempt(
                    username, 
                    success=True, 
                    ip_address=ip_address,
                    device_info=client_info
                )
                
                # 获取用户会话信息
                active_sessions = self.get_user_active_sessions(username)
                login_history = self.get_user_login_history(username)
                
                # 构建响应
                response = {
                    'success': True,
                    'message': '登录成功',
                    'user': user_info,
                    'tokens': tokens,
                    'session_info': {
                        'active_sessions': active_sessions,
                        'device_id': device_id,
                        'login_time': datetime.now().isoformat(),
                        'ip_address': ip_address,
                        'remember_me': remember_me
                    }
                }
                
                # 添加设备历史信息（如果是新设备则提醒）
                if login_history['device_history']:
                    known_devices = [d.get('device_id') for d in login_history['device_history']]
                    if device_id not in known_devices:
                        response['warnings'] = ['检测到新设备登录，如非本人操作请立即修改密码']
                
                logging.info(f"Login successful: username={username}, device_id={device_id[:16]}..., "
                           f"active_sessions={active_sessions}")
                
                return response
                
            except Exception as e:
                logging.error(f"Token generation failed for user {username}: {e}")
                return {
                    'success': False,
                    'message': '登录处理异常，请稍后重试',
                    'error_code': 'TOKEN_GENERATION_FAILED'
                }
        else:
            # 认证失败
            self.record_login_attempt(
                username, 
                success=False, 
                ip_address=ip_address,
                device_info=client_info
            )
            
            # 获取更新后的锁定状态
            lock_status = self.is_account_locked(username, ip_address)
            attempts_left = lock_status['attempts_left']
            
            error_message = f'用户名或密码错误'
            if attempts_left > 0:
                error_message += f'，剩余尝试次数：{attempts_left}'
            else:
                error_message += f'，账户已被锁定'
            
            logging.warning(f"Login failed: username={username}, ip={ip_address}, "
                          f"attempts_left={attempts_left}")
            
            return {
                'success': False,
                'message': error_message,
                'error_code': 'INVALID_CREDENTIALS',
                'attempts_left': attempts_left
            }
    
    def logout_user(self, token: str, logout_all_devices: bool = False) -> Dict[str, Any]:
        """用户登出（支持单设备或全设备登出）"""
        try:
            # 验证令牌获取用户信息
            token_info = self.verify_token(token, 'access')
            if not token_info:
                return {
                    'success': False,
                    'message': '无效的访问令牌',
                    'error_code': 'INVALID_TOKEN'
                }
            
            username = token_info['username']
            
            if logout_all_devices:
                # 撤销用户所有会话
                revoked_count = self.revoke_user_sessions(username)
                logging.info(f"User {username} logged out from all devices: {revoked_count} sessions")
                
                return {
                    'success': True,
                    'message': f'已从所有设备退出登录（{revoked_count}个会话）',
                    'revoked_sessions': revoked_count
                }
            else:
                # 只撤销当前令牌
                revoked = self.revoke_token(token)
                
                if revoked:
                    active_sessions = self.get_user_active_sessions(username)
                    logging.info(f"User {username} logged out from current device, "
                               f"remaining sessions: {active_sessions}")
                    
                    return {
                        'success': True,
                        'message': '退出登录成功',
                        'remaining_sessions': active_sessions
                    }
                else:
                    return {
                        'success': False,
                        'message': '退出登录失败',
                        'error_code': 'LOGOUT_FAILED'
                    }
                    
        except Exception as e:
            logging.error(f"Logout error: {e}")
            return {
                'success': False,
                'message': '退出登录异常',
                'error_code': 'LOGOUT_ERROR'
            }

# Task 5.2 增强：全局用户服务实例（现代化用户管理）
user_service = UserService()

# ========== Task 5.2 新增：用户管理API帮助函数 ==========

def create_default_admin_user(username: str = "admin", password: str = "admin123456") -> bool:
    """创建默认管理员用户（用于系统初始化）"""
    try:
        # 检查是否已存在管理员
        users = user_service.load_users()
        admin_exists = any(
            user.get('role') == UserRole.ADMIN.value 
            for user in users.values()
        )
        
        if admin_exists:
            logging.info("Admin user already exists, skipping creation")
            return True
        
        # 创建管理员用户
        success, message, _ = user_service.create_user_advanced(
            username=username,
            password=password,
            email="admin@example.com",
            full_name="系统管理员",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            metadata={"created_by": "system_init"}
        )
        
        if success:
            logging.info(f"Default admin user created: {username}")
        else:
            logging.error(f"Failed to create default admin user: {message}")
        
        return success
        
    except Exception as e:
        logging.error(f"Error creating default admin user: {e}")
        return False

def validate_user_access(username: str, required_role: UserRole = UserRole.USER, 
                        required_status: UserStatus = UserStatus.ACTIVE) -> Tuple[bool, str]:
    """验证用户访问权限的帮助函数"""
    try:
        users = user_service.load_users()
        user_data = users.get(username)
        
        if not user_data:
            return False, "用户不存在"
        
        user_status = UserStatus(user_data.get('status', UserStatus.ACTIVE.value))
        user_role = UserRole(user_data.get('role', UserRole.USER.value))
        
        if user_status != required_status:
            return False, f"用户状态不符合要求: {user_status.value}"
        
        # 角色权限检查（管理员拥有所有权限）
        if user_role == UserRole.ADMIN:
            return True, "管理员权限验证通过"
        
        role_hierarchy = {
            UserRole.GUEST: 0,
            UserRole.USER: 1,
            UserRole.MODERATOR: 2,
            UserRole.ADMIN: 3
        }
        
        if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 0):
            return False, f"用户权限不足: 需要{required_role.value}权限"
        
        return True, "权限验证通过"
        
    except Exception as e:
        logging.error(f"Error validating user access for {username}: {e}")
        return False, f"权限验证异常: {str(e)}"

# Task 5.2 完成标记
logging.info("[TASK 5.2] 用户服务实现 - 现代化用户管理系统启动完成")
logging.info("[TASK 5.2] 功能包括: 高级用户CRUD、密码安全策略、权限管理、审计日志")
