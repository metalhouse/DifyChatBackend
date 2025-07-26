"""
聊天室系统主模块
提供完整的实时聊天功能，包括WebSocket通信、消息加密、权限管理等
"""

import logging
import os
from typing import Optional, Any

# 设置模块日志
logger = logging.getLogger(__name__)

def init_chatroom_system(app, socketio, db_session=None):
    """
    初始化聊天室系统
    
    Args:
        app: Flask应用实例
        socketio: SocketIO实例
        db_session: 数据库会话（可选，如果不提供将使用SQLite）
    """
    try:
        logger.info("🚀 开始初始化聊天室系统...")
        
        # 如果没有提供数据库会话，尝试创建一个
        if db_session is None:
            # 检查是否启用了MariaDB
            mariadb_enabled = os.getenv('MARIADB_ENABLED', 'false').lower() == 'true'
            
            if mariadb_enabled:
                logger.info("📦 尝试使用MariaDB数据库")
                try:
                    from .mariadb_config import initialize_mariadb_for_chatroom, get_mariadb_session
                    
                    # 初始化MariaDB
                    if initialize_mariadb_for_chatroom():
                        # 使用MariaDB会话上下文管理器的方式
                        db_session = "mariadb"  # 标记使用MariaDB
                        logger.info("✅ MariaDB数据库配置成功")
                    else:
                        logger.warning("⚠️ MariaDB初始化失败，降级到SQLite")
                        db_session = None
                        
                except ImportError as e:
                    logger.warning(f"⚠️ 无法导入MariaDB配置: {e}")
                    db_session = None
            
            # 如果MariaDB不可用或未启用，使用SQLite
            if db_session is None:
                logger.info("📦 使用内置SQLite数据库")
                try:
                    from .simple_db import SimpleDatabaseSession, create_chatroom_tables
                    
                    # 确保数据库表存在
                    create_chatroom_tables()
                    
                    # 创建数据库会话
                    db_session = SimpleDatabaseSession()
                    
                except Exception as e:
                    logger.error(f"❌ 无法创建数据库会话: {e}")
                    return False
        
        # 导入聊天室组件
        from .services.database_service import ChatroomDatabaseService
        from .services.online_user_manager import OnlineUserManager
        from .services.permissions import setup_chatroom_permissions
        from .websocket.connection_manager import ConnectionManager
        from .websocket.handlers import ChatroomWebSocketHandler
        from .api.routes import chatroom_bp
        
        logger.info("✅ 聊天室模块导入成功")
        
        # 初始化各个组件
        logger.info("🔧 初始化聊天室组件...")
        
        # 1. 数据库服务
        db_service = ChatroomDatabaseService(db_session)
        
        # 2. 在线用户管理器
        online_manager = OnlineUserManager()
        
        # 3. 连接管理器
        connection_manager = ConnectionManager()
        
        # 4. WebSocket处理器
        ws_handler = ChatroomWebSocketHandler(
            socketio=socketio,
            db_service=db_service,
            online_manager=online_manager,
            connection_manager=connection_manager
        )
        
        # 5. 注册WebSocket事件
        ws_handler.register_handlers()
        
        # 6. 注册HTTP API路由
        app.register_blueprint(chatroom_bp, url_prefix='/api/v1/chatroom')
        
        # 7. 设置权限系统（安全地尝试）
        try:
            setup_chatroom_permissions(app)
        except Exception as e:
            logger.warning(f"⚠️ 权限系统设置失败: {e}")
        
        # 8. 保存实例到app中，供其他模块使用
        app.chatroom_db_service = db_service
        app.chatroom_online_manager = online_manager
        app.chatroom_connection_manager = connection_manager
        app.chatroom_ws_handler = ws_handler
        
        # 9. 添加关闭钩子
        @app.teardown_appcontext
        def cleanup_chatroom_system(error):
            """应用关闭时清理聊天室系统"""
            try:
                # 注意：在Flask的teardown_appcontext中，我们不能使用async/await
                # 所以这里只做简单的清理，复杂的异步清理应该在其他地方处理
                if hasattr(app, 'chatroom_online_manager'):
                    # OnlineUserManager的cleanup是async方法，这里不直接调用
                    logger.info("聊天室在线用户管理器存在，需要异步清理")
                if hasattr(app, 'chatroom_connection_manager'):
                    # ConnectionManager没有cleanup方法，但可以清理连接
                    try:
                        # 如果有同步的清理方法，可以在这里调用
                        connection_count = len(app.chatroom_connection_manager.connections)
                        logger.info(f"聊天室连接管理器清理，当前连接数: {connection_count}")
                    except Exception as cm_error:
                        logger.warning(f"连接管理器清理警告: {cm_error}")
            except Exception as e:
                logger.error(f"聊天室系统清理失败: {e}")
        
        logger.info("✅ 聊天室系统初始化完成")
        logger.info("🔌 WebSocket端点: /chatroom")
        logger.info("🌐 HTTP API端点: /api/v1/chatroom")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ 聊天室模块导入失败: {e}")
        logger.error("请确保聊天室代码文件存在，或运行部署脚本进行安装")
        return False
        
    except Exception as e:
        logger.error(f"❌ 聊天室系统初始化失败: {e}", exc_info=True)
        return False


class ChatroomApp:
    """聊天室应用管理类"""
    
    def __init__(self, app=None, socketio=None, db_session=None):
        self.app = app
        self.socketio = socketio
        self.db_session = db_session
        self.initialized = False
        
        if app is not None:
            self.init_app(app, socketio, db_session)
    
    def init_app(self, app, socketio=None, db_session=None):
        """初始化应用"""
        self.app = app
        self.socketio = socketio or getattr(app, 'socketio', None)
        self.db_session = db_session
        
        if self.socketio is None:
            logger.warning("⚠️ 没有提供SocketIO实例，聊天室WebSocket功能将不可用")
            return False
        
        success = init_chatroom_system(app, self.socketio, self.db_session)
        self.initialized = success
        return success
    
    def cleanup(self):
        """清理资源"""
        if self.app and hasattr(self.app, 'chatroom_online_manager'):
            try:
                self.app.chatroom_online_manager.cleanup()
                self.app.chatroom_connection_manager.cleanup()
                logger.info("✅ 聊天室系统清理完成")
            except Exception as e:
                logger.error(f"聊天室系统清理失败: {e}")


# 便捷的初始化函数
def setup_chatroom(app, socketio=None, db_session=None):
    """
    便捷的聊天室系统设置函数
    
    Args:
        app: Flask应用实例
        socketio: SocketIO实例（可选）
        db_session: 数据库会话（可选）
    
    Returns:
        ChatroomApp实例
    """
    chatroom_app = ChatroomApp(app, socketio, db_session)
    return chatroom_app


# 导出主要接口
__all__ = [
    'init_chatroom_system',
    'ChatroomApp', 
    'setup_chatroom'
]
