"""
在线用户管理服务
使用Redis管理聊天室在线用户状态
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import redis

logger = logging.getLogger(__name__)

class OnlineUserManager:
    """在线用户管理器"""
    
    def __init__(self, redis_client: redis.Redis = None):
        """
        初始化在线用户管理器
        
        Args:
            redis_client: Redis客户端实例
        """
        if redis_client:
            self.redis = redis_client
        else:
            # 尝试创建Redis连接
            try:
                from utils.cache_manager import cache_manager
                self.redis = cache_manager.client if hasattr(cache_manager, 'client') else None
            except ImportError:
                try:
                    # 使用聊天室Redis配置创建连接
                    from config import get_chatroom_redis_config
                    redis_config = get_chatroom_redis_config()
                    
                    if redis_config.enabled:
                        self.redis = redis.Redis(
                            host=redis_config.host,
                            port=redis_config.port,
                            db=redis_config.db,
                            password=redis_config.password,
                            decode_responses=redis_config.decode_responses,
                            socket_timeout=redis_config.socket_timeout
                        )
                        # 测试连接
                        self.redis.ping()
                    else:
                        self.redis = None
                except Exception as e:
                    logger.warning(f"Redis连接失败，将使用内存存储: {e}")
                    self.redis = None
        
        # Redis键前缀
        self.online_key_prefix = "chatroom:online:"
        self.user_session_prefix = "user:session:"
        self.chatroom_stats_prefix = "chatroom:stats:"
        
        # 如果没有Redis，使用内存存储
        if not self.redis:
            self._memory_storage = {
                'online_users': {},  # chatroom_id -> {user_id: user_data}
                'user_sessions': {}  # session_id -> user_data
            }
            logger.warning("使用内存存储管理在线用户，重启后数据将丢失")
    
    async def user_join_chatroom(
        self, 
        chatroom_id: str, 
        user_id: str, 
        user_name: str, 
        session_id: str
    ) -> bool:
        """
        用户加入聊天室
        
        Args:
            chatroom_id: 聊天室ID
            user_id: 用户ID
            user_name: 用户名
            session_id: WebSocket会话ID
            
        Returns:
            bool: 是否成功
        """
        try:
            user_data = {
                "user_id": user_id,
                "user_name": user_name,
                "session_id": session_id,
                "joined_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat()
            }
            
            if self.redis:
                # 使用Redis存储
                online_key = f"{self.online_key_prefix}{chatroom_id}"
                session_key = f"{self.user_session_prefix}{session_id}"
                
                # 记录用户在线状态
                self.redis.hset(online_key, user_id, json.dumps(user_data))
                self.redis.expire(online_key, 3600)  # 1小时过期
                
                # 记录用户会话
                session_data = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "chatroom_id": chatroom_id,
                    "joined_at": user_data["joined_at"]
                }
                self.redis.setex(session_key, 3600, json.dumps(session_data))
                
            else:
                # 使用内存存储
                if chatroom_id not in self._memory_storage['online_users']:
                    self._memory_storage['online_users'][chatroom_id] = {}
                
                self._memory_storage['online_users'][chatroom_id][user_id] = user_data
                self._memory_storage['user_sessions'][session_id] = {
                    "user_id": user_id,
                    "user_name": user_name,
                    "chatroom_id": chatroom_id,
                    "joined_at": user_data["joined_at"]
                }
            
            logger.info(f"用户 {user_name}({user_id}) 加入聊天室 {chatroom_id}")
            return True
            
        except Exception as e:
            logger.error(f"用户加入聊天室失败: {e}")
            return False
    
    async def user_leave_chatroom(self, chatroom_id: str, user_id: str) -> bool:
        """
        用户离开聊天室
        
        Args:
            chatroom_id: 聊天室ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        try:
            if self.redis:
                # 从Redis移除
                online_key = f"{self.online_key_prefix}{chatroom_id}"
                self.redis.hdel(online_key, user_id)
                
            else:
                # 从内存移除
                if (chatroom_id in self._memory_storage['online_users'] and 
                    user_id in self._memory_storage['online_users'][chatroom_id]):
                    del self._memory_storage['online_users'][chatroom_id][user_id]
                    
                    # 如果聊天室没有用户了，清理聊天室
                    if not self._memory_storage['online_users'][chatroom_id]:
                        del self._memory_storage['online_users'][chatroom_id]
            
            logger.info(f"用户 {user_id} 离开聊天室 {chatroom_id}")
            return True
            
        except Exception as e:
            logger.error(f"用户离开聊天室失败: {e}")
            return False
    
    async def remove_user_session(self, session_id: str) -> bool:
        """
        移除用户会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否成功
        """
        try:
            if self.redis:
                session_key = f"{self.user_session_prefix}{session_id}"
                
                # 获取会话信息以便清理在线状态
                session_data = self.redis.get(session_key)
                if session_data:
                    session_info = json.loads(session_data)
                    chatroom_id = session_info.get('chatroom_id')
                    user_id = session_info.get('user_id')
                    
                    if chatroom_id and user_id:
                        await self.user_leave_chatroom(chatroom_id, user_id)
                
                # 删除会话
                self.redis.delete(session_key)
                
            else:
                # 从内存移除
                if session_id in self._memory_storage['user_sessions']:
                    session_info = self._memory_storage['user_sessions'][session_id]
                    chatroom_id = session_info.get('chatroom_id')
                    user_id = session_info.get('user_id')
                    
                    if chatroom_id and user_id:
                        await self.user_leave_chatroom(chatroom_id, user_id)
                    
                    del self._memory_storage['user_sessions'][session_id]
            
            return True
            
        except Exception as e:
            logger.error(f"移除用户会话失败: {e}")
            return False
    
    async def get_online_users(self, chatroom_id: str) -> List[Dict]:
        """
        获取聊天室在线用户列表
        
        Args:
            chatroom_id: 聊天室ID
            
        Returns:
            List[Dict]: 在线用户信息列表
        """
        try:
            online_users = []
            
            if self.redis:
                online_key = f"{self.online_key_prefix}{chatroom_id}"
                users_data = self.redis.hgetall(online_key)
                
                for user_id, user_data_str in users_data.items():
                    try:
                        user_data = json.loads(user_data_str)
                        online_users.append({
                            "id": user_data["user_id"],
                            "name": user_data["user_name"],
                            "joined_at": user_data["joined_at"],
                            "last_activity": user_data.get("last_activity", user_data["joined_at"])
                        })
                    except json.JSONDecodeError:
                        logger.warning(f"解析用户数据失败: {user_id}")
                        continue
                        
            else:
                # 从内存获取
                if chatroom_id in self._memory_storage['online_users']:
                    for user_id, user_data in self._memory_storage['online_users'][chatroom_id].items():
                        online_users.append({
                            "id": user_data["user_id"],
                            "name": user_data["user_name"],
                            "joined_at": user_data["joined_at"],
                            "last_activity": user_data.get("last_activity", user_data["joined_at"])
                        })
            
            return online_users
            
        except Exception as e:
            logger.error(f"获取在线用户列表失败: {e}")
            return []
    
    async def update_user_activity(self, chatroom_id: str, user_id: str) -> bool:
        """
        更新用户活动时间
        
        Args:
            chatroom_id: 聊天室ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        try:
            current_time = datetime.utcnow().isoformat()
            
            if self.redis:
                online_key = f"{self.online_key_prefix}{chatroom_id}"
                user_data_str = self.redis.hget(online_key, user_id)
                
                if user_data_str:
                    user_data = json.loads(user_data_str)
                    user_data["last_activity"] = current_time
                    self.redis.hset(online_key, user_id, json.dumps(user_data))
                    
            else:
                # 更新内存中的数据
                if (chatroom_id in self._memory_storage['online_users'] and 
                    user_id in self._memory_storage['online_users'][chatroom_id]):
                    self._memory_storage['online_users'][chatroom_id][user_id]["last_activity"] = current_time
            
            return True
            
        except Exception as e:
            logger.error(f"更新用户活动时间失败: {e}")
            return False
    
    async def get_chatroom_stats(self, chatroom_id: str = None) -> Dict:
        """
        获取聊天室统计信息
        
        Args:
            chatroom_id: 聊天室ID，如果为None则返回所有聊天室统计
            
        Returns:
            Dict: 统计信息
        """
        try:
            if chatroom_id:
                # 获取特定聊天室统计
                online_users = await self.get_online_users(chatroom_id)
                return {
                    "chatroom_id": chatroom_id,
                    "online_count": len(online_users),
                    "online_users": online_users,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                # 获取所有聊天室统计
                all_stats = {}
                
                if self.redis:
                    # 从Redis获取所有聊天室
                    pattern = f"{self.online_key_prefix}*"
                    chatroom_keys = self.redis.keys(pattern)
                    
                    for key in chatroom_keys:
                        room_id = key.replace(self.online_key_prefix, "")
                        online_users = await self.get_online_users(room_id)
                        all_stats[room_id] = {
                            "online_count": len(online_users),
                            "online_users": online_users
                        }
                        
                else:
                    # 从内存获取
                    for room_id in self._memory_storage['online_users']:
                        online_users = await self.get_online_users(room_id)
                        all_stats[room_id] = {
                            "online_count": len(online_users),
                            "online_users": online_users
                        }
                
                return {
                    "total_chatrooms": len(all_stats),
                    "chatrooms": all_stats,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"获取聊天室统计失败: {e}")
            return {}
    
    async def cleanup_expired_users(self, max_inactive_minutes: int = 30):
        """
        清理过期的在线用户
        
        Args:
            max_inactive_minutes: 最大不活跃时间(分钟)
        """
        try:
            current_time = datetime.utcnow()
            expired_threshold = current_time - timedelta(minutes=max_inactive_minutes)
            
            if self.redis:
                # 清理Redis中的过期用户
                pattern = f"{self.online_key_prefix}*"
                chatroom_keys = self.redis.keys(pattern)
                
                for key in chatroom_keys:
                    users_data = self.redis.hgetall(key)
                    for user_id, user_data_str in users_data.items():
                        try:
                            user_data = json.loads(user_data_str)
                            last_activity = datetime.fromisoformat(user_data.get("last_activity", user_data["joined_at"]))
                            
                            if last_activity < expired_threshold:
                                self.redis.hdel(key, user_id)
                                logger.info(f"清理过期用户: {user_id}")
                                
                        except (json.JSONDecodeError, ValueError):
                            # 如果数据格式错误，直接删除
                            self.redis.hdel(key, user_id)
                            logger.warning(f"清理格式错误的用户数据: {user_id}")
                            
            else:
                # 清理内存中的过期用户
                for chatroom_id in list(self._memory_storage['online_users'].keys()):
                    for user_id in list(self._memory_storage['online_users'][chatroom_id].keys()):
                        user_data = self._memory_storage['online_users'][chatroom_id][user_id]
                        try:
                            last_activity = datetime.fromisoformat(user_data.get("last_activity", user_data["joined_at"]))
                            
                            if last_activity < expired_threshold:
                                del self._memory_storage['online_users'][chatroom_id][user_id]
                                logger.info(f"清理过期用户: {user_id}")
                                
                        except ValueError:
                            # 如果时间格式错误，直接删除
                            del self._memory_storage['online_users'][chatroom_id][user_id]
                            logger.warning(f"清理时间格式错误的用户数据: {user_id}")
                    
                    # 如果聊天室没有用户了，清理聊天室
                    if not self._memory_storage['online_users'][chatroom_id]:
                        del self._memory_storage['online_users'][chatroom_id]
                        
        except Exception as e:
            logger.error(f"清理过期用户失败: {e}")
    
    async def cleanup(self, max_inactive_minutes: int = 30):
        """
        清理过期用户的别名方法（兼容性）
        
        Args:
            max_inactive_minutes: 最大不活跃时间(分钟)
        """
        await self.cleanup_expired_users(max_inactive_minutes)

# 创建全局在线用户管理器实例
online_user_manager = OnlineUserManager()
