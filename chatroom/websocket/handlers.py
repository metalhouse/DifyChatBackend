"""
WebSocket处理器
处理聊天室的实时通信逻辑
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any
from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect

# 导入服务
from .connection_manager import connection_manager
from ..services.permissions import get_current_user, verify_chatroom_access
from ..services.message_crypto import MessageCrypto, message_security_manager
from ..services.online_user_manager import online_user_manager
from ..services.database_service import ChatroomDatabaseService

logger = logging.getLogger(__name__)

class ChatroomWebSocketHandler:
    """聊天室WebSocket处理器"""
    
    def __init__(self, socketio: SocketIO, db_service: ChatroomDatabaseService, 
                 online_manager=None, connection_manager=None):
        """
        初始化WebSocket处理器
        
        Args:
            socketio: SocketIO实例
            db_service: 数据库服务实例
            online_manager: 在线用户管理器（可选）
            connection_manager: 连接管理器（可选）
        """
        self.socketio = socketio
        self.db_service = db_service
        self.online_manager = online_manager
        self.connection_manager = connection_manager
        
        # 注册WebSocket事件处理器
        self.register_handlers()
    
    def register_handlers(self):
        """注册WebSocket事件处理器"""
        
        @self.socketio.on('connect', namespace='/chatroom')
        def handle_connect(auth=None):
            """处理WebSocket连接"""
            try:
                # 验证JWT token
                token = request.args.get('token')
                if not token:
                    logger.warning("WebSocket连接缺少认证令牌")
                    disconnect()
                    return False
                
                # 验证用户信息 (这里需要实现JWT验证)
                try:
                    # 简化处理，实际应该验证JWT
                    user_info = self.verify_websocket_token(token)
                    if not user_info:
                        disconnect()
                        return False
                except Exception as e:
                    logger.error(f"WebSocket认证失败: {e}")
                    disconnect()
                    return False
                
                # 检查聊天室权限
                if not verify_chatroom_access(
                    user_info['id'], 
                    user_info.get('roles', []), 
                    None  # 此时还没有指定聊天室
                ):
                    logger.warning(f"用户 {user_info['id']} 没有聊天室访问权限")
                    disconnect()
                    return False
                
                # 建立连接
                session_id = request.sid
                user_id = user_info['id']
                user_name = user_info['username']
                
                # 存储用户信息到session
                self.socketio.session[session_id] = {
                    'user_id': user_id,
                    'user_name': user_name,
                    'roles': user_info.get('roles', []),
                    'connected_at': datetime.utcnow().isoformat()
                }
                
                logger.info(f"WebSocket连接成功: {user_name}({user_id})")
                
                # 发送连接成功消息
                emit('connected', {
                    'success': True,
                    'message': '连接成功',
                    'user_id': user_id,
                    'session_id': session_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                return True
                
            except Exception as e:
                logger.error(f"WebSocket连接处理失败: {e}")
                disconnect()
                return False
        
        @self.socketio.on('disconnect', namespace='/chatroom')
        def handle_disconnect():
            """处理WebSocket断开连接"""
            try:
                session_id = request.sid
                session_data = self.socketio.session.get(session_id, {})
                user_id = session_data.get('user_id')
                user_name = session_data.get('user_name', 'Unknown')
                
                if user_id:
                    # 清理在线状态
                    online_user_manager.remove_user_session(session_id)
                    logger.info(f"WebSocket断开连接: {user_name}({user_id})")
                
            except Exception as e:
                logger.error(f"WebSocket断开连接处理失败: {e}")
        
        @self.socketio.on('get_chatrooms', namespace='/chatroom')
        def handle_get_chatrooms():
            """获取聊天室列表"""
            try:
                session_data = self.socketio.session.get(request.sid, {})
                user_id = session_data.get('user_id')
                
                if not user_id:
                    emit('error', {
                        'message': '用户未认证',
                        'code': 'USER_NOT_AUTHENTICATED'
                    })
                    return
                
                # 获取用户可访问的聊天室
                chatrooms, total = self.db_service.get_user_chatrooms(user_id)
                
                emit('chatroom_list', {
                    'success': True,
                    'data': chatrooms,
                    'total': total,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                logger.error(f"获取聊天室列表失败: {e}")
                emit('error', {
                    'message': '获取聊天室列表失败',
                    'code': 'GET_CHATROOMS_ERROR'
                })
        
        @self.socketio.on('join_chatroom', namespace='/chatroom')
        def handle_join_chatroom(data):
            """加入聊天室"""
            try:
                session_data = self.socketio.session.get(request.sid, {})
                user_id = session_data.get('user_id')
                user_name = session_data.get('user_name')
                
                if not user_id:
                    emit('error', {
                        'message': '用户未认证',
                        'code': 'USER_NOT_AUTHENTICATED'
                    })
                    return
                
                chatroom_id = data.get('chatroom_id')
                if not chatroom_id:
                    emit('error', {
                        'message': '缺少聊天室ID',
                        'code': 'MISSING_CHATROOM_ID'
                    })
                    return
                
                # 检查聊天室是否存在
                chatroom = self.db_service.get_chatroom_by_id(chatroom_id)
                if not chatroom:
                    emit('error', {
                        'message': '聊天室不存在',
                        'code': 'CHATROOM_NOT_FOUND'
                    })
                    return
                
                # 检查用户权限
                if not chatroom.is_public and not self.db_service.is_chatroom_member(chatroom_id, user_id):
                    emit('error', {
                        'message': '没有访问该聊天室的权限',
                        'code': 'ACCESS_DENIED'
                    })
                    return
                
                # 加入Socket.IO房间
                join_room(chatroom_id)
                
                # 更新在线状态
                online_user_manager.user_join_chatroom(
                    chatroom_id, user_id, user_name, request.sid
                )
                
                # 获取聊天室信息
                recent_messages = self.db_service.get_chatroom_messages(chatroom_id, limit=20)
                online_users = online_user_manager.get_online_users(chatroom_id)
                
                # 发送加入成功消息
                emit('chatroom_joined', {
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
                self.socketio.emit('user_joined', {
                    'chatroom_id': chatroom_id,
                    'user_id': user_id,
                    'user_name': user_name,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=chatroom_id, namespace='/chatroom', include_self=False)
                
                logger.info(f"用户 {user_name}({user_id}) 加入聊天室 {chatroom_id}")
                
            except Exception as e:
                logger.error(f"加入聊天室失败: {e}")
                emit('error', {
                    'message': '加入聊天室失败',
                    'code': 'JOIN_CHATROOM_ERROR'
                })
        
        @self.socketio.on('leave_chatroom', namespace='/chatroom')
        def handle_leave_chatroom(data):
            """离开聊天室"""
            try:
                session_data = self.socketio.session.get(request.sid, {})
                user_id = session_data.get('user_id')
                user_name = session_data.get('user_name')
                
                chatroom_id = data.get('chatroom_id')
                if chatroom_id:
                    # 离开Socket.IO房间
                    leave_room(chatroom_id)
                    
                    # 更新在线状态
                    online_user_manager.user_leave_chatroom(chatroom_id, user_id)
                    
                    # 通知其他用户
                    self.socketio.emit('user_left', {
                        'chatroom_id': chatroom_id,
                        'user_id': user_id,
                        'user_name': user_name,
                        'timestamp': datetime.utcnow().isoformat()
                    }, room=chatroom_id, namespace='/chatroom', include_self=False)
                    
                    logger.info(f"用户 {user_name}({user_id}) 离开聊天室 {chatroom_id}")
                
            except Exception as e:
                logger.error(f"离开聊天室失败: {e}")
        
        @self.socketio.on('send_message', namespace='/chatroom')
        def handle_send_message(data):
            """发送消息"""
            try:
                session_data = self.socketio.session.get(request.sid, {})
                user_id = session_data.get('user_id')
                user_name = session_data.get('user_name')
                
                if not user_id:
                    emit('error', {
                        'message': '用户未认证',
                        'code': 'USER_NOT_AUTHENTICATED'
                    })
                    return
                
                # 验证必要字段
                chatroom_id = data.get('chatroom_id')
                message_content = data.get('message', '')
                message_type = data.get('message_type', 'text')
                timestamp = data.get('timestamp')
                
                if not chatroom_id or not timestamp:
                    emit('error', {
                        'message': '缺少必要字段',
                        'code': 'MISSING_REQUIRED_FIELDS'
                    })
                    return
                
                # 检查聊天室权限
                if not self.db_service.is_chatroom_member(chatroom_id, user_id):
                    chatroom = self.db_service.get_chatroom_by_id(chatroom_id)
                    if not chatroom or not chatroom.is_public:
                        emit('error', {
                            'message': '没有发送消息的权限',
                            'code': 'SEND_MESSAGE_DENIED'
                        })
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
                        emit('error', {
                            'message': f'消息安全验证失败: {error_msg}',
                            'code': 'MESSAGE_SECURITY_ERROR'
                        })
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
                    emit('error', {
                        'message': '消息保存失败',
                        'code': 'MESSAGE_SAVE_ERROR'
                    })
                    return
                
                # 准备广播消息
                broadcast_message = MessageCrypto.prepare_encrypted_message_for_client(saved_message)
                
                # 广播消息给聊天室所有用户
                self.socketio.emit('message', {
                    'success': True,
                    'data': broadcast_message
                }, room=chatroom_id, namespace='/chatroom')
                
                # 更新用户活动时间
                online_user_manager.update_user_activity(chatroom_id, user_id)
                
                logger.info(f"消息发送成功: {user_name} -> {chatroom_id}")
                
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                emit('error', {
                    'message': '发送消息失败',
                    'code': 'SEND_MESSAGE_ERROR'
                })
        
        @self.socketio.on('get_history', namespace='/chatroom')
        def handle_get_history(data):
            """获取历史消息"""
            try:
                session_data = self.socketio.session.get(request.sid, {})
                user_id = session_data.get('user_id')
                
                if not user_id:
                    emit('error', {
                        'message': '用户未认证',
                        'code': 'USER_NOT_AUTHENTICATED'
                    })
                    return
                
                chatroom_id = data.get('chatroom_id')
                limit = min(data.get('limit', 50), 100)  # 限制最大50条
                before_message_id = data.get('before')
                
                if not chatroom_id:
                    emit('error', {
                        'message': '缺少聊天室ID',
                        'code': 'MISSING_CHATROOM_ID'
                    })
                    return
                
                # 检查权限
                if not self.db_service.is_chatroom_member(chatroom_id, user_id):
                    chatroom = self.db_service.get_chatroom_by_id(chatroom_id)
                    if not chatroom or not chatroom.is_public:
                        emit('error', {
                            'message': '没有访问权限',
                            'code': 'ACCESS_DENIED'
                        })
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
                
                emit('history', {
                    'success': True,
                    'data': {
                        'chatroom_id': chatroom_id,
                        'messages': formatted_messages,
                        'has_more': len(messages) == limit
                    }
                })
                
            except Exception as e:
                logger.error(f"获取历史消息失败: {e}")
                emit('error', {
                    'message': '获取历史消息失败',
                    'code': 'GET_HISTORY_ERROR'
                })
    
    def verify_websocket_token(self, token: str) -> Dict[str, Any]:
        """
        验证WebSocket连接的JWT令牌
        
        Args:
            token: JWT令牌
            
        Returns:
            Dict: 用户信息
        """
        try:
            # 这里应该实现JWT验证逻辑
            # 简化处理，实际应该导入系统的JWT验证
            import jwt
            from config import Config
            
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
            
            return {
                'id': payload.get('user_id'),
                'username': payload.get('username'),
                'roles': payload.get('roles', [])
            }
            
        except Exception as e:
            logger.error(f"WebSocket令牌验证失败: {e}")
            return None
