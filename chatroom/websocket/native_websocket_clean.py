"""
原生WebSocket实现，匹配前端需求文档规范
支持 ws://127.0.0.1:6000/ws/chatroom?token={jwt_token} 端点
完全兼容前端WebSocket客户端需求
"""
import json
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Set, Optional
from urllib.parse import parse_qs

try:
    import websockets
    from websockets.exceptions import ConnectionClosed, WebSocketException
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logging.warning("websockets库不可用，原生WebSocket功能将被禁用")

# JWT验证
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logging.warning("JWT库不可用，WebSocket认证将被禁用")

logger = logging.getLogger(__name__)

class NativeWebSocketHandler:
    """原生WebSocket处理器，匹配前端需求文档"""
    
    def __init__(self, app, db_service=None, online_manager=None):
        self.app = app
        self.db_service = db_service
        self.online_manager = online_manager
        
        # 连接管理
        self.active_connections: Dict[str, 'websockets.WebSocketServerProtocol'] = {}
        self.user_connections: Dict[str, str] = {}  # user_id -> connection_id
        self.chatroom_users: Dict[str, Set[str]] = {}  # chatroom_id -> user_ids
        self.user_chatrooms: Dict[str, str] = {}  # user_id -> chatroom_id
        self.connection_info: Dict[str, Dict] = {}  # connection_id -> user_info
        
        logger.info("原生WebSocket处理器初始化完成")
    
    async def handle_connection(self, websocket, path):
        """处理WebSocket连接"""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets库不可用，无法处理连接")
            return
            
        connection_id = str(uuid.uuid4())
        remote_addr = websocket.remote_address
        
        logger.info(f"新的WebSocket连接: {connection_id} from {remote_addr}")
        
        try:
            # 解析路径
            if path != "/ws/chatroom":
                await websocket.close(code=1008, reason="Invalid endpoint")
                return
                
            # 从查询字符串获取token (如果有的话)
            token = None
            if hasattr(websocket, 'query_string') and websocket.query_string:
                query_params = parse_qs(websocket.query_string)
                token = query_params.get('token', [None])[0]
            
            # 如果URL中没有token，等待认证消息
            if not token:
                # 等待认证消息
                auth_message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                user_info = await self.authenticate_message(auth_message)
            else:
                # 直接验证URL中的token
                user_info = await self.verify_jwt_token(token)
            
            if not user_info:
                await websocket.close(code=1008, reason="Authentication failed")
                return
            
            # 存储连接信息
            self.active_connections[connection_id] = websocket
            self.user_connections[user_info['user_id']] = connection_id
            self.connection_info[connection_id] = user_info
            
            # 发送连接成功消息
            await self.send_message(connection_id, {
                'type': 'connected',
                'data': {
                    'connection_id': connection_id,
                    'user_id': user_info['user_id'],
                    'username': user_info.get('username', 'Unknown'),
                    'server_time': datetime.utcnow().isoformat() + 'Z'
                },
                'status': 'success',
                'message': '连接成功'
            })
            
            logger.info(f"用户 {user_info['user_id']} 通过WebSocket连接成功")
            
            # 处理消息循环
            async for message in websocket:
                try:
                    await self.handle_message(connection_id, message)
                except Exception as e:
                    logger.error(f"处理消息时出错: {e}")
                    await self.send_error(connection_id, "消息处理失败", str(e))
        
        except asyncio.TimeoutError:
            await websocket.close(code=1008, reason="Authentication timeout")
            logger.warning(f"连接 {connection_id} 认证超时")
        
        except Exception as e:
            if "ConnectionClosed" in str(type(e)):
                logger.info(f"WebSocket连接 {connection_id} 已关闭")
            else:
                logger.error(f"WebSocket连接处理出错: {e}")
                try:
                    await websocket.close(code=1011, reason="Server error")
                except:
                    pass
        
        finally:
            # 清理连接
            await self.cleanup_connection(connection_id)
    
    async def authenticate_message(self, message: str) -> Optional[Dict]:
        """验证认证消息"""
        try:
            auth_data = json.loads(message)
            if auth_data.get('type') != 'auth':
                return None
            
            token = auth_data.get('token')
            if not token:
                return None
            
            return await self.verify_jwt_token(token)
        except Exception as e:
            logger.error(f"认证消息解析失败: {e}")
            return None
    
    async def verify_jwt_token(self, token: str) -> Optional[Dict]:
        """验证JWT token"""
        if not JWT_AVAILABLE:
            # 简化认证用于测试
            logger.warning("JWT不可用，使用简化认证")
            return {
                'user_id': 'demo_user',
                'username': 'Demo User',
                'is_admin': False
            }
        
        try:
            jwt_secret = getattr(self.app.config, 'JWT_SECRET_KEY', 'your-secret-key')
            payload = jwt.decode(token, jwt_secret, algorithms=['HS256'])
            
            return {
                'user_id': payload.get('user_id'),
                'username': payload.get('username'),
                'is_admin': payload.get('is_admin', False),
                'exp': payload.get('exp')
            }
        
        except Exception as e:
            logger.warning(f"JWT token验证失败: {e}")
            return None
    
    async def handle_message(self, connection_id: str, message: str):
        """处理WebSocket消息"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            logger.debug(f"收到消息类型: {message_type} from {connection_id}")
            
            # 根据消息类型分发处理
            handlers = {
                'get_chatrooms': self.handle_get_chatrooms,
                'join_chatroom': self.handle_join_chatroom,
                'leave_chatroom': self.handle_leave_chatroom,
                'send_message': self.handle_send_message_ws,
                'get_messages': self.handle_get_messages,
                'heartbeat': self.handle_heartbeat
            }
            
            handler = handlers.get(message_type)
            if handler:
                await handler(connection_id, data)
            else:
                await self.send_error(connection_id, "未知消息类型", f"不支持的消息类型: {message_type}")
        
        except json.JSONDecodeError:
            await self.send_error(connection_id, "消息格式错误", "消息必须是有效的JSON格式")
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            await self.send_error(connection_id, "消息处理失败", str(e))
    
    async def handle_get_chatrooms(self, connection_id: str, data: Dict):
        """获取聊天室列表"""
        try:
            # 模拟聊天室数据
            chatrooms = [
                {
                    'id': 'general',
                    'name': '综合讨论',
                    'description': '全员可见的综合讨论区',
                    'member_count': len(self.chatroom_users.get('general', set())),
                    'is_public': True
                },
                {
                    'id': 'tech',
                    'name': '技术交流',
                    'description': '技术相关话题讨论',
                    'member_count': len(self.chatroom_users.get('tech', set())),
                    'is_public': True
                }
            ]
            
            await self.send_message(connection_id, {
                'type': 'chatrooms_list',
                'data': chatrooms,
                'status': 'success',
                'message': '聊天室列表获取成功'
            })
        
        except Exception as e:
            await self.send_error(connection_id, "获取聊天室列表失败", str(e))
    
    async def handle_join_chatroom(self, connection_id: str, data: Dict):
        """加入聊天室"""
        try:
            chatroom_id = data.get('chatroom_id')
            if not chatroom_id:
                await self.send_error(connection_id, "参数错误", "缺少chatroom_id参数")
                return
            
            user_info = self.connection_info.get(connection_id)
            if not user_info:
                await self.send_error(connection_id, "认证错误", "用户信息不存在")
                return
            
            user_id = user_info['user_id']
            
            # 添加用户到聊天室
            if chatroom_id not in self.chatroom_users:
                self.chatroom_users[chatroom_id] = set()
            
            self.chatroom_users[chatroom_id].add(user_id)
            self.user_chatrooms[user_id] = chatroom_id
            
            # 通知用户加入成功
            await self.send_message(connection_id, {
                'type': 'chatroom_joined',
                'data': {
                    'chatroom_id': chatroom_id,
                    'user_id': user_id,
                    'username': user_info.get('username'),
                    'join_time': datetime.utcnow().isoformat() + 'Z'
                },
                'status': 'success',
                'message': f'成功加入聊天室 {chatroom_id}'
            })
            
            # 通知聊天室其他成员
            await self.broadcast_to_chatroom(chatroom_id, {
                'type': 'user_joined',
                'data': {
                    'chatroom_id': chatroom_id,
                    'user_id': user_id,
                    'username': user_info.get('username'),
                    'join_time': datetime.utcnow().isoformat() + 'Z'
                }
            }, exclude_user=user_id)
            
            logger.info(f"用户 {user_id} 加入聊天室 {chatroom_id}")
        
        except Exception as e:
            await self.send_error(connection_id, "加入聊天室失败", str(e))
    
    async def handle_leave_chatroom(self, connection_id: str, data: Dict):
        """离开聊天室"""
        try:
            chatroom_id = data.get('chatroom_id')
            if not chatroom_id:
                await self.send_error(connection_id, "参数错误", "缺少chatroom_id参数")
                return
            
            user_info = self.connection_info.get(connection_id)
            if not user_info:
                return
            
            user_id = user_info['user_id']
            
            # 从聊天室移除用户
            if chatroom_id in self.chatroom_users:
                self.chatroom_users[chatroom_id].discard(user_id)
            
            if user_id in self.user_chatrooms:
                del self.user_chatrooms[user_id]
            
            # 通知用户离开成功
            await self.send_message(connection_id, {
                'type': 'chatroom_left',
                'data': {
                    'chatroom_id': chatroom_id,
                    'user_id': user_id,
                    'leave_time': datetime.utcnow().isoformat() + 'Z'
                },
                'status': 'success',
                'message': f'已离开聊天室 {chatroom_id}'
            })
            
            # 通知聊天室其他成员
            await self.broadcast_to_chatroom(chatroom_id, {
                'type': 'user_left',
                'data': {
                    'chatroom_id': chatroom_id,
                    'user_id': user_id,
                    'username': user_info.get('username'),
                    'leave_time': datetime.utcnow().isoformat() + 'Z'
                }
            }, exclude_user=user_id)
            
            logger.info(f"用户 {user_id} 离开聊天室 {chatroom_id}")
        
        except Exception as e:
            await self.send_error(connection_id, "离开聊天室失败", str(e))
    
    async def handle_send_message_ws(self, connection_id: str, data: Dict):
        """发送消息"""
        try:
            chatroom_id = data.get('chatroom_id')
            message = data.get('message')
            
            if not chatroom_id or not message:
                await self.send_error(connection_id, "参数错误", "缺少必要参数")
                return
            
            user_info = self.connection_info.get(connection_id)
            if not user_info:
                await self.send_error(connection_id, "认证错误", "用户信息不存在")
                return
            
            user_id = user_info['user_id']
            
            # 构建消息对象
            message_obj = {
                'id': str(uuid.uuid4()),
                'chatroom_id': chatroom_id,
                'user_id': user_id,
                'username': user_info.get('username'),
                'message': message,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'message_type': 'text'
            }
            
            # 广播消息到聊天室
            await self.broadcast_to_chatroom(chatroom_id, {
                'type': 'new_message',
                'data': message_obj
            })
            
            # 确认消息发送成功
            await self.send_message(connection_id, {
                'type': 'message_sent',
                'data': {
                    'message_id': message_obj['id'],
                    'chatroom_id': chatroom_id,
                    'timestamp': message_obj['timestamp']
                },
                'status': 'success',
                'message': '消息发送成功'
            })
            
            logger.info(f"用户 {user_id} 在聊天室 {chatroom_id} 发送了消息")
        
        except Exception as e:
            await self.send_error(connection_id, "发送消息失败", str(e))
    
    async def handle_get_messages(self, connection_id: str, data: Dict):
        """获取历史消息"""
        try:
            chatroom_id = data.get('chatroom_id')
            limit = data.get('limit', 50)
            offset = data.get('offset', 0)
            
            if not chatroom_id:
                await self.send_error(connection_id, "参数错误", "缺少chatroom_id参数")
                return
            
            # 模拟历史消息
            messages = [
                {
                    'id': f'msg_{i}',
                    'chatroom_id': chatroom_id, 
                    'user_id': f'user_{i % 3}',
                    'username': f'User{i % 3}',
                    'message': f'这是测试消息 {i}',
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'message_type': 'text'
                }
                for i in range(offset, min(offset + limit, offset + 10))
            ]
            
            await self.send_message(connection_id, {
                'type': 'messages_history',
                'data': {
                    'chatroom_id': chatroom_id,
                    'messages': messages,
                    'total': len(messages),
                    'offset': offset,
                    'limit': limit
                },
                'status': 'success',
                'message': '历史消息获取成功'
            })
        
        except Exception as e:
            await self.send_error(connection_id, "获取历史消息失败", str(e))
    
    async def handle_heartbeat(self, connection_id: str, data: Dict):
        """处理心跳消息"""
        await self.send_message(connection_id, {
            'type': 'heartbeat_response',
            'data': {
                'server_time': datetime.utcnow().isoformat() + 'Z'
            },
            'status': 'success'
        })
    
    async def broadcast_to_chatroom(self, chatroom_id: str, message: Dict, exclude_user: str = None):
        """向聊天室所有成员广播消息"""
        if chatroom_id not in self.chatroom_users:
            return
        
        for user_id in self.chatroom_users[chatroom_id]:
            if exclude_user and user_id == exclude_user:
                continue
            
            connection_id = self.user_connections.get(user_id)
            if connection_id and connection_id in self.active_connections:
                try:
                    await self.send_message(connection_id, message)
                except Exception as e:
                    logger.error(f"广播消息到用户 {user_id} 失败: {e}")
    
    async def send_message(self, connection_id: str, message: Dict):
        """发送消息到指定连接"""
        if connection_id not in self.active_connections:
            return
        
        try:
            websocket = self.active_connections[connection_id]
            await websocket.send(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            if "ConnectionClosed" in str(type(e)):
                logger.info(f"连接 {connection_id} 已关闭，移除连接")
                await self.cleanup_connection(connection_id)
            else:
                logger.error(f"发送消息到连接 {connection_id} 失败: {e}")
    
    async def send_error(self, connection_id: str, error_message: str, details: str = None):
        """发送错误消息"""
        error_data = {
            'type': 'error',
            'data': {
                'error': error_message,
                'details': details,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            },
            'status': 'error',
            'message': error_message
        }
        
        await self.send_message(connection_id, error_data)
    
    async def cleanup_connection(self, connection_id: str):
        """清理连接相关数据"""
        try:
            # 获取用户信息
            user_info = self.connection_info.get(connection_id)
            if user_info:
                user_id = user_info['user_id']
                
                # 从所有聊天室移除用户
                for chatroom_id, members in self.chatroom_users.items():
                    if user_id in members:
                        members.discard(user_id)
                        
                        # 通知聊天室其他成员用户离线
                        await self.broadcast_to_chatroom(chatroom_id, {
                            'type': 'user_offline',
                            'data': {
                                'chatroom_id': chatroom_id,
                                'user_id': user_id,
                                'username': user_info.get('username'),
                                'offline_time': datetime.utcnow().isoformat() + 'Z'
                            }
                        })
                
                # 清理用户连接映射
                if user_id in self.user_connections:
                    del self.user_connections[user_id]
                
                if user_id in self.user_chatrooms:
                    del self.user_chatrooms[user_id]
            
            # 清理连接数据
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
            
            if connection_id in self.connection_info:
                del self.connection_info[connection_id]
            
            logger.info(f"连接 {connection_id} 清理完成")
        
        except Exception as e:
            logger.error(f"清理连接 {connection_id} 时出错: {e}")


class NativeWebSocketServer:
    """原生WebSocket服务器包装类"""
    
    def __init__(self, app, db_session=None):
        self.app = app
        self.db_session = db_session
        self.handler = None
        self.server = None
        
    def start(self, host='127.0.0.1', port=5000):
        """启动WebSocket服务器"""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets库不可用，无法启动WebSocket服务器")
            return
            
        # 创建处理器实例
        self.handler = NativeWebSocketHandler(self.app, self.db_session)
        
        # 计算WebSocket服务端口（避免与Flask冲突）
        ws_port = port + 1000  # 使用6000端口
        
        # 启动WebSocket服务器
        async def run_server():
            logger.info(f"原生WebSocket服务器启动: ws://{host}:{ws_port}/ws/chatroom")
            
            async def websocket_handler(websocket, path):
                if path == '/ws/chatroom':
                    await self.handler.handle_connection(websocket, path)
                else:
                    await websocket.close(code=1000, reason="Invalid path")
            
            import websockets
            self.server = await websockets.serve(
                websocket_handler,
                host,
                ws_port,
                ping_interval=30,
                ping_timeout=10
            )
            
            logger.info(f"✅ 原生WebSocket服务器已启动在端口 {ws_port}")
            logger.info(f"💡 前端请连接: ws://{host}:{ws_port}/ws/chatroom?token=YOUR_JWT_TOKEN")
            
            await self.server.wait_closed()
        
        # 运行异步服务器
        try:
            asyncio.run(run_server())
        except Exception as e:
            logger.error(f"WebSocket服务器启动失败: {e}")
    
    async def stop(self):
        """停止WebSocket服务器"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("原生WebSocket服务器已停止")


def setup_native_websocket(app, db_session=None):
    """
    设置原生WebSocket服务器以匹配前端需求
    
    Args:
        app: Flask应用实例
        db_session: 数据库会话
        
    Returns:
        NativeWebSocketServer: WebSocket服务器实例，如果库不可用则返回None
    """
    if not WEBSOCKETS_AVAILABLE:
        logger.warning("websockets库不可用，跳过原生WebSocket服务器初始化")
        return None
        
    try:
        server = NativeWebSocketServer(app, db_session)
        logger.info("原生WebSocket服务器初始化完成")
        return server
    except Exception as e:
        logger.error(f"原生WebSocket服务器初始化失败: {e}")
        return None


if __name__ == "__main__":
    # 测试启动
    import os
    import sys
    
    # 添加项目根目录到Python路径
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    from flask import Flask
    
    # 创建测试应用
    app = Flask(__name__)
    app.config['JWT_SECRET_KEY'] = 'test-secret-key'
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 启动WebSocket服务器
    server = setup_native_websocket(app)
    if server:
        server.start(host='127.0.0.1', port=5000)
