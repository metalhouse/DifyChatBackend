"""
用户服务模块
处理用户相关的业务逻辑
"""
import json
import hashlib
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
import jwt
from config import get_database_config, get_security_config
from auth.auth_manager import auth_manager
from auth.utils import validate_password_strength, get_client_info, create_session_token

class UserService:
    """用户管理服务"""
    
    def __init__(self, users_file: str = None):
        self.db_config = get_database_config()
        self.security_config = get_security_config()
        self.users_file = users_file or self.db_config.users_file
        
        # 登录尝试记录（内存实现，生产环境建议使用Redis）
        self.login_attempts = {}  # {username: {count, last_attempt, ip_attempts: {ip: count}}}
        
        # 集成JWT认证管理器
        self.auth_manager = auth_manager
    
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

# 全局用户服务实例
user_service = UserService()
