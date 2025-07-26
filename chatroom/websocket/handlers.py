"""
原生WebSocket处理器
处理聊天室的实时通信逻辑（移除Flask-SocketIO依赖）
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio
import websockets
import jwt
from config import Config

# 导入服务
from .connection_manager import connection_manager
from ..services.permissions import get_current_user, verify_chatroom_access
from ..services.message_crypto import MessageCrypto, message_security_manager
from ..services.online_user_manager import online_user_manager
from ..services.database_service import ChatroomDatabaseService

logger = logging.getLogger(__name__)

class NativeWebSocketHandler:
    """原生WebSocket处理器"""
    
    def __init__(self, db_service: ChatroomDatabaseService, 
                 online_manager=None, connection_manager_instance=None):
        """
        初始化原生WebSocket处理器
        
        Args:
            db_service: 数据库服务实例
            online_manager: 在线用户管理器（可选）
            connection_manager_instance: 连接管理器（可选）
        """
        self.db_service = db_service
        self.online_manager = online_manager or online_user_manager
        self.connection_manager = connection_manager_instance or connection_manager
        
        # 存储活动的WebSocket连接
        self.active_connections = {}
        self.user_sessions = {}  # user_id -> [websocket1, websocket2, ...]
        self.chatroom_members = {}  # chatroom_id -> [user_id1, user_id2, ...]
    
    async def handle_websocket_connection(self, websocket, path):
        """
        处理WebSocket连接的主要入口点
        
        Args:
            websocket: WebSocket连接对象
            path: 连接路径
        """
        try:
            # 从查询参数获取token
            query_params = {}
            if '?' in path:
                _, query_string = path.split('?', 1)
                for param in query_string.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        query_params[key] = value
            
            token = query_params.get('token')
            if not token:
                logger.warning("WebSocket连接缺少认证令牌")
                await websocket.close(code=4001, reason="Missing authentication token")
                return
            
            # 验证用户信息
            user_info = self.verify_websocket_token(token)
            if not user_info:
                logger.warning("WebSocket认证失败")
                await websocket.close(code=4002, reason="Authentication failed")
                return
            
            # 检查聊天室权限
            if not verify_chatroom_access(
                user_info['id'], 
                user_info.get('roles', []), 
                None  # 此时还没有指定聊天室
            ):
                logger.warning(f"用户 {user_info['id']} 没有聊天室访问权限")
                await websocket.close(code=4003, reason="Access denied")
                return
            
            # 建立连接
            user_id = user_info['id']
            user_name = user_info['username']
            session_id = f"ws_{id(websocket)}"
            
            # 存储连接信息
            self.active_connections[session_id] = {
                'websocket': websocket,
                'user_id': user_id,
                'user_name': user_name,
                'roles': user_info.get('roles', []),
                'connected_at': datetime.utcnow().isoformat(),
                'chatrooms': set()  # 用户加入的聊天室
            }
            
            # 维护用户会话列表
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = []
            self.user_sessions[user_id].append(session_id)
            
            logger.info(f"WebSocket连接成功: {user_name}({user_id}) - {session_id}")
            
            # 发送连接成功消息
            await self.send_to_websocket(websocket, {
                'type': 'connected',
                'success': True,
                'message': '连接成功',
                'data': {
                    'user_id': user_id,
                    'session_id': session_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
            })
            
            # 处理消息循环
            await self.handle_messages(websocket, session_id)
            
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket连接正常关闭: {session_id if 'session_id' in locals() else 'unknown'}")
        except Exception as e:
            logger.error(f"WebSocket连接处理失败: {e}")
        finally:
            # 清理连接
            if 'session_id' in locals():
                await self.cleanup_connection(session_id)
    
    async def handle_messages(self, websocket, session_id):
        """
        处理WebSocket消息循环
        
        Args:
            websocket: WebSocket连接对象
            session_id: 会话ID
        """
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')
                    
                    # 路由到相应的处理函数
                    if message_type == 'get_chatrooms':
                        await self.handle_get_chatrooms(websocket, session_id, data)
                    elif message_type == 'join_chatroom':
                        await self.handle_join_chatroom(websocket, session_id, data)
                    elif message_type == 'leave_chatroom':
                        await self.handle_leave_chatroom(websocket, session_id, data)
                    elif message_type == 'send_message':
                        await self.handle_send_message(websocket, session_id, data)
                    elif message_type == 'get_history':
                        await self.handle_get_history(websocket, session_id, data)
                    else:
                        await self.send_error(websocket, f"未知的消息类型: {message_type}", "UNKNOWN_MESSAGE_TYPE")
                        
                except json.JSONDecodeError:
                    await self.send_error(websocket, "无效的JSON格式", "INVALID_JSON")
                except Exception as e:
                    logger.error(f"处理WebSocket消息失败: {e}")
                    await self.send_error(websocket, "处理消息失败", "MESSAGE_PROCESSING_ERROR")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket连接关闭: {session_id}")
        except Exception as e:
            logger.error(f"WebSocket消息循环失败: {e}")
    
    async def handle_get_chatrooms(self, websocket, session_id, data):
        """获取聊天室列表"""
        try:
            connection_info = self.active_connections.get(session_id)
            if not connection_info:
                await self.send_error(websocket, "连接信息未找到", "CONNECTION_NOT_FOUND")
                return
                
            user_id = connection_info['user_id']
            
            # 获取用户可访问的聊天室
            chatrooms, total = self.db_service.get_user_chatrooms(user_id)
            
            await self.send_to_websocket(websocket, {
                'type': 'chatroom_list',
                'success': True,
                'data': {
                    'chatrooms': chatrooms,
                    'total': total,
                    'timestamp': datetime.utcnow().isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"获取聊天室列表失败: {e}")
            await self.send_error(websocket, "获取聊天室列表失败", "GET_CHATROOMS_ERROR")
    
    async def handle_join_chatroom(self, websocket, session_id, data):
        """加入聊天室"""
        try:
            connection_info = self.active_connections.get(session_id)
            if not connection_info:
                await self.send_error(websocket, "连接信息未找到", "CONNECTION_NOT_FOUND")
                return
                
            user_id = connection_info['user_id']
            user_name = connection_info['user_name']
            chatroom_id = data.get('chatroom_id')
            
            if not chatroom_id:
                await self.send_error(websocket, "缺少聊天室ID", "MISSING_CHATROOM_ID")
                return
            
            # 检查聊天室是否存在
            chatroom = self.db_service.get_chatroom_by_id(chatroom_id)
            if not chatroom:
                await self.send_error(websocket, "聊天室不存在", "CHATROOM_NOT_FOUND")
                return
            
            # 检查用户权限
            if not chatroom.is_public and not self.db_service.is_chatroom_member(chatroom_id, user_id):
                await self.send_error(websocket, "没有访问该聊天室的权限", "ACCESS_DENIED")
                return
            
            # 将用户加入聊天室
            connection_info['chatrooms'].add(chatroom_id)
            
            # 维护聊天室成员列表
            if chatroom_id not in self.chatroom_members:
                self.chatroom_members[chatroom_id] = set()
            self.chatroom_members[chatroom_id].add(user_id)
            
            # 更新在线状态
            self.online_manager.user_join_chatroom(
                chatroom_id, user_id, user_name, session_id
            )
            
            # 获取聊天室信息
            recent_messages = self.db_service.get_chatroom_messages(chatroom_id, limit=20)
            online_users = self.online_manager.get_online_users(chatroom_id)
            
            # 发送加入成功消息
            await self.send_to_websocket(websocket, {
                'type': 'chatroom_joined',
                'success': True,
                'data': {
                    'chatroom': {
                        'id': chatroom.id,
                        'name': chatroom.name,
                        'description': chatroom.description,
                        'is_public': chatroom.is_public
                    },
                    'messages': [
                        MessageCrypto.prepare_encrypted_message_for_client(msg)
                        for msg in recent_messages
                    ],
                    'online_users': online_users
                }
            })
            
            # 通知其他用户有新用户加入
            await self.broadcast_to_chatroom(chatroom_id, {
                'type': 'user_joined',
                'data': {
                    'chatroom_id': chatroom_id,
                    'user_id': user_id,
                    'user_name': user_name,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }, exclude_user=user_id)
            
            logger.info(f"用户 {user_name}({user_id}) 加入聊天室 {chatroom_id}")
            
        except Exception as e:
            logger.error(f"加入聊天室失败: {e}")
            await self.send_error(websocket, "加入聊天室失败", "JOIN_CHATROOM_ERROR")
    
    async def handle_leave_chatroom(self, websocket, session_id, data):
        """离开聊天室"""
        try:
            connection_info = self.active_connections.get(session_id)
            if not connection_info:
                return
                
            user_id = connection_info['user_id']
            user_name = connection_info['user_name']
            chatroom_id = data.get('chatroom_id')
            
            if chatroom_id and chatroom_id in connection_info['chatrooms']:
                # 从聊天室移除用户
                connection_info['chatrooms'].discard(chatroom_id)
                
                if chatroom_id in self.chatroom_members:
                    self.chatroom_members[chatroom_id].discard(user_id)
                
                # 更新在线状态
                self.online_manager.user_leave_chatroom(chatroom_id, user_id)
                
                # 通知其他用户
                await self.broadcast_to_chatroom(chatroom_id, {
                    'type': 'user_left',
                    'data': {
                        'chatroom_id': chatroom_id,
                        'user_id': user_id,
                        'user_name': user_name,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                }, exclude_user=user_id)
                
                logger.info(f"用户 {user_name}({user_id}) 离开聊天室 {chatroom_id}")
                
        except Exception as e:
            logger.error(f"离开聊天室失败: {e}")
    
    async def handle_send_message(self, websocket, session_id, data):
        """发送消息"""
        try:
            connection_info = self.active_connections.get(session_id)
            if not connection_info:
                await self.send_error(websocket, "连接信息未找到", "CONNECTION_NOT_FOUND")
                return
                
            user_id = connection_info['user_id']
            user_name = connection_info['user_name']
            
            # 验证必要字段
            chatroom_id = data.get('chatroom_id')
            message_content = data.get('message', '')
            message_type = data.get('message_type', 'text')
            timestamp = data.get('timestamp')
            
            if not chatroom_id or not timestamp:
                await self.send_error(websocket, "缺少必要字段", "MISSING_REQUIRED_FIELDS")
                return
            
            # 检查用户是否在聊天室中
            if chatroom_id not in connection_info['chatrooms']:
                await self.send_error(websocket, "用户未加入该聊天室", "NOT_IN_CHATROOM")
                return
            
            # 检查聊天室权限
            if not self.db_service.is_chatroom_member(chatroom_id, user_id):
                chatroom = self.db_service.get_chatroom_by_id(chatroom_id)
                if not chatroom or not chatroom.is_public:
                    await self.send_error(websocket, "没有发送消息的权限", "SEND_MESSAGE_DENIED")
                    return
            
            # 处理加密消息
            if data.get('encrypted') and data.get('encryption_data'):
                # 验证消息安全性
                message_hash = data.get('message_hash')
                encryption_data = data.get('encryption_data')
                
                is_valid, error_msg = message_security_manager.validate_message_security(
                    message_content, timestamp, user_id, message_hash, encryption_data
                )
                
                if not is_valid:
                    await self.send_error(websocket, f'消息安全验证失败: {error_msg}', "MESSAGE_SECURITY_ERROR")
                    return
                
                # 准备加密消息存储
                storage_data = MessageCrypto.prepare_encrypted_message_for_storage(
                    message_content, encryption_data, user_id, timestamp
                )
                
                # 保存消息到数据库
                saved_message = self.db_service.save_message(
                    chatroom_id=chatroom_id,
                    user_id=user_id,
                    user_name=user_name,
                    content=storage_data['content'],
                    message_type=message_type,
                    encrypted=storage_data['encrypted'],
                    encryption_iv=storage_data.get('encryption_iv'),
                    encryption_tag=storage_data.get('encryption_tag'),
                    message_hash=storage_data.get('message_hash')
                )
            else:
                # 处理未加密消息
                saved_message = self.db_service.save_message(
                    chatroom_id=chatroom_id,
                    user_id=user_id,
                    user_name=user_name,
                    content=message_content,
                    message_type=message_type
                )
            
            if not saved_message:
                await self.send_error(websocket, "消息保存失败", "MESSAGE_SAVE_ERROR")
                return
            
            # 准备广播消息
            broadcast_message = MessageCrypto.prepare_encrypted_message_for_client(saved_message)
            
            # 广播消息给聊天室所有用户
            await self.broadcast_to_chatroom(chatroom_id, {
                'type': 'message',
                'success': True,
                'data': broadcast_message
            })
            
            # 更新用户活动时间
            self.online_manager.update_user_activity(chatroom_id, user_id)
            
            logger.info(f"消息发送成功: {user_name} -> {chatroom_id}")
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            await self.send_error(websocket, "发送消息失败", "SEND_MESSAGE_ERROR")
    
    async def handle_get_history(self, websocket, session_id, data):
        """获取历史消息"""
        try:
            connection_info = self.active_connections.get(session_id)
            if not connection_info:
                await self.send_error(websocket, "连接信息未找到", "CONNECTION_NOT_FOUND")
                return
                
            user_id = connection_info['user_id']
            chatroom_id = data.get('chatroom_id')
            limit = min(data.get('limit', 50), 100)  # 限制最大50条
            before_message_id = data.get('before')
            
            if not chatroom_id:
                await self.send_error(websocket, "缺少聊天室ID", "MISSING_CHATROOM_ID")
                return
            
            # 检查权限
            if not self.db_service.is_chatroom_member(chatroom_id, user_id):
                chatroom = self.db_service.get_chatroom_by_id(chatroom_id)
                if not chatroom or not chatroom.is_public:
                    await self.send_error(websocket, "没有访问权限", "ACCESS_DENIED")
                    return
            
            # 获取历史消息
            messages = self.db_service.get_chatroom_messages(
                chatroom_id, limit, before_message_id
            )
            
            # 转换消息格式
            formatted_messages = [
                MessageCrypto.prepare_encrypted_message_for_client(msg)
                for msg in messages
            ]
            
            await self.send_to_websocket(websocket, {
                'type': 'history',
                'success': True,
                'data': {
                    'chatroom_id': chatroom_id,
                    'messages': formatted_messages,
                    'has_more': len(messages) == limit
                }
            })
            
        except Exception as e:
            logger.error(f"获取历史消息失败: {e}")
            await self.send_error(websocket, "获取历史消息失败", "GET_HISTORY_ERROR")
    
    async def cleanup_connection(self, session_id):
        """清理WebSocket连接"""
        try:
            connection_info = self.active_connections.get(session_id)
            if not connection_info:
                return
            
            user_id = connection_info['user_id']
            user_name = connection_info['user_name']
            
            # 从所有聊天室中移除用户
            for chatroom_id in list(connection_info['chatrooms']):
                if chatroom_id in self.chatroom_members:
                    self.chatroom_members[chatroom_id].discard(user_id)
                
                # 更新在线状态
                self.online_manager.user_leave_chatroom(chatroom_id, user_id)
                
                # 通知其他用户
                await self.broadcast_to_chatroom(chatroom_id, {
                    'type': 'user_left',
                    'data': {
                        'chatroom_id': chatroom_id,
                        'user_id': user_id,
                        'user_name': user_name,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                }, exclude_user=user_id)
            
            # 清理连接记录
            del self.active_connections[session_id]
            
            # 清理用户会话记录
            if user_id in self.user_sessions:
                if session_id in self.user_sessions[user_id]:
                    self.user_sessions[user_id].remove(session_id)
                if not self.user_sessions[user_id]:
                    del self.user_sessions[user_id]
            
            # 清理在线状态
            self.online_manager.remove_user_session(session_id)
            
            logger.info(f"WebSocket连接清理完成: {user_name}({user_id}) - {session_id}")
            
        except Exception as e:
            logger.error(f"清理WebSocket连接失败: {e}")
    
    async def send_to_websocket(self, websocket, message):
        """发送消息到WebSocket"""
        try:
            message_json = json.dumps(message, ensure_ascii=False)
            await websocket.send(message_json)
        except Exception as e:
            logger.error(f"发送WebSocket消息失败: {e}")
    
    async def send_error(self, websocket, message, code):
        """发送错误消息"""
        await self.send_to_websocket(websocket, {
            'type': 'error',
            'message': message,
            'code': code,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def broadcast_to_chatroom(self, chatroom_id, message, exclude_user=None):
        """向聊天室广播消息"""
        try:
            sent_count = 0
            for session_id, connection_info in list(self.active_connections.items()):
                if (chatroom_id in connection_info['chatrooms'] and 
                    (exclude_user is None or connection_info['user_id'] != exclude_user)):
                    try:
                        websocket = connection_info['websocket']
                        await self.send_to_websocket(websocket, message)
                        sent_count += 1
                    except Exception as e:
                        logger.warning(f"向会话 {session_id} 发送广播消息失败: {e}")
                        # 可能需要清理断开的连接
            
            logger.debug(f"向聊天室 {chatroom_id} 广播消息，发送到 {sent_count} 个连接")
            
        except Exception as e:
            logger.error(f"广播消息到聊天室失败: {e}")
    
    def verify_websocket_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证WebSocket连接的JWT令牌
        
        Args:
            token: JWT令牌
            
        Returns:
            Dict: 用户信息
        """
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
            
            return {
                'id': payload.get('user_id'),
                'username': payload.get('username'),
                'roles': payload.get('roles', [])
            }
            
        except Exception as e:
            logger.error(f"WebSocket令牌验证失败: {e}")
            return None


# 创建全局处理器实例（保持兼容性）
websocket_handler = None

def get_websocket_handler(db_service=None, online_manager=None, connection_manager_instance=None):
    """获取WebSocket处理器实例"""
    global websocket_handler
    if websocket_handler is None and db_service:
        websocket_handler = NativeWebSocketHandler(
            db_service=db_service,
            online_manager=online_manager,
            connection_manager_instance=connection_manager_instance
        )
    return websocket_handler
