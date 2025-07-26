#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天室系统启动脚本
"""

import os
import sys
from flask import Flask
from flask_socketio import SocketIO

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    
    # 加载配置
    config_name = os.environ.get('FLASK_ENV', 'development')
    
    try:
        from chatroom_config import config
        app.config.from_object(config[config_name])
    except ImportError:
        print("❌ 无法加载配置文件，请先运行部署脚本")
        sys.exit(1)
    
    # 初始化SocketIO
    socketio = SocketIO(
        app,
        async_mode=app.config.get('SOCKETIO_ASYNC_MODE', 'threading'),
        cors_allowed_origins=app.config.get('SOCKETIO_CORS_ALLOWED_ORIGINS', "*"),
        ping_timeout=app.config.get('SOCKETIO_PING_TIMEOUT', 60),
        ping_interval=app.config.get('SOCKETIO_PING_INTERVAL', 25)
    )
    
    # 初始化聊天室系统
    try:
        from chatroom import init_chatroom_system
        
        # 创建数据库会话（这里需要根据你的项目调整）
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        Session = sessionmaker(bind=engine)
        db_session = Session()
        
        # 初始化聊天室系统
        init_chatroom_system(app, socketio, db_session)
        
        print("✅ 聊天室系统初始化成功")
        
    except ImportError as e:
        print(f"❌ 无法导入聊天室模块: {e}")
        print("请确保聊天室代码文件存在")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 聊天室系统初始化失败: {e}")
        sys.exit(1)
    
    return app, socketio

def main():
    """主函数"""
    print("🚀 启动聊天室系统...")
    
    # 创建应用
    app, socketio = create_app()
    
    # 获取启动参数
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"🌐 服务器地址: http://{host}:{port}")
    print(f"🔌 WebSocket地址: ws://{host}:{port}/chatroom")
    
    if debug:
        print("🐛 开发模式已启用")
    
    try:
        # 启动服务器
        socketio.run(
            app, 
            host=host, 
            port=port, 
            debug=debug,
            allow_unsafe_werkzeug=True  # 仅用于开发环境
        )
    except KeyboardInterrupt:
        print("\n⏹️ 服务器已停止")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()