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