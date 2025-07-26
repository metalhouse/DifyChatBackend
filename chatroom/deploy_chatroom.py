# 聊天室系统快速部署脚本

import os
import sys
import subprocess
import json
from pathlib import Path

def print_banner():
    """打印欢迎横幅"""
    print("""
    ╔══════════════════════════════════════════════╗
    ║          聊天室系统快速部署工具              ║
    ║      Chatroom System Quick Deploy Tool       ║
    ╚══════════════════════════════════════════════╝
    """)

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ 需要Python 3.7或更高版本")
        return False
    print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
    return True

def install_dependencies():
    """安装必要的依赖包"""
    print("\n📦 安装依赖包...")
    
    dependencies = [
        "flask",
        "flask-socketio",
        "sqlalchemy",
        "redis",
        "pyjwt",
        "cryptography",
        "python-socketio[client]",
        "requests"
    ]
    
    for dep in dependencies:
        try:
            print(f"  安装 {dep}...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", dep
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  ✅ {dep} 安装成功")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ {dep} 安装失败: {e}")
            return False
    
    print("✅ 所有依赖包安装完成")
    return True

def create_config_file():
    """创建配置文件"""
    print("\n⚙️ 创建配置文件...")
    
    config_content = '''
# 聊天室系统配置文件
import os
from datetime import timedelta

class ChatroomConfig:
    """聊天室系统配置"""
    
    # 基本配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///chatroom.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Redis配置
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/1'
    
    # JWT配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # WebSocket配置
    SOCKETIO_ASYNC_MODE = 'threading'
    SOCKETIO_PING_TIMEOUT = 60
    SOCKETIO_PING_INTERVAL = 25
    SOCKETIO_CORS_ALLOWED_ORIGINS = "*"
    
    # 聊天室配置
    CHATROOM_MAX_USERS_DEFAULT = 100
    CHATROOM_MESSAGE_MAX_LENGTH = 4000
    CHATROOM_HISTORY_LIMIT = 50
    CHATROOM_MESSAGE_RATE_LIMIT = 10  # 消息/分钟
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'chatroom.log'

# 主配置类
class Config(ChatroomConfig):
    pass

class DevelopmentConfig(ChatroomConfig):
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(ChatroomConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql://user:pass@localhost/chatroom'

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
'''
    
    config_path = Path("chatroom_config.py")
    config_path.write_text(config_content.strip(), encoding='utf-8')
    print(f"✅ 配置文件创建: {config_path}")
    return str(config_path)

def create_startup_script():
    """创建启动脚本"""
    print("\n🚀 创建启动脚本...")
    
    startup_content = '''#!/usr/bin/env python3
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
        print("\\n⏹️ 服务器已停止")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
'''
    
    startup_path = Path("start_chatroom.py")
    startup_path.write_text(startup_content.strip(), encoding='utf-8')
    
    # 在Unix系统上设置执行权限
    if os.name != 'nt':
        os.chmod(startup_path, 0o755)
    
    print(f"✅ 启动脚本创建: {startup_path}")
    return str(startup_path)

def create_environment_file():
    """创建环境变量文件"""
    print("\n🌍 创建环境变量文件...")
    
    env_content = '''# 聊天室系统环境变量配置

# Flask配置
FLASK_ENV=development
HOST=0.0.0.0
PORT=5000

# 安全配置
SECRET_KEY=your-super-secret-key-change-this-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-this-in-production

# 数据库配置
DATABASE_URL=sqlite:///chatroom.db
# 生产环境MySQL示例:
# DATABASE_URL=mysql://username:password@localhost/chatroom_db

# Redis配置
REDIS_URL=redis://localhost:6379/1

# 日志配置
LOG_LEVEL=INFO
'''
    
    env_path = Path(".env")
    if not env_path.exists():
        env_path.write_text(env_content.strip(), encoding='utf-8')
        print(f"✅ 环境变量文件创建: {env_path}")
    else:
        print(f"ℹ️ 环境变量文件已存在: {env_path}")
    
    return str(env_path)

def create_docker_files():
    """创建Docker相关文件"""
    print("\n🐳 创建Docker配置文件...")
    
    # Dockerfile
    dockerfile_content = '''FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python", "start_chatroom.py"]
'''
    
    # docker-compose.yml
    compose_content = '''version: '3.8'

services:
  chatroom:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=mysql://chatroom:password@db:3306/chatroom_db
      - REDIS_URL=redis://redis:6379/1
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs

  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=rootpassword
      - MYSQL_DATABASE=chatroom_db
      - MYSQL_USER=chatroom
      - MYSQL_PASSWORD=password
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  mysql_data:
  redis_data:
'''
    
    # requirements.txt
    requirements_content = '''Flask==2.3.3
Flask-SocketIO==5.3.6
SQLAlchemy==2.0.23
redis==5.0.1
PyJWT==2.8.0
cryptography==41.0.7
python-socketio[client]==5.10.0
requests==2.31.0
python-dotenv==1.0.0
'''
    
    Path("Dockerfile").write_text(dockerfile_content.strip(), encoding='utf-8')
    Path("docker-compose.yml").write_text(compose_content.strip(), encoding='utf-8')
    Path("requirements.txt").write_text(requirements_content.strip(), encoding='utf-8')
    
    print("✅ Docker配置文件创建完成")

def create_readme():
    """创建README文件"""
    print("\n📝 创建README文件...")
    
    readme_content = '''# 聊天室系统

这是一个基于Flask和WebSocket的实时聊天室系统，支持消息加密、用户权限管理和在线状态跟踪。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并修改配置：

```bash
cp .env.example .env
# 编辑 .env 文件，设置数据库连接等配置
```

### 3. 启动系统

```bash
python start_chatroom.py
```

系统将在 http://localhost:5000 启动。

### 4. 使用Docker启动（推荐）

```bash
docker-compose up -d
```

## 📡 API接口

### HTTP API

- `POST /api/v1/chatroom/create` - 创建聊天室
- `GET /api/v1/chatroom/my-chatrooms` - 获取我的聊天室
- `GET /api/v1/chatroom/{id}` - 获取聊天室详情
- 更多接口请参考 [API文档](API_DOCUMENTATION.md)

### WebSocket API

连接地址: `ws://localhost:5000/chatroom?token={jwt_token}`

主要事件:
- `get_chatrooms` - 获取聊天室列表
- `join_chatroom` - 加入聊天室
- `send_message` - 发送消息
- 详细文档请参考 [WebSocket API文档](WEBSOCKET_API.md)

## 🔒 安全特性

- JWT Token认证
- AES-256-GCM消息加密
- SHA-256消息完整性验证
- 基于角色的权限控制（RBAC）
- 防重放攻击

## 🏗️ 系统架构

```
chatroom/
├── __init__.py              # 主应用集成
├── models/                  # 数据库模型
├── api/                     # HTTP API路由
├── websocket/               # WebSocket处理
└── services/                # 业务服务层
```

## 🧪 测试

运行测试脚本：

```bash
python chatroom/test_chatroom_system.py
```

## 📚 文档

- [集成指南](chatroom/INTEGRATION_GUIDE.md)
- [WebSocket API文档](chatroom/WEBSOCKET_API.md)
- [部署说明](DEPLOYMENT.md)

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License
'''
    
    readme_path = Path("README_CHATROOM.md")
    readme_path.write_text(readme_content.strip(), encoding='utf-8')
    print(f"✅ README文件创建: {readme_path}")

def main():
    """主部署流程"""
    print_banner()
    
    # 检查Python版本
    if not check_python_version():
        return False
    
    # 询问用户是否继续
    print("\n这个脚本将：")
    print("1. 安装必要的Python依赖包")
    print("2. 创建配置文件和启动脚本")
    print("3. 创建Docker配置文件")
    print("4. 创建文档和说明文件")
    
    response = input("\n是否继续? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("部署已取消")
        return False
    
    try:
        # 安装依赖
        if not install_dependencies():
            print("❌ 依赖安装失败，部署终止")
            return False
        
        # 创建配置文件
        config_file = create_config_file()
        
        # 创建启动脚本
        startup_script = create_startup_script()
        
        # 创建环境变量文件
        env_file = create_environment_file()
        
        # 创建Docker文件
        create_docker_files()
        
        # 创建README
        create_readme()
        
        print("\n" + "="*60)
        print("🎉 聊天室系统部署完成！")
        print("="*60)
        
        print("\n📋 创建的文件:")
        print(f"  - 配置文件: {config_file}")
        print(f"  - 启动脚本: {startup_script}")
        print(f"  - 环境变量: {env_file}")
        print("  - Docker配置: Dockerfile, docker-compose.yml")
        print("  - 依赖文件: requirements.txt")
        print("  - 说明文档: README_CHATROOM.md")
        
        print("\n🚀 启动方式:")
        print("  方式1 - 直接启动:")
        print("    python start_chatroom.py")
        print("\n  方式2 - Docker启动:")
        print("    docker-compose up -d")
        
        print("\n⚠️ 注意事项:")
        print("  1. 请编辑 .env 文件配置数据库连接")
        print("  2. 在生产环境中更改默认的密钥")
        print("  3. 确保Redis服务正在运行")
        print("  4. 查看集成指南了解更多配置选项")
        
        print("\n📚 文档位置:")
        print("  - 集成指南: chatroom/INTEGRATION_GUIDE.md")
        print("  - WebSocket API: chatroom/WEBSOCKET_API.md")
        print("  - 测试脚本: chatroom/test_chatroom_system.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 部署过程中出现错误: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
