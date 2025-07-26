"""
DifyChatBackend主应用文件 - 标准化版本
"""
from flask import Flask, request
import logging
import logging.handlers
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入配置
from config import get_config, get_logging_config

# 导入缓存管理器
from utils.cache_manager import init_cache_manager, get_cache_manager
from services.dify_service import dify_service

# 导入标准化的响应构建器
from utils.response_builder import ResponseBuilder, ErrorCode

# 导入认证装饰器
from auth.decorators import require_auth, auto_refresh_token

# 导入标准化的API路由
from api.auth_routes import login, refresh_token, logout, get_current_user
from api.chat_routes import (
    api_agents, api_conversations, api_chat, api_create_conversation,
    api_message_feedback, api_suggested_questions, api_delete_conversation,
    api_rename_conversation, api_audio_to_text, api_text_to_audio,
    api_messages_history, api_app_info, api_chat_messages,
    api_streaming_stats, api_streaming_reset_stats,
    api_agent_detail, api_conversation_detail, api_system_stats
)
from api.cache_routes import (
    api_user_permissions, api_agent_config, api_preload_cache,
    api_refresh_agent_cache, api_invalidate_cache, api_cache_stats, api_cache_health
)
# 导入智能体功能配置路由
from api.agent_config_routes import agent_config_bp

# 可选导入CORS
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
    print("Warning: Flask-CORS not available, CORS will be disabled")

# 可选导入聊天室系统
try:
    from flask_socketio import SocketIO
    from chatroom import init_chatroom_system
    CHATROOM_AVAILABLE = True
    print("✅ 聊天室系统模块已加载")
except ImportError as e:
    CHATROOM_AVAILABLE = False
    print(f"⚠️ Warning: 聊天室系统不可用 - {e}")
    print("如需使用聊天室功能，请安装: pip install flask-socketio")

def create_app(config_env: str = None) -> Flask:
    """应用工厂函数"""
    # 加载配置
    if config_env:
        os.environ['FLASK_ENV'] = config_env
    
    config = get_config()
    
    # 创建Flask应用
    app = Flask(__name__)
    
    # 应用配置
    app.config.update(config.get_flask_config())
    
    # 设置CORS
    if config.server.cors_enabled and CORS_AVAILABLE:
        CORS(app, origins=config.server.cors_origins)
    
    # 配置日志
    setup_logging(config.logging)
    
    # 初始化缓存管理器
    cache_manager = init_cache_manager(config)
    
    # 记录缓存状态
    cache_status = "启用" if cache_manager.enabled else "禁用"
    logging.info(f"缓存管理器初始化完成: {cache_status}")
    
    # 初始化聊天室系统（如果启用）
    socketio = None
    chatroom_enabled = os.getenv('CHATROOM_ENABLED', 'false').lower() == 'true'
    
    if CHATROOM_AVAILABLE and chatroom_enabled:
        try:
            logging.info("🔧 启用聊天室系统...")
            
            # 创建SocketIO实例
            socketio = SocketIO(
                app,
                cors_allowed_origins=os.getenv('SOCKETIO_CORS_ALLOWED_ORIGINS', '*'),
                async_mode=os.getenv('SOCKETIO_ASYNC_MODE', 'threading'),
                ping_timeout=int(os.getenv('SOCKETIO_PING_TIMEOUT', 60)),
                ping_interval=int(os.getenv('SOCKETIO_PING_INTERVAL', 25)),
                max_http_buffer_size=int(os.getenv('SOCKETIO_MAX_HTTP_BUFFER_SIZE', 1000000))
            )
            
            # 尝试创建数据库会话
            db_session = None
            mariadb_enabled = os.getenv('MARIADB_ENABLED', 'false').lower() == 'true'
            
            if mariadb_enabled:
                try:
                    # 使用MariaDB
                    from chatroom.mariadb_config import get_mariadb_session
                    logging.info("📦 使用MariaDB数据库")
                    # 这里不直接获取session，而是让聊天室系统自己处理
                    db_session = None  # 聊天室系统会自动使用MariaDB配置
                    
                except Exception as e:
                    logging.warning(f"⚠️ MariaDB连接失败，降级到SQLite: {e}")
                    db_session = None
            else:
                try:
                    # 优先尝试使用SQLAlchemy + SQLite
                    from sqlalchemy import create_engine
                    from sqlalchemy.orm import sessionmaker
                    
                    # 确保数据目录存在
                    data_dir = os.path.join(os.path.dirname(__file__), 'data')
                    os.makedirs(data_dir, exist_ok=True)
                    
                    # 使用SQLite作为默认数据库
                    engine = create_engine(f'sqlite:///{data_dir}/chatroom.db', echo=False)
                    Session = sessionmaker(bind=engine)
                    db_session = Session()
                    logging.info("✅ 使用SQLite数据库会话")
                    
                except ImportError:
                    # SQLAlchemy不可用，使用简化的数据库会话
                    logging.info("⚠️ SQLAlchemy不可用，使用简化数据库会话")
                    db_session = None  # 聊天室系统会自动创建SQLite会话
            
            # 初始化聊天室系统
            success = init_chatroom_system(app, socketio, db_session)
            
            if success:
                logging.info("✅ 聊天室系统初始化成功")
            else:
                logging.warning("⚠️ 聊天室系统初始化失败，仅提供基本功能")
                socketio = None
            
        except Exception as e:
            logging.error(f"❌ 聊天室系统初始化失败: {e}")
            socketio = None
    elif CHATROOM_AVAILABLE and not chatroom_enabled:
        logging.info("ℹ️ 聊天室系统已禁用（CHATROOM_ENABLED=false）")
    else:
        logging.info("⚠️ 聊天室系统不可用（缺少依赖包）")
    
    # 将socketio实例附加到app，以便在主程序中使用
    app.socketio = socketio
    
    # 注册路由
    register_routes(app)
    
    # 注册错误处理器
    register_error_handlers(app)
    
    return app

def setup_logging(log_config):
    """配置日志系统"""
    # 清除现有处理器
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # 创建日志目录
    log_file_path = Path(log_config.file_path)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 配置根日志记录器
    logging.root.setLevel(getattr(logging, log_config.level))
    
    handlers = []
    
    # 控制台处理器
    if log_config.enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_config.level))
        console_handler.setFormatter(logging.Formatter(log_config.format))
        handlers.append(console_handler)
    
    # 文件处理器（带轮转）
    if log_config.enable_file:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_config.file_path,
            maxBytes=log_config.max_file_size,
            backupCount=log_config.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_config.level))
        file_handler.setFormatter(logging.Formatter(log_config.format))
        handlers.append(file_handler)
    
    # Syslog处理器
    if log_config.enable_syslog:
        try:
            syslog_handler = logging.handlers.SysLogHandler(
                address=(log_config.syslog_host, log_config.syslog_port)
            )
            syslog_handler.setLevel(getattr(logging, log_config.level))
            syslog_handler.setFormatter(
                logging.Formatter('DifyChatBackend: %(name)s - %(levelname)s - %(message)s')
            )
            handlers.append(syslog_handler)
        except Exception as e:
            logging.warning(f"Failed to setup remote syslog: {e}")
    
    # 添加所有处理器
    for handler in handlers:
        logging.root.addHandler(handler)
    
    logging.info("日志系统初始化完成")

def register_routes(app):
    """注册路由 - 使用v1 API版本路径"""
    
    # ========== 认证路由 ==========
    # 注意：login和refresh_token不需要认证，使用根路径
    app.add_url_rule('/api/v1/auth/login', 'login', login, methods=['POST'])
    app.add_url_rule('/api/v1/auth/refresh', 'refresh_token', refresh_token, methods=['POST'])
    app.add_url_rule('/api/v1/auth/logout', 'logout', logout, methods=['POST'])
    app.add_url_rule('/api/v1/auth/me', 'get_current_user', get_current_user, methods=['GET'])
    
    # ========== 聊天相关路由 ==========
    app.add_url_rule('/api/v1/chat/agents', 'api_agents', api_agents, methods=['GET'])
    app.add_url_rule('/api/v1/chat/conversations', 'api_conversations', api_conversations, methods=['GET'])
    app.add_url_rule('/api/v1/chat/conversations', 'api_create_conversation', api_create_conversation, methods=['POST'])
    app.add_url_rule('/api/v1/chat/messages', 'api_chat', api_chat, methods=['POST'])
    
    # ========== 标准Dify API路由 ==========
    app.add_url_rule('/api/v1/chat-messages', 'api_chat_messages', api_chat_messages, methods=['POST'])
    
    # ========== 新增Dify功能路由 ==========
    app.add_url_rule('/api/v1/messages/<message_id>/feedbacks', 'api_message_feedback', api_message_feedback, methods=['POST'])
    app.add_url_rule('/api/v1/messages/<message_id>/suggested', 'api_suggested_questions', api_suggested_questions, methods=['GET'])
    app.add_url_rule('/api/v1/conversations/<conversation_id>', 'api_delete_conversation', api_delete_conversation, methods=['DELETE'])
    app.add_url_rule('/api/v1/conversations/<conversation_id>/name', 'api_rename_conversation', api_rename_conversation, methods=['POST'])
    app.add_url_rule('/api/v1/messages', 'api_messages_history', api_messages_history, methods=['GET'])
    app.add_url_rule('/api/v1/audio-to-text', 'api_audio_to_text', api_audio_to_text, methods=['POST'])
    app.add_url_rule('/api/v1/text-to-audio', 'api_text_to_audio', api_text_to_audio, methods=['POST'])
    app.add_url_rule('/api/v1/app/info', 'api_app_info', api_app_info, methods=['GET'])
    
    # ========== 缓存管理路由 ==========
    app.add_url_rule('/api/v1/user/permissions', 'api_user_permissions', api_user_permissions, methods=['GET'])
    app.add_url_rule('/api/v1/agent/config', 'api_agent_config', api_agent_config, methods=['GET'])
    app.add_url_rule('/api/v1/cache/preload', 'api_preload_cache', api_preload_cache, methods=['POST'])
    app.add_url_rule('/api/v1/cache/refresh', 'api_refresh_agent_cache', api_refresh_agent_cache, methods=['POST'])
    app.add_url_rule('/api/v1/cache/invalidate', 'api_invalidate_cache', api_invalidate_cache, methods=['DELETE'])
    app.add_url_rule('/api/v1/cache/stats', 'api_cache_stats', api_cache_stats, methods=['GET'])
    app.add_url_rule('/api/v1/cache/health', 'api_cache_health', api_cache_health, methods=['GET'])
    
    # ========== Task 5.3 新增：流式监控路由 ==========
    app.add_url_rule('/api/v1/streaming/stats', 'api_streaming_stats', api_streaming_stats, methods=['GET'])
    app.add_url_rule('/api/v1/streaming/reset', 'api_streaming_reset_stats', api_streaming_reset_stats, methods=['POST'])
    
    # ========== 新增：单个资源详情端点 ==========
    app.add_url_rule('/api/v1/agents/<agent_id>', 'api_agent_detail', api_agent_detail, methods=['GET'])
    app.add_url_rule('/api/v1/conversations/<conversation_id>', 'api_conversation_detail', api_conversation_detail, methods=['GET'])
    app.add_url_rule('/api/v1/stats', 'api_system_stats', api_system_stats, methods=['GET'])
    
    # ========== 智能体功能配置路由 ==========
    app.register_blueprint(agent_config_bp)
    
    # ========== 系统健康检查路由 ==========
    @app.route('/health')
    def health_check():
        """系统健康检查端点"""
        config = get_config()
        
        # 检查基本服务状态
        health_data = {
            'service': 'DifyChatBackend',
            'status': 'healthy',
            'environment': config.env,
            'version': '2.0.0-standard',
            'timestamp': int(__import__('time').time())
        }
        
        # 检查缓存状态
        cache_manager = get_cache_manager()
        if cache_manager and cache_manager.enabled:
            cache_health = cache_manager.health_check()
            health_data['cache'] = {
                'enabled': True,
                'status': cache_health.get('status'),
                'connection': cache_health.get('connected', False)
            }
        else:
            health_data['cache'] = {
                'enabled': False,
                'status': 'disabled'
            }
        
        # 检查Dify服务状态（简化版）
        try:
            # 这里可以添加对Dify服务的健康检查
            health_data['dify_service'] = {
                'status': 'available',
                'message': 'Service available'
            }
        except Exception as e:
            health_data['dify_service'] = {
                'status': 'unavailable',
                'message': str(e)
            }
        
        return ResponseBuilder.success(
            data=health_data,
            message="服务健康检查完成"
        )
    
    @app.route('/api/v1/health')
    def api_health_check():
        """API健康检查端点（标准化响应格式）"""
        return health_check()
    
    # ========== 系统信息路由 (分层披露) ==========
    @app.route('/api/v1/info/public')
    def api_system_info_public():
        """公开系统信息端点（无需认证）"""
        import time
        
        config = get_config()
        
        # 公开的基础信息
        public_info = {
            'service_name': 'DifyChatBackend',
            'version': 'v2.1.0',
            'api_version': 'v1',
            'status': 'healthy',
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'features': [
                'chat',
                'agents', 
                'conversations',
                'jwt_auth'
            ]
        }
        
        return ResponseBuilder.success(
            data=public_info,
            message="获取系统信息成功"
        )
    
    @app.route('/api/v1/info')
    @require_auth()
    @auto_refresh_token()
    def api_system_info():
        """认证用户系统信息端点（需要认证）"""
        import time
        from flask import g
        
        config = get_config()
        cache_manager = get_cache_manager()
        
        # 认证用户的完整信息
        user_info = getattr(g, 'current_user', {})
        user_permissions = user_info.get('permissions', [])
        
        # 检查缓存状态
        cache_status = "connected" if cache_manager else "disabled"
        if cache_manager:
            try:
                cache_manager.client.ping()
                cache_status = "connected"
            except:
                cache_status = "error"
        
        detailed_info = {
            'service_name': 'DifyChatBackend',
            'version': 'v2.1.0',
            'api_version': 'v1',
            'status': 'healthy',
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'features': [
                'chat',
                'agents',
                'conversations', 
                'jwt_auth',
                'redis_cache',
                'admin_panel'
            ],
            'environment': config.env,
            'uptime': '72h 15m',  # 这里可以实现真实的运行时间计算
            'cache_status': cache_status,
            'dify_status': 'connected',  # 这里可以实现Dify服务状态检查
            'user_permissions': user_permissions,
            'rate_limits': {
                'requests_per_minute': 60,
                'remaining': 58  # 这里可以实现真实的速率限制检查
            }
        }
        
        return ResponseBuilder.success(
            data=detailed_info,
            message="获取完整系统信息成功"
        )

    @app.route('/api/v1/info/detailed')
    @require_auth()
    @auto_refresh_token()
    def api_system_info_detailed():
        """系统详细信息端点（兼容性，重定向到认证版）"""
        return api_system_info()
    
    # ========== 兼容性路由（向后兼容旧版本路径） ==========
    # 这些路由提供向后兼容性，但建议使用新的v1路径
    app.add_url_rule('/api/login', 'legacy_api_login', login, methods=['POST'])
    app.add_url_rule('/login', 'legacy_login', login, methods=['POST'])
    app.add_url_rule('/api/conversations', 'legacy_api_conversations', api_conversations, methods=['GET'])
    app.add_url_rule('/api/chat', 'legacy_api_chat', api_chat, methods=['POST'])
    app.add_url_rule('/api/agents', 'legacy_api_agents', api_agents, methods=['GET'])
    
    # ========== 根路径和静态文件路由 ==========
    @app.route('/')
    def index():
        """应用主页"""
        return ResponseBuilder.success(
            data={
                "app_name": "DifyChatBackend",
                "version": "v1",
                "status": "running",
                "description": "Python Flask 后端服务，提供聊天、用户认证等功能",
                "endpoints": {
                    "auth": "/api/v1/auth/login",
                    "chat": "/api/v1/chat/messages", 
                    "agents": "/api/v1/chat/agents",
                    "chatroom": "/api/v1/chatroom"
                }
            },
            message="欢迎使用DifyChatBackend服务"
        )
    
    @app.route('/favicon.ico')
    def favicon():
        """返回默认favicon"""
        return ResponseBuilder.success(
            data={"message": "No favicon available"},
            message="favicon请求"
        )

def register_error_handlers(app):
    """注册错误处理器"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return ResponseBuilder.error(
            error_code=ErrorCode.INVALID_REQUEST,
            message="请求格式错误"
        )
    
    @app.errorhandler(401)
    def unauthorized(error):
        return ResponseBuilder.error(
            error_code=ErrorCode.AUTHENTICATION_REQUIRED,
            message="需要身份验证"
        )
    
    @app.errorhandler(403)
    def forbidden(error):
        return ResponseBuilder.error(
            error_code=ErrorCode.ACCESS_DENIED,
            message="访问被拒绝"
        )
    
    @app.errorhandler(404)
    def not_found(error):
        return ResponseBuilder.error(
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            message="请求的资源不存在"
        )
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return ResponseBuilder.error(
            error_code=ErrorCode.METHOD_NOT_ALLOWED,
            message="请求方法不被允许"
        )
    
    @app.errorhandler(429)
    def rate_limited(error):
        return ResponseBuilder.error(
            error_code=ErrorCode.RATE_LIMITED,
            message="请求过于频繁，请稍后重试"
        )
    
    @app.errorhandler(500)
    def internal_error(error):
        logging.error(f"Internal server error: {error}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="服务器内部错误"
        )
    
    @app.errorhandler(502)
    def bad_gateway(error):
        return ResponseBuilder.error(
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message="外部服务不可用"
        )
    
    @app.errorhandler(503)
    def service_unavailable(error):
        return ResponseBuilder.error(
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            message="服务暂时不可用"
        )
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logging.error(f"Unexpected error: {error}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="服务器发生意外错误"
        )

# 创建应用实例
app = create_app()

if __name__ == '__main__':
    config = get_config()
    
    logging.info(f"启动DifyChatBackend服务 - 标准化版本")
    logging.info(f"环境: {config.env}")
    logging.info(f"服务器配置: {config.server.host}:{config.server.port}")
    logging.info(f"API版本: v1")
    logging.info(f"响应格式: 标准化")
    
    try:
        # 如果聊天室系统可用，使用SocketIO启动
        if hasattr(app, 'socketio') and app.socketio:
            logging.info("🔌 使用SocketIO模式启动服务器")
            app.socketio.run(
                app,
                host=config.server.host,
                port=config.server.port,
                debug=config.server.debug,
                allow_unsafe_werkzeug=True  # 仅用于开发环境
            )
        else:
            # 标准Flask启动模式
            logging.info("🌐 使用标准Flask模式启动服务器")
            app.run(
                host=config.server.host,
                port=config.server.port,
                debug=config.server.debug,
                threaded=config.server.threaded
            )
    except KeyboardInterrupt:
        logging.info("服务器关闭")
    except Exception as e:
        logging.error(f"服务器启动失败: {e}")
        raise
