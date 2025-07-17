"""
DifyChatBackend主应用文件 - 重构版本
"""
from flask import Flask
import logging
import logging.handlers
import os
from dotenv import load_dotenv

# 导入API路由
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from api.auth_routes import login
from api.chat_routes import api_conversations, api_chat, api_agents

# 创建Flask应用
app = Flask(__name__)
load_dotenv()

# 配置日志
def setup_logging():
    """配置日志系统"""
    # 本地文件日志
    logging.basicConfig(
        filename='login.log', 
        level=logging.INFO, 
        format='%(asctime)s %(levelname)s %(message)s', 
        encoding='utf-8'
    )
    
    # 远程syslog日志（如果配置了的话）
    syslog_host = os.environ.get('SYSLOG_HOST')
    syslog_port = int(os.environ.get('SYSLOG_PORT', '514'))
    
    if syslog_host:
        try:
            remote_syslog = logging.handlers.SysLogHandler(
                address=(syslog_host, syslog_port)
            )
            remote_syslog.setLevel(logging.INFO)
            remote_syslog.setFormatter(
                logging.Formatter('DifyChatBackend: %(asctime)s %(levelname)s %(message)s')
            )
            logging.getLogger().addHandler(remote_syslog)
        except Exception as e:
            logging.warning(f"Failed to setup remote syslog: {e}")

# 注册路由
def register_routes():
    """注册API路由"""
    # 认证相关路由
    app.route('/api/login', methods=['POST'])(login)
    
    # 对话相关路由
    app.route('/api/conversations', methods=['GET'])(api_conversations)
    app.route('/api/chat', methods=['POST'])(api_chat)
    app.route('/api/agents', methods=['GET'])(api_agents)

# 错误处理
@app.errorhandler(404)
def not_found(error):
    return {'success': False, 'message': 'API接口不存在'}, 404

@app.errorhandler(500)
def internal_error(error):
    return {'success': False, 'message': '服务器内部错误'}, 500

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Unhandled exception: {e}", exc_info=True)
    return {'success': False, 'message': '服务器错误'}, 500

# 健康检查接口
@app.route('/health')
def health_check():
    """健康检查接口"""
    return {
        'status': 'healthy',
        'version': '2.0.0-alpha',
        'timestamp': int(__import__('time').time())
    }

# 初始化应用
def create_app():
    """创建并配置Flask应用"""
    setup_logging()
    register_routes()
    
    logging.info("DifyChatBackend started successfully")
    return app

if __name__ == '__main__':
    app = create_app()
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', '5000'))
    
    app.run(host=host, port=port, debug=debug_mode)
