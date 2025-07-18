"""
DifyChatBackend主应用文件 - 标准化版本
"""
from flask import Flask
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

# 导入标准化的API路由
from api.auth_routes import login, refresh_token, logout, get_current_user
from api.chat_routes import (
    api_agents, api_conversations, api_chat, api_create_conversation,
    api_message_feedback, api_suggested_questions, api_delete_conversation,
    api_rename_conversation, api_audio_to_text, api_text_to_audio,
    api_messages_history, api_app_info, api_chat_messages
)
from api.cache_routes import (
    api_user_permissions, api_agent_config, api_preload_cache,
    api_refresh_agent_cache, api_invalidate_cache, api_cache_stats, api_cache_health
)

# 可选导入CORS
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
    print("Warning: Flask-CORS not available, CORS will be disabled")

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
    
    # ========== 系统信息路由 (公开访问) ==========
    @app.route('/api/v1/info')
    def api_system_info():
        """系统信息端点（公开访问）"""
        config = get_config()
        
        system_info = {
            'name': 'DifyChatBackend API',
            'version': '2.0.0-standard',
            'description': '基于Dify的智能对话后端服务 - 标准化版本',
            'environment': config.env,
            'api_version': 'v1',
            'features': [
                'JWT认证系统',
                'Redis缓存管理', 
                '智能体对话',
                '会话管理',
                '权限控制',
                '标准化API响应'
            ],
            'endpoints': {
                'authentication': '/api/v1/auth/',
                'chat': '/api/v1/chat/',
                'health': '/api/v1/health',
                'cache': '/api/v1/cache/'
            },
            'documentation': {
                'response_format': '/docs/api-response-format',
                'error_codes': '/docs/error-codes', 
                'authentication': '/docs/authentication'
            }
        }
        
        return ResponseBuilder.success(
            data=system_info,
            message="系统信息获取成功"
        )
    
    # ========== 兼容性路由（向后兼容旧版本路径） ==========
    # 这些路由提供向后兼容性，但建议使用新的v1路径
    app.add_url_rule('/login', 'legacy_login', login, methods=['POST'])
    app.add_url_rule('/api/conversations', 'legacy_api_conversations', api_conversations, methods=['GET'])
    app.add_url_rule('/api/chat', 'legacy_api_chat', api_chat, methods=['POST'])
    app.add_url_rule('/api/agents', 'legacy_api_agents', api_agents, methods=['GET'])

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
