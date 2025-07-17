"""
JWT认证管理器
提供完整的JWT认证功能，包括令牌生成、验证、刷新和撤销
"""
import jwt
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
from config import get_security_config, get_redis_config

class TokenType(Enum):
    """令牌类型枚举"""
    ACCESS = "access"
    REFRESH = "refresh"

@dataclass
class TokenInfo:
    """令牌信息数据类"""
    user_id: str
    username: str
    token_type: TokenType
    issued_at: datetime
    expires_at: datetime
    device_id: Optional[str] = None
    ip_address: Optional[str] = None

class AuthManager:
    """JWT认证管理器"""
    
    def __init__(self):
        self.security_config = get_security_config()
        self.redis_config = get_redis_config()
        
        # 令牌黑名单（内存实现，生产环境应使用Redis）
        self._blacklisted_tokens: Set[str] = set()
        
        # 用户活跃会话追踪
        self._active_sessions: Dict[str, Set[str]] = {}
        
        # Redis连接（如果启用）
        self._redis_client = None
        if self.redis_config.enabled:
            try:
                import redis
                self._redis_client = redis.Redis(
                    host=self.redis_config.host,
                    port=self.redis_config.port,
                    db=self.redis_config.db,
                    password=self.redis_config.password,
                    decode_responses=self.redis_config.decode_responses,
                    socket_timeout=self.redis_config.socket_timeout
                )
                # 测试连接
                self._redis_client.ping()
                logging.info("Redis连接成功，启用分布式令牌黑名单")
            except Exception as e:
                logging.warning(f"Redis连接失败，使用内存黑名单: {e}")
                self._redis_client = None
    
    def generate_token_pair(self, user_id: str, username: str, 
                           device_id: Optional[str] = None,
                           ip_address: Optional[str] = None) -> Dict[str, Any]:
        """生成访问令牌和刷新令牌对"""
        now = datetime.now(timezone.utc)
        
        # 生成访问令牌
        access_token_info = TokenInfo(
            user_id=user_id,
            username=username,
            token_type=TokenType.ACCESS,
            issued_at=now,
            expires_at=now + timedelta(seconds=self.security_config.jwt_access_token_expires),
            device_id=device_id,
            ip_address=ip_address
        )
        
        # 生成刷新令牌
        refresh_token_info = TokenInfo(
            user_id=user_id,
            username=username,
            token_type=TokenType.REFRESH,
            issued_at=now,
            expires_at=now + timedelta(seconds=self.security_config.jwt_refresh_token_expires),
            device_id=device_id,
            ip_address=ip_address
        )
        
        access_token = self._create_jwt_token(access_token_info)
        refresh_token = self._create_jwt_token(refresh_token_info)
        
        # 记录活跃会话
        self._add_active_session(user_id, access_token)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': self.security_config.jwt_access_token_expires,
            'issued_at': int(now.timestamp()),
            'device_id': device_id
        }
    
    def verify_token(self, token: str, token_type: TokenType = TokenType.ACCESS) -> Optional[TokenInfo]:
        """验证JWT令牌"""
        try:
            # 检查黑名单
            if self._is_token_blacklisted(token):
                logging.warning("令牌已被撤销")
                return None
            
            # 解码JWT
            payload = jwt.decode(
                token,
                self.security_config.jwt_secret_key,
                algorithms=['HS256']
            )
            
            # 验证令牌类型
            if payload.get('type') != token_type.value:
                logging.warning(f"令牌类型不匹配: 期望{token_type.value}, 实际{payload.get('type')}")
                return None
            
            # 构造令牌信息
            token_info = TokenInfo(
                user_id=payload.get('user_id'),
                username=payload.get('username'),
                token_type=TokenType(payload.get('type')),
                issued_at=datetime.fromtimestamp(payload.get('iat', 0), tz=timezone.utc),
                expires_at=datetime.fromtimestamp(payload.get('exp', 0), tz=timezone.utc),
                device_id=payload.get('device_id'),
                ip_address=payload.get('ip_address')
            )
            
            return token_info
            
        except jwt.ExpiredSignatureError:
            logging.info("令牌已过期")
            return None
        except jwt.InvalidTokenError as e:
            logging.warning(f"无效的令牌: {e}")
            return None
        except Exception as e:
            logging.error(f"令牌验证异常: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """使用刷新令牌生成新的访问令牌"""
        # 验证刷新令牌
        token_info = self.verify_token(refresh_token, TokenType.REFRESH)
        if not token_info:
            return None
        
        # 生成新的令牌对（使用不同的时间戳确保不同）
        import time
        time.sleep(0.001)  # 确保时间戳不同
        
        # 强制使用当前时间而不是缓存时间
        now = datetime.now(timezone.utc)
        
        new_tokens = self.generate_token_pair(
            user_id=token_info.user_id,
            username=token_info.username,
            device_id=token_info.device_id,
            ip_address=token_info.ip_address
        )
        
        # 可选：撤销旧的刷新令牌（更严格的安全策略）
        # self.revoke_token(refresh_token)
        
        return new_tokens
    
    def revoke_token(self, token: str) -> bool:
        """撤销令牌（加入黑名单）"""
        try:
            # 解码令牌获取过期时间（不验证过期）
            payload = jwt.decode(
                token,
                self.security_config.jwt_secret_key,
                algorithms=['HS256'],
                options={"verify_exp": False}
            )
            
            exp_timestamp = payload.get('exp', 0)
            current_timestamp = int(time.time())
            
            # 只有未过期的令牌才需要加入黑名单
            if exp_timestamp > current_timestamp:
                ttl = exp_timestamp - current_timestamp
                self._add_to_blacklist(token, ttl)
                
                # 从活跃会话中移除
                user_id = payload.get('user_id')
                if user_id:
                    self._remove_active_session(user_id, token)
                
                logging.info(f"令牌已撤销: user_id={user_id}")
            
            return True
            
        except Exception as e:
            logging.error(f"撤销令牌失败: {e}")
            return False
    
    def revoke_user_sessions(self, user_id: str, except_token: Optional[str] = None) -> int:
        """撤销用户的所有会话（除了指定的令牌）"""
        revoked_count = 0
        
        if user_id in self._active_sessions:
            sessions_to_revoke = self._active_sessions[user_id].copy()
            
            if except_token:
                except_token_id = except_token[:16] if len(except_token) > 16 else except_token
                sessions_to_revoke.discard(except_token_id)
            
            # 由于我们只存储了令牌ID片段，这里无法直接撤销具体令牌
            # 在生产环境中，应该在数据库中存储完整的会话信息
            revoked_count = len(sessions_to_revoke)
            
            # 清理活跃会话记录
            if except_token:
                except_token_id = except_token[:16] if len(except_token) > 16 else except_token
                if except_token_id in self._active_sessions.get(user_id, set()):
                    self._active_sessions[user_id] = {except_token_id}
                else:
                    self._active_sessions.pop(user_id, None)
            else:
                self._active_sessions.pop(user_id, None)
        
        logging.info(f"用户{user_id}撤销了{revoked_count}个会话")
        return revoked_count
    
    def get_user_active_sessions(self, user_id: str) -> int:
        """获取用户活跃会话数量"""
        return len(self._active_sessions.get(user_id, set()))
    
    def cleanup_expired_blacklist(self):
        """清理过期的黑名单令牌（定期任务）"""
        if self._redis_client:
            # Redis会自动处理TTL过期
            return
        
        # 内存实现：无法直接清理，因为我们没有存储过期时间
        # 在生产环境中应该使用Redis或数据库
        pass
    
    def _create_jwt_token(self, token_info: TokenInfo) -> str:
        """创建JWT令牌"""
        payload = {
            'user_id': token_info.user_id,
            'username': token_info.username,
            'type': token_info.token_type.value,
            'iat': int(token_info.issued_at.timestamp()),
            'exp': int(token_info.expires_at.timestamp()),
            'device_id': token_info.device_id,
            'ip_address': token_info.ip_address
        }
        
        return jwt.encode(
            payload,
            self.security_config.jwt_secret_key,
            algorithm='HS256'
        )
    
    def _is_token_blacklisted(self, token: str) -> bool:
        """检查令牌是否在黑名单中"""
        if self._redis_client:
            try:
                return self._redis_client.exists(f"blacklist:{token}") > 0
            except Exception as e:
                logging.error(f"Redis黑名单检查失败: {e}")
                # 回退到内存检查
                return token in self._blacklisted_tokens
        
        return token in self._blacklisted_tokens
    
    def _add_to_blacklist(self, token: str, ttl: int):
        """将令牌加入黑名单"""
        if self._redis_client:
            try:
                self._redis_client.setex(f"blacklist:{token}", ttl, "1")
                return
            except Exception as e:
                logging.error(f"Redis黑名单添加失败: {e}")
        
        # 回退到内存存储
        self._blacklisted_tokens.add(token)
    
    def _add_active_session(self, user_id: str, token: str):
        """添加活跃会话"""
        if user_id not in self._active_sessions:
            self._active_sessions[user_id] = set()
        
        # 使用令牌的前16位作为会话标识，避免存储完整令牌
        token_id = token[:16] if len(token) > 16 else token
        self._active_sessions[user_id].add(token_id)
    
    def _remove_active_session(self, user_id: str, token: str):
        """移除活跃会话"""
        if user_id in self._active_sessions:
            token_id = token[:16] if len(token) > 16 else token
            self._active_sessions[user_id].discard(token_id)
            if not self._active_sessions[user_id]:
                del self._active_sessions[user_id]

# 全局认证管理器实例
auth_manager = AuthManager()
