"""
DifyChatBackend主应用文件 - 重构版本
"""
from flask import Flask, jsonify
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

# 导入API路由
from api.auth_routes import login, refresh_token, logout
from api.chat_routes import (
    api_conversations, api_chat, api_agents,
    api_user_permissions, api_agent_config, api_preload_cache,
    api_refresh_agent_cache, api_invalidate_agent_cache, api_agent_cache_stats
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
    """注册路由"""
    # 认证路由（注意：login和refresh_token不需要认证）
    app.add_url_rule('/login', 'login', login, methods=['POST'])
    app.add_url_rule('/refresh', 'refresh_token', refresh_token, methods=['POST'])
    app.add_url_rule('/logout', 'logout', logout, methods=['POST'])
    
    # 聊天相关路由（这些已经有装饰器保护）
    app.add_url_rule('/api/conversations', 'api_conversations', api_conversations, methods=['GET'])
    app.add_url_rule('/api/chat', 'api_chat', api_chat, methods=['POST'])
    app.add_url_rule('/api/agents', 'api_agents', api_agents, methods=['GET'])
    
    # 智能体缓存管理路由
    app.add_url_rule('/api/user/permissions', 'api_user_permissions', api_user_permissions, methods=['GET'])
    app.add_url_rule('/api/agent/config', 'api_agent_config', api_agent_config, methods=['GET'])
    app.add_url_rule('/api/cache/preload', 'api_preload_cache', api_preload_cache, methods=['POST'])
    app.add_url_rule('/api/cache/refresh', 'api_refresh_agent_cache', api_refresh_agent_cache, methods=['POST'])
    app.add_url_rule('/api/cache/invalidate', 'api_invalidate_agent_cache', api_invalidate_agent_cache, methods=['DELETE'])
    app.add_url_rule('/api/cache/stats', 'api_agent_cache_stats', api_agent_cache_stats, methods=['GET'])
    
    # 健康检查路由
    @app.route('/health')
    def health_check():
        """健康检查端点"""
        config = get_config()
        return jsonify({
            'status': 'healthy',
            'environment': config.env,
            'version': '2.0.0-alpha',
            'timestamp': int(__import__('time').time())
        })
    
    # 缓存健康检查路由
    @app.route('/health/cache')
    def cache_health_check():
        """缓存健康检查端点"""
        cache_manager = get_cache_manager()
        if cache_manager:
            health_status = cache_manager.health_check()
            cache_stats = dify_service.get_cache_stats()
            
            return jsonify({
                **health_status,
                "dify_cache_config": {
                    "conversations_ttl": cache_stats.get("conversations_cache_ttl"),
                    "agents_ttl": cache_stats.get("agents_cache_ttl")
                }
            })
        else:
            return jsonify({
                "status": "not_initialized",
                "enabled": False,
                "message": "缓存管理器未初始化"
            }), 503
    
    # 错误处理器
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not Found', 'message': '请求的资源不存在'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal Server Error', 'message': '服务器内部错误'}), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        logging.error(f"Unhandled exception: {e}", exc_info=True)
        return jsonify({'error': 'Unexpected Error', 'message': '服务器发生意外错误'}), 500

# 创建应用实例
app = create_app()

if __name__ == '__main__':
    config = get_config()
    
    logging.info(f"启动DifyChatBackend服务 - 环境: {config.env}")
    logging.info(f"服务器配置: {config.server.host}:{config.server.port}")
    
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
