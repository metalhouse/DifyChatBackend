# 聊天室系统集成指南

## 📋 概述

本指南说明如何将聊天室系统集成到现有的DifyChatBackend项目中。

## 🔧 安装依赖

首先，需要安装额外的依赖包：

```bash
# 安装WebSocket支持
pip install flask-socketio

# 安装数据库支持（如果尚未安装）
pip install sqlalchemy

# 安装Redis支持（用于在线用户管理）
pip install redis
```

## 🏗️ 项目结构

聊天室系统已创建在以下目录结构中：

```
chatroom/
├── __init__.py              # 主应用集成文件
├── models/                  # 数据库模型
│   ├── __init__.py
│   └── chatroom_models.py
├── api/                     # HTTP API路由
│   └── routes.py
├── websocket/               # WebSocket处理
│   ├── connection_manager.py
│   └── handlers.py
└── services/                # 业务服务
    ├── permissions.py       # 权限管理
    ├── message_crypto.py    # 消息加密
    ├── online_user_manager.py # 在线用户管理
    └── database_service.py  # 数据库服务
```

## 🚀 集成到主应用

### 1. 修改主应用文件 (app.py)

```python
from flask import Flask
from flask_socketio import SocketIO
from chatroom import init_chatroom_system

app = Flask(__name__)
app.config.from_object('config.Config')

# 初始化SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# 初始化聊天室系统
init_chatroom_system(
    app=app, 
    socketio=socketio,
    db_session=get_db_session()  # 你的数据库会话获取函数
)

if __name__ == '__main__':
    socketio.run(app, debug=True)
```

### 2. 更新配置文件 (config.py)

```python
class Config:
    # 现有配置...
    
    # 聊天室相关配置
    CHATROOM_MAX_USERS_DEFAULT = 100
    CHATROOM_MESSAGE_MAX_LENGTH = 4000
    CHATROOM_HISTORY_LIMIT = 50
    
    # WebSocket配置
    SOCKETIO_ASYNC_MODE = 'threading'  # 或 'eventlet', 'gevent'
    SOCKETIO_PING_TIMEOUT = 60
    SOCKETIO_PING_INTERVAL = 25
```

### 3. 更新用户权限系统

在你的用户模型或认证系统中，为用户添加聊天室相关权限：

```python
# 在用户权限中添加以下角色
CHATROOM_ROLES = {
    "admin": ["chatroom_admin", "chatroom_access", "user_management"],
    "chatroom_manager": ["chatroom_create", "chatroom_manage", "chatroom_access"],
    "chatroom_user": ["chatroom_access"],
    "regular_user": []
}
```

## 🗄️ 数据库初始化

### 1. 创建数据库表

系统启动时会自动创建以下表：
- `chatrooms` - 聊天室信息
- `chatroom_members` - 聊天室成员
- `chatroom_messages` - 聊天消息
- `chatroom_online_users` - 在线用户状态

### 2. 手动创建表（如果需要）

```sql
-- 参考 chatroom/models/chatroom_models.py 中的表结构
-- 或运行以下Python代码

from chatroom.models import Base
from sqlalchemy import create_engine

engine = create_engine('your_database_url')
Base.metadata.create_all(engine)
```

## 🔌 API端点

### HTTP API

所有API都在 `/api/v1/chatroom` 路径下：

#### 管理员API (需要 `chatroom_admin` 权限)
- `POST /api/v1/chatroom/create` - 创建聊天室
- `GET /api/v1/chatroom/admin/list` - 获取所有聊天室
- `PUT /api/v1/chatroom/{id}` - 更新聊天室
- `DELETE /api/v1/chatroom/{id}` - 删除聊天室
- `POST /api/v1/chatroom/{id}/members` - 添加成员
- `DELETE /api/v1/chatroom/{id}/members/{user_id}` - 移除成员

#### 用户API (需要 `chatroom_access` 权限)
- `GET /api/v1/chatroom/my-chatrooms` - 获取我的聊天室
- `GET /api/v1/chatroom/{id}` - 获取聊天室详情
- `GET /api/v1/chatroom/{id}/messages` - 获取消息历史
- `GET /api/v1/chatroom/{id}/members` - 获取成员列表

### WebSocket API

连接端点：`ws://localhost:5000/chatroom?token={jwt_token}`

#### 客户端发送事件
- `get_chatrooms` - 获取聊天室列表
- `join_chatroom` - 加入聊天室
- `leave_chatroom` - 离开聊天室
- `send_message` - 发送消息
- `get_history` - 获取历史消息

#### 服务端推送事件
- `connected` - 连接成功
- `chatroom_list` - 聊天室列表
- `chatroom_joined` - 加入聊天室成功
- `message` - 新消息
- `user_joined` - 用户加入
- `user_left` - 用户离开
- `error` - 错误消息

## 🔒 消息加密

系统支持AES256-GCM端到端加密：

### 前端加密示例 (JavaScript)

```javascript
// 使用CryptoJS库
const message = "Hello, World!";
const key = CryptoJS.lib.WordArray.random(256/8); // 256位密钥
const iv = CryptoJS.lib.WordArray.random(96/8);   // 96位IV

// 加密
const encrypted = CryptoJS.AES.encrypt(message, key, {
    iv: iv,
    mode: CryptoJS.mode.GCM
});

// 发送加密消息
socket.emit('send_message', {
    chatroom_id: 'room-id',
    message: message,  // 原文（用于完整性校验）
    encrypted: true,
    encryption_data: {
        iv: iv.toString(),
        ciphertext: encrypted.ciphertext.toString(),
        tag: encrypted.tag.toString()
    },
    message_hash: calculateSHA256Hash(message, timestamp, userId),
    timestamp: new Date().toISOString()
});
```

## 🧪 测试

### 1. 基本功能测试

```python
import requests

# 测试创建聊天室
response = requests.post('http://localhost:5000/api/v1/chatroom/create', 
    headers={'Authorization': 'Bearer your_jwt_token'},
    json={
        'name': '测试聊天室',
        'description': '这是一个测试聊天室',
        'is_public': True
    }
)

print(response.json())
```

### 2. WebSocket测试

```javascript
// 前端测试代码
const socket = io('/chatroom', {
    auth: {
        token: 'your_jwt_token'
    }
});

socket.on('connected', (data) => {
    console.log('连接成功:', data);
    
    // 获取聊天室列表
    socket.emit('get_chatrooms');
});

socket.on('chatroom_list', (data) => {
    console.log('聊天室列表:', data);
});
```

## 📊 监控和日志

### 日志配置

```python
import logging

# 配置聊天室日志
chatroom_logger = logging.getLogger('chatroom')
chatroom_logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
chatroom_logger.addHandler(handler)
```

### 性能监控

系统提供以下监控端点：
- `GET /api/v1/chatroom/stats` - 聊天室统计信息

## 🔧 配置调优

### Redis优化

```python
# 在线用户管理器配置
REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'db': 1,  # 使用专门的数据库
    'decode_responses': True,
    'max_connections': 20
}
```

### WebSocket优化

```python
# SocketIO配置
SOCKETIO_CONFIG = {
    'async_mode': 'threading',
    'ping_timeout': 60,
    'ping_interval': 25,
    'max_http_buffer_size': 1000000
}
```

## 🚨 安全考虑

1. **认证验证**: 确保所有WebSocket连接都进行JWT验证
2. **权限检查**: 每个操作都验证用户权限
3. **消息过滤**: 对输入消息进行XSS过滤
4. **频率限制**: 实现消息发送频率限制
5. **加密存储**: 敏感消息使用加密存储

## 🐛 故障排除

### 常见问题

1. **WebSocket连接失败**
   - 检查JWT token是否有效
   - 确认用户有聊天室访问权限
   - 查看服务器日志中的错误信息

2. **消息加密失败**
   - 验证加密数据格式是否正确
   - 检查IV和Tag长度
   - 确认时间戳格式正确

3. **权限问题**
   - 确认用户角色配置正确
   - 检查权限装饰器是否正常工作

### 调试模式

```python
# 启用详细日志
import logging
logging.getLogger('chatroom').setLevel(logging.DEBUG)

# WebSocket调试
socketio = SocketIO(app, logger=True, engineio_logger=True)
```

## 📚 API文档

详细的API文档请参考：
- [HTTP API文档](API_DOCUMENTATION.md)
- [WebSocket API文档](WEBSOCKET_API.md)
- [错误码参考](ERROR_CODES.md)

---

如有问题或需要帮助，请查看日志文件或联系开发团队。
