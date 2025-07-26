# 聊天室系统

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