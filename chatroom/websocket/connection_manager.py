"""
WebSocket连接管理器
处理聊天室的实时通信
"""
import json
import asyncio
import logging
from typing import Dict, Set, Optional, List
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储所有活跃连接 {user_id: websocket}
        self.active_connections: Dict[str, object] = {}
        
        # 聊天室用户映射 {chatroom_id: {user_id}}
        self.chatroom_users: Dict[str, Set[str]] = {}
        
        # 用户当前聊天室映射 {user_id: chatroom_id}
        self.user_chatrooms: Dict[str, str] = {}
        
        # 用户会话映射 {user_id: session_info}
        self.user_sessions: Dict[str, Dict] = {}
        
        logger.info("WebSocket连接管理器初始化完成")
    
    async def connect(self, websocket: object, user_id: str, user_name: str, session_id: str = None):
        """
        建立WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            user_id: 用户ID
            user_name: 用户名
            session_id: 会话ID
        """
        try:
            # 如果用户已有连接，先断开旧连接
            if user_id in self.active_connections:
                await self.disconnect(user_id, notify_others=False)
            
            # 生成会话ID
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # 存储连接信息
            self.active_connections[user_id] = websocket
            self.user_sessions[user_id] = {
                "session_id": session_id,
                "user_name": user_name,
                "connected_at": datetime.utcnow(),
                "last_activity": datetime.utcnow()
            }
            
            logger.info(f"用户 {user_name}({user_id}) 建立WebSocket连接")
            
            # 发送连接成功消息
            await self.send_to_user(user_id, {
                "type": "connected",
                "data": {
                    "message": "连接成功",
                    "user_id": user_id,
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"WebSocket连接建立失败: {e}")
            raise
    
    async def disconnect(self, user_id: str, notify_others: bool = True):
        """
        断开WebSocket连接
        
        Args:
            user_id: 用户ID
            notify_others: 是否通知其他用户
        """
        try:
            # 获取用户信息
            session_info = self.user_sessions.get(user_id, {})
            user_name = session_info.get("user_name", "Unknown")
            
            # 从连接池移除
            if user_id in self.active_connections:
                del self.active_connections[user_id]
            
            # 从会话信息移除
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            
            # 从聊天室中移除用户
            current_chatroom = self.user_chatrooms.get(user_id)
            if current_chatroom:
                await self.leave_chatroom(user_id, current_chatroom, notify_others)
            
            logger.info(f"用户 {user_name}({user_id}) 断开WebSocket连接")
            
        except Exception as e:
            logger.error(f"WebSocket断开连接处理失败: {e}")
    
    async def send_to_user(self, user_id: str, message: Dict) -> bool:
        """
        发送消息给特定用户
        
        Args:
            user_id: 用户ID
            message: 消息内容
            
        Returns:
            bool: 是否发送成功
        """
        try:
            if user_id in self.active_connections:
                websocket = self.active_connections[user_id]
                
                # 添加时间戳和消息ID
                message.update({
                    "timestamp": datetime.utcnow().isoformat(),
                    "message_id": str(uuid.uuid4())
                })
                
                # 根据WebSocket库的不同，这里的发送方法可能不同
                # 这里假设使用类似 websocket.send_text 的方法
                if hasattr(websocket, 'send_text'):
                    await websocket.send_text(json.dumps(message, ensure_ascii=False))
                elif hasattr(websocket, 'send'):
                    await websocket.send(json.dumps(message, ensure_ascii=False))
                else:
                    # 兼容不同的WebSocket实现
                    await websocket.send(json.dumps(message, ensure_ascii=False))
                
                # 更新用户活动时间
                if user_id in self.user_sessions:
                    self.user_sessions[user_id]["last_activity"] = datetime.utcnow()
                
                return True
            else:
                logger.warning(f"尝试向不存在的连接发送消息: {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"发送消息给用户 {user_id} 失败: {e}")
            # 如果发送失败，可能连接已断开，清理连接
            await self.disconnect(user_id, notify_others=False)
            return False
    
    async def broadcast_to_chatroom(self, chatroom_id: str, message: Dict, exclude_user: str = None):
        """
        向聊天室广播消息
        
        Args:
            chatroom_id: 聊天室ID
            message: 消息内容
            exclude_user: 排除的用户ID(比如消息发送者)
        """
        try:
            if chatroom_id not in self.chatroom_users:
                logger.warning(f"尝试向不存在的聊天室广播消息: {chatroom_id}")
                return
            
            users = self.chatroom_users[chatroom_id].copy()  # 复制避免并发修改
            success_count = 0
            
            for user_id in users:
                if exclude_user and user_id == exclude_user:
                    continue
                
                if await self.send_to_user(user_id, message):
                    success_count += 1
            
            logger.debug(f"聊天室 {chatroom_id} 广播消息成功发送给 {success_count} 个用户")
            
        except Exception as e:
            logger.error(f"聊天室广播失败: {e}")
    
    async def join_chatroom(self, user_id: str, chatroom_id: str) -> bool:
        """
        用户加入聊天室
        
        Args:
            user_id: 用户ID
            chatroom_id: 聊天室ID
            
        Returns:
            bool: 是否成功加入
        """
        try:
            # 如果用户已在其他聊天室，先离开
            current_chatroom = self.user_chatrooms.get(user_id)
            if current_chatroom and current_chatroom != chatroom_id:
                await self.leave_chatroom(user_id, current_chatroom)
            
            # 加入新聊天室
            if chatroom_id not in self.chatroom_users:
                self.chatroom_users[chatroom_id] = set()
            
            self.chatroom_users[chatroom_id].add(user_id)
            self.user_chatrooms[user_id] = chatroom_id
            
            # 获取用户信息
            session_info = self.user_sessions.get(user_id, {})
            user_name = session_info.get("user_name", "Unknown")
            
            logger.info(f"用户 {user_name}({user_id}) 加入聊天室 {chatroom_id}")
            
            # 通知其他用户
            await self.broadcast_to_chatroom(chatroom_id, {
                "type": "user_joined",
                "data": {
                    "chatroom_id": chatroom_id,
                    "user_id": user_id,
                    "user_name": user_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }, exclude_user=user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"用户加入聊天室失败: {e}")
            return False
    
    async def leave_chatroom(self, user_id: str, chatroom_id: str = None, notify_others: bool = True) -> bool:
        """
        用户离开聊天室
        
        Args:
            user_id: 用户ID
            chatroom_id: 聊天室ID(如果为None则使用用户当前聊天室)
            notify_others: 是否通知其他用户
            
        Returns:
            bool: 是否成功离开
        """
        try:
            # 确定要离开的聊天室
            if not chatroom_id:
                chatroom_id = self.user_chatrooms.get(user_id)
            
            if not chatroom_id:
                return True  # 用户不在任何聊天室中
            
            # 从聊天室移除用户
            if chatroom_id in self.chatroom_users:
                self.chatroom_users[chatroom_id].discard(user_id)
                
                # 如果聊天室没有用户了，清理聊天室
                if not self.chatroom_users[chatroom_id]:
                    del self.chatroom_users[chatroom_id]
            
            # 从用户聊天室映射移除
            if user_id in self.user_chatrooms:
                del self.user_chatrooms[user_id]
            
            # 获取用户信息
            session_info = self.user_sessions.get(user_id, {})
            user_name = session_info.get("user_name", "Unknown")
            
            logger.info(f"用户 {user_name}({user_id}) 离开聊天室 {chatroom_id}")
            
            # 通知其他用户
            if notify_others:
                await self.broadcast_to_chatroom(chatroom_id, {
                    "type": "user_left",
                    "data": {
                        "chatroom_id": chatroom_id,
                        "user_id": user_id,
                        "user_name": user_name,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }, exclude_user=user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"用户离开聊天室失败: {e}")
            return False
    
    def get_online_users(self, chatroom_id: str) -> List[Dict]:
        """
        获取聊天室在线用户列表
        
        Args:
            chatroom_id: 聊天室ID
            
        Returns:
            List[Dict]: 在线用户信息列表
        """
        try:
            if chatroom_id not in self.chatroom_users:
                return []
            
            online_users = []
            for user_id in self.chatroom_users[chatroom_id]:
                session_info = self.user_sessions.get(user_id, {})
                online_users.append({
                    "id": user_id,
                    "name": session_info.get("user_name", "Unknown"),
                    "joined_at": session_info.get("connected_at", datetime.utcnow()).isoformat(),
                    "last_activity": session_info.get("last_activity", datetime.utcnow()).isoformat()
                })
            
            return online_users
            
        except Exception as e:
            logger.error(f"获取在线用户列表失败: {e}")
            return []
    
    def get_chatroom_stats(self) -> Dict:
        """
        获取聊天室统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            return {
                "total_connections": len(self.active_connections),
                "total_chatrooms": len(self.chatroom_users),
                "chatroom_details": {
                    chatroom_id: len(users) 
                    for chatroom_id, users in self.chatroom_users.items()
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"获取聊天室统计失败: {e}")
            return {}
    
    async def cleanup_inactive_connections(self, timeout_minutes: int = 30):
        """
        清理不活跃的连接
        
        Args:
            timeout_minutes: 超时时间(分钟)
        """
        try:
            current_time = datetime.utcnow()
            inactive_users = []
            
            for user_id, session_info in self.user_sessions.items():
                last_activity = session_info.get("last_activity", current_time)
                if (current_time - last_activity).total_seconds() > timeout_minutes * 60:
                    inactive_users.append(user_id)
            
            for user_id in inactive_users:
                logger.info(f"清理不活跃连接: {user_id}")
                await self.disconnect(user_id)
                
        except Exception as e:
            logger.error(f"清理不活跃连接失败: {e}")

# 全局连接管理器实例
connection_manager = ConnectionManager()
