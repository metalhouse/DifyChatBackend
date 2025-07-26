# DifyChatBackend 项目架构说明

## 📋 概述

DifyChatBackend项目采用**双服务架构**，分别提供HTTP REST API和WebSocket实时通信功能。

## 🏗️ 服务架构

### 1. 主API服务 (HTTP REST API)
- **端口**: `5000`
- **入口文件**: `app.py`
- **功能**: 提供标准的REST API接口
- **协议**: HTTP/HTTPS

#### 主要功能
- 用户认证与授权
- 智能体管理
- 对话管理
- 缓存管理
- 系统统计

#### API端点前缀
- **新版本** (推荐): `/api/v1/`
- **兼容版本**: `/api/`

### 2. WebSocket服务 (实时聊天室)
- **端口**: `6000`
- **入口文件**: 集成在主应用中，由 `chatroom/websocket/` 模块提供
- **功能**: 实时聊天室功能
- **协议**: WebSocket/WSS

#### 主要功能
- 实时消息传输
- 多聊天室管理
- 在线用户状态
- 消息加密

## 🔗 服务连接配置

### HTTP API服务
```javascript
// API基础URL
const API_BASE_URL = 'http://127.0.0.1:5000';

// 主要端点
const ENDPOINTS = {
    login: `${API_BASE_URL}/api/v1/auth/login`,
    agents: `${API_BASE_URL}/api/v1/chat/agents`,
    conversations: `${API_BASE_URL}/api/v1/conversations`,
    chat: `${API_BASE_URL}/api/v1/chat`
};
```

### WebSocket服务
```javascript
// WebSocket连接URL
const WEBSOCKET_URL = 'ws://127.0.0.1:6000/ws/chatroom';

// 需要从HTTP API获取JWT token
const token = 'your_jwt_token_from_api_login';
const socket = new WebSocket(`${WEBSOCKET_URL}?token=${token}`);
```

## 🔐 认证流程

### 1. 获取JWT Token
通过HTTP API登录获取token：

```javascript
async function login(username, password) {
    const response = await fetch('http://127.0.0.1:5000/api/v1/auth/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: username,
            password: password
        })
    });
    
    const data = await response.json();
    if (data.success) {
        return data.data.tokens.access_token;
    } else {
        throw new Error(data.message);
    }
}
```

### 2. 使用Token访问服务

#### HTTP API使用
```javascript
const response = await fetch('/api/v1/chat/agents', {
    headers: {
        'Authorization': `Bearer ${token}`
    }
});
```

#### WebSocket使用
```javascript
const socket = new WebSocket(`ws://127.0.0.1:6000/ws/chatroom?token=${token}`);
```

## 📡 数据格式标准

### HTTP API响应格式
```json
{
  "success": true,
  "message": "操作成功的描述",
  "data": {
    // 响应数据
  },
  "request_id": "uuid",
  "timestamp": 1642147200
}
```

### WebSocket消息格式
```json
{
  "type": "event_name",
  "data": {
    // 事件数据
  },
  "status": "success",
  "message": "操作描述"
}
```

## 🔧 配置文件

### 主配置 (.env)
```properties
# HTTP API服务
FLASK_PORT=5000
FLASK_HOST=0.0.0.0

# WebSocket服务
WEBSOCKET_HOST=127.0.0.1
WEBSOCKET_PORT=6000

# 聊天室功能
CHATROOM_ENABLED=true

# 认证配置
JWT_SECRET_KEY=your-jwt-secret
```

## 🚀 启动方式

### 开发环境
```bash
# 启动主应用（包含HTTP API和WebSocket服务）
python app.py

# 服务状态检查
# HTTP API: http://127.0.0.1:5000/health
# WebSocket: ws://127.0.0.1:6000/ws/chatroom
```

### 生产环境
建议使用 Docker 或 systemd 服务管理。

## 📊 端口分配

| 服务 | 端口 | 协议 | 用途 |
|------|------|------|------|
| HTTP API | 5000 | HTTP/HTTPS | REST API接口 |
| WebSocket | 6000 | WebSocket/WSS | 实时聊天室 |
| Admin Panel | 5000 | HTTP | 管理后台 (集成在主服务中) |

## 🔍 服务发现

### 检查服务状态
```javascript
// 检查HTTP API状态
const apiHealth = await fetch('http://127.0.0.1:5000/health');

// 检查WebSocket连接
const socket = new WebSocket('ws://127.0.0.1:6000/ws/chatroom?token=test');
socket.onopen = () => console.log('WebSocket服务可用');
socket.onerror = () => console.log('WebSocket服务不可用');
```

## 🛠️ 开发指南

### 前端开发者
1. **HTTP API**: 参考 `API_DOCUMENTATION.md`
2. **WebSocket**: 参考 `WEBSOCKET_FRONTEND_GUIDE.md`
3. **测试工具**: 使用 `websocket_test.html`

### API路由版本
- **推荐使用**: `/api/v1/auth/login` (标准化响应格式)
- **兼容支持**: `/api/login` (旧版格式)

## 🔒 安全注意事项

### 跨域配置
HTTP API支持CORS，WebSocket需要通过token认证。

### Token有效期
- Access Token: 1小时
- Refresh Token: 7天
- 支持自动刷新机制

### 生产部署
1. 使用HTTPS/WSS协议
2. 配置防火墙规则
3. 使用强密码和密钥
4. 启用Redis缓存

## 📞 技术支持

如有问题，请检查：
1. 服务是否正常启动
2. 端口是否被占用
3. 防火墙设置
4. 配置文件是否正确

---

**架构版本**: v2.1  
**最后更新**: 2025-07-26  
**维护团队**: 后端开发团队
