# WebSocket配置说明文档

## 📋 概述

本文档详细说明了DifyChatBackend系统中WebSocket相关的所有配置项，包括环境变量设置、端口配置、认证配置等。

## ⚙️ 环境变量配置

### WebSocket基础配置

在`.env`文件中设置以下变量：

```properties
# WebSocket服务配置
WEBSOCKET_HOST=127.0.0.1
WEBSOCKET_PORT=6000

# 聊天室功能启用
CHATROOM_ENABLED=true
CHATROOM_MAX_ROOMS=100
CHATROOM_MAX_USERS_PER_ROOM=50
CHATROOM_MESSAGE_RETENTION_DAYS=30

# 加密配置
CHATROOM_ENABLE_ENCRYPTION=true
CHATROOM_ENCRYPTION_ALGORITHM=AES-256-GCM
```

### 安全配置

```properties
# JWT配置（用于WebSocket认证）
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=604800

# 通用安全配置
SECRET_KEY=your-secret-key
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=300
```

### 数据库配置

```properties
# 数据存储配置
DATA_DIR=data
USERS_FILE=data/users.json
AGENTS_FILE=data/agents.json

# 备份配置
BACKUP_ENABLED=true
BACKUP_MAX_FILES=5
BACKUP_ON_SAVE=true
BACKUP_CLEANUP_ON_STARTUP=false
```

### Redis配置（可选）

```properties
# Redis缓存配置
REDIS_ENABLED=false
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# 聊天室专用Redis配置
CHATROOM_REDIS_ENABLED=false
CHATROOM_REDIS_HOST=localhost
CHATROOM_REDIS_PORT=6379
CHATROOM_REDIS_DB=1
CHATROOM_REDIS_PASSWORD=
```

## 🔧 配置类说明

### ChatroomConfig类

```python
@dataclass
class ChatroomConfig:
    """聊天室配置"""
    enabled: bool = False                      # 是否启用聊天室功能
    max_rooms: int = 100                       # 最大聊天室数量
    max_users_per_room: int = 50              # 每个聊天室最大用户数
    message_retention_days: int = 30           # 消息保留天数
    enable_encryption: bool = True             # 是否启用消息加密
    encryption_algorithm: str = 'AES-256-GCM' # 加密算法
    websocket_host: str = '127.0.0.1'         # WebSocket监听主机
    websocket_port: int = 6000                 # WebSocket监听端口
```

### BackupConfig类

```python
@dataclass
class BackupConfig:
    """备份配置"""
    enabled: bool = True                       # 是否启用备份
    max_backup_files: int = 5                 # 最大备份文件数
    backup_on_save: bool = True               # 保存时是否备份
    cleanup_on_startup: bool = False          # 启动时是否清理旧备份
```

## 🚀 快速配置指南

### 1. 开发环境配置

```properties
# .env
FLASK_ENV=development
FLASK_DEBUG=false
FLASK_PORT=5000

# WebSocket配置
WEBSOCKET_HOST=127.0.0.1
WEBSOCKET_PORT=6000

# 聊天室配置
CHATROOM_ENABLED=true
CHATROOM_MAX_ROOMS=10
CHATROOM_MAX_USERS_PER_ROOM=20

# 安全配置（开发用）
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET_KEY=dev-jwt-secret-key
```

### 2. 生产环境配置

```properties
# .env
FLASK_ENV=production
FLASK_DEBUG=false
FLASK_PORT=5000

# WebSocket配置（使用SSL）
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=6000

# 聊天室配置
CHATROOM_ENABLED=true
CHATROOM_MAX_ROOMS=100
CHATROOM_MAX_USERS_PER_ROOM=50
CHATROOM_ENABLE_ENCRYPTION=true

# 安全配置（生产用）
SECRET_KEY=your-super-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# Redis配置（生产推荐）
REDIS_ENABLED=true
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
CHATROOM_REDIS_ENABLED=true
```

## 🔗 连接配置

### WebSocket端点

- **开发环境**: `ws://127.0.0.1:6000/ws/chatroom`
- **生产环境**: `wss://your-domain.com:6000/ws/chatroom`

### 认证参数

WebSocket连接需要通过查询参数传递JWT token：

```
ws://127.0.0.1:6000/ws/chatroom?token=your_jwt_token
```

### 获取JWT Token

通过登录API获取token：

```bash
curl -X POST http://127.0.0.1:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

## 📊 性能调优配置

### 连接限制

```properties
# 连接相关配置
CHATROOM_MAX_ROOMS=100
CHATROOM_MAX_USERS_PER_ROOM=50

# Redis连接池配置
REDIS_MAX_CONNECTIONS=10
CHATROOM_REDIS_MAX_CONNECTIONS=20
```

### 消息处理

```properties
# 消息相关配置
CHATROOM_MESSAGE_RETENTION_DAYS=30
BACKUP_MAX_FILES=5

# 日志配置
LOG_LEVEL=INFO
LOG_MAX_FILE_SIZE=10485760  # 10MB
```

## 🛠️ 配置验证

### 检查配置

使用以下Python代码验证配置：

```python
from config import get_chatroom_config, get_backup_config

# 检查聊天室配置
chatroom_config = get_chatroom_config()
print(f"WebSocket地址: {chatroom_config.websocket_host}:{chatroom_config.websocket_port}")
print(f"聊天室功能: {'启用' if chatroom_config.enabled else '禁用'}")

# 检查备份配置
backup_config = get_backup_config()
print(f"备份功能: {'启用' if backup_config.enabled else '禁用'}")
print(f"最大备份文件数: {backup_config.max_backup_files}")
```

### 测试连接

使用提供的测试工具：

1. 打开 `websocket_test.html`
2. 输入正确的WebSocket地址
3. 通过登录获取JWT token
4. 建立WebSocket连接测试

## 🔒 安全注意事项

### 1. 生产环境安全

- 使用强密码设置 `SECRET_KEY` 和 `JWT_SECRET_KEY`
- 启用HTTPS和WSS（WebSocket Secure）
- 配置防火墙规则限制端口访问
- 定期更新JWT密钥

### 2. 网络安全

```properties
# 生产环境推荐配置
WEBSOCKET_HOST=0.0.0.0  # 监听所有接口
CORS_ORIGINS=https://your-frontend-domain.com  # 限制CORS源
MAX_LOGIN_ATTEMPTS=5    # 限制登录尝试次数
LOCKOUT_DURATION=300    # 锁定时间（秒）
```

### 3. 数据安全

```properties
# 启用消息加密
CHATROOM_ENABLE_ENCRYPTION=true
CHATROOM_ENCRYPTION_ALGORITHM=AES-256-GCM

# 启用数据备份
BACKUP_ENABLED=true
BACKUP_ON_SAVE=true
```

## 📝 配置示例文件

### 完整的.env配置示例

```properties
# 基本Flask配置
FLASK_ENV=development
FLASK_DEBUG=false
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# WebSocket配置
WEBSOCKET_HOST=127.0.0.1
WEBSOCKET_PORT=6000

# 聊天室配置
CHATROOM_ENABLED=true
CHATROOM_MAX_ROOMS=100
CHATROOM_MAX_USERS_PER_ROOM=50
CHATROOM_MESSAGE_RETENTION_DAYS=30
CHATROOM_ENABLE_ENCRYPTION=true
CHATROOM_ENCRYPTION_ALGORITHM=AES-256-GCM

# 安全配置
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=604800
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=300

# 数据库配置
DATA_DIR=data
USERS_FILE=data/users.json
AGENTS_FILE=data/agents.json

# 备份配置
BACKUP_ENABLED=true
BACKUP_MAX_FILES=5
BACKUP_ON_SAVE=true
BACKUP_CLEANUP_ON_STARTUP=false

# Dify API配置
DIFY_BASE_URL=http://your-dify-server/v1
DIFY_API_KEY=your-dify-api-key
DIFY_TIMEOUT=30
DIFY_MAX_RETRIES=3

# 日志配置
LOG_LEVEL=INFO
LOG_ENABLE_CONSOLE=true
LOG_ENABLE_FILE=true
LOG_MAX_FILE_SIZE=10485760
LOG_BACKUP_COUNT=5

# Redis配置（可选）
REDIS_ENABLED=false
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# 聊天室Redis配置（可选）
CHATROOM_REDIS_ENABLED=false
CHATROOM_REDIS_HOST=localhost
CHATROOM_REDIS_PORT=6379
CHATROOM_REDIS_DB=1
CHATROOM_REDIS_PASSWORD=

# CORS配置
CORS_ENABLED=true
CORS_ORIGINS=*
```

## 🆘 常见问题

### Q: WebSocket连接失败
A: 检查以下项目：
- WebSocket端口（6000）是否正确
- JWT token是否有效
- 防火墙是否阻止连接
- 后端服务是否正常运行

### Q: 消息无法发送
A: 检查以下项目：
- 是否已成功连接到WebSocket
- 用户是否有发送权限
- 聊天室ID是否正确
- 消息格式是否符合要求

### Q: 备份文件过多
A: 调整以下配置：
```properties
BACKUP_MAX_FILES=3          # 减少备份文件数量
BACKUP_CLEANUP_ON_STARTUP=true  # 启动时清理旧备份
```

---

**文档版本**: v1.0  
**最后更新**: 2025-07-26  
**适用版本**: DifyChatBackend v2.0+
