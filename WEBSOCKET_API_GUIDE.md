# WebSocket API 连接指南

## 概述

DifyChatBackend 提供原生 WebSocket 支持，用于实时聊天功能。WebSocket 服务器基于 `websockets 15.0.1` 库实现，支持 JWT 认证和完整的聊天室功能。

## 连接信息

- **WebSocket 端点**: `ws://localhost:6000/ws/chatroom`
- **认证方式**: JWT Token (通过URL参数或消息认证)
- **协议版本**: WebSocket 13
- **支持压缩**: permessage-deflate

## 连接方式

### 方式1: URL参数认证（推荐）

```javascript
const token = "your_jwt_token_here";
const websocket = new WebSocket(`ws://localhost:6000/ws/chatroom?token=${token}`);
```

### 方式2: 消息认证

```javascript
const websocket = new WebSocket("ws://localhost:6000/ws/chatroom");

websocket.onopen = function() {
    // 发送认证消息
    websocket.send(JSON.stringify({
        type: "auth",
        token: "your_jwt_token_here"
    }));
};
```

## JWT Token 获取

通过 HTTP API 登录获取 JWT Token：

```javascript
const response = await fetch('http://localhost:5000/api/v1/auth/login', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        username: 'your_username',
        password: 'your_password'
    })
});

const data = await response.json();
const token = data.data.tokens.access_token;
```

## 连接生命周期

### 1. 连接建立

成功连接后，服务器会发送连接确认消息：

```json
{
    "type": "connected",
    "data": {
        "connection_id": "uuid-string",
        "user_id": "username",
        "username": "display_name",
        "server_time": "2025-07-26T15:07:55.136538Z"
    },
    "status": "success",
    "message": "连接成功"
}
```

### 2. 心跳检测

- **Ping间隔**: 30秒
- **Ping超时**: 10秒
- 客户端无需手动处理，浏览器自动管理

### 3. 连接关闭

常见关闭代码：
- `1000`: 正常关闭
- `1006`: 异常关闭（网络问题）
- `1008`: 认证失败
- `1011`: 服务器错误

## API 消息格式

### 请求消息格式

```json
{
    "type": "message_type",
    "data": {
        // 消息特定数据
    }
}
```

### 响应消息格式

```json
{
    "type": "response_type",
    "data": {
        // 响应数据
    },
    "status": "success|error",
    "message": "描述信息"
}
```

## 支持的消息类型

### 1. 获取聊天室列表

**请求**:
```json
{
    "type": "get_chatrooms"
}
```

**响应**:
```json
{
    "type": "chatrooms_list",
    "data": [
        {
            "id": "general",
            "name": "综合讨论",
            "description": "全员可见的综合讨论区",
            "member_count": 5,
            "is_public": true
        }
    ],
    "status": "success",
    "message": "聊天室列表获取成功"
}
```

### 2. 加入聊天室

**请求**:
```json
{
    "type": "join_chatroom",
    "chatroom_id": "general"
}
```

**响应**:
```json
{
    "type": "join_result",
    "data": {
        "chatroom_id": "general",
        "chatroom_name": "综合讨论"
    },
    "status": "success",
    "message": "加入聊天室成功"
}
```

### 3. 离开聊天室

**请求**:
```json
{
    "type": "leave_chatroom",
    "chatroom_id": "general"
}
```

**响应**:
```json
{
    "type": "leave_result",
    "data": {
        "chatroom_id": "general"
    },
    "status": "success",
    "message": "离开聊天室成功"
}
```

### 4. 发送消息

**请求**:
```json
{
    "type": "send_message",
    "chatroom_id": "general",
    "message": "Hello, world!",
    "message_type": "text"
}
```

**响应**:
```json
{
    "type": "message_sent",
    "data": {
        "message_id": "uuid-string",
        "chatroom_id": "general",
        "timestamp": "2025-07-26T15:10:00Z"
    },
    "status": "success",
    "message": "消息发送成功"
}
```

### 5. 获取历史消息

**请求**:
```json
{
    "type": "get_messages",
    "chatroom_id": "general",
    "limit": 20,
    "offset": 0
}
```

**响应**:
```json
{
    "type": "messages_list",
    "data": {
        "messages": [
            {
                "id": "uuid-string",
                "user_id": "username",
                "username": "display_name",
                "message": "Hello, world!",
                "message_type": "text",
                "timestamp": "2025-07-26T15:10:00Z"
            }
        ],
        "total": 100,
        "limit": 20,
        "offset": 0
    },
    "status": "success",
    "message": "历史消息获取成功"
}
```

## 实时消息推送

当其他用户发送消息时，所有在线用户会收到：

```json
{
    "type": "new_message",
    "data": {
        "message_id": "uuid-string",
        "chatroom_id": "general",
        "user_id": "username",
        "username": "display_name",
        "message": "Hello, everyone!",
        "message_type": "text",
        "timestamp": "2025-07-26T15:12:00Z"
    }
}
```

## JavaScript 客户端示例

```javascript
class ChatroomWebSocket {
    constructor(token) {
        this.token = token;
        this.websocket = null;
        this.isConnected = false;
    }

    connect() {
        const wsUrl = `ws://localhost:6000/ws/chatroom?token=${this.token}`;
        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = (event) => {
            console.log('WebSocket 连接成功');
            this.isConnected = true;
        };

        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.websocket.onclose = (event) => {
            console.log(`WebSocket 连接关闭: ${event.code}`);
            this.isConnected = false;
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket 错误:', error);
        };
    }

    handleMessage(data) {
        switch(data.type) {
            case 'connected':
                console.log('连接确认:', data.data);
                break;
            case 'chatrooms_list':
                console.log('聊天室列表:', data.data);
                break;
            case 'new_message':
                console.log('新消息:', data.data);
                break;
            default:
                console.log('未知消息类型:', data);
        }
    }

    sendMessage(type, data = {}) {
        if (!this.isConnected) {
            console.error('WebSocket 未连接');
            return;
        }

        const message = JSON.stringify({
            type: type,
            ...data
        });

        this.websocket.send(message);
    }

    getChatrooms() {
        this.sendMessage('get_chatrooms');
    }

    joinChatroom(chatroomId) {
        this.sendMessage('join_chatroom', { chatroom_id: chatroomId });
    }

    sendChatMessage(chatroomId, message, messageType = 'text') {
        this.sendMessage('send_message', {
            chatroom_id: chatroomId,
            message: message,
            message_type: messageType
        });
    }

    disconnect() {
        if (this.websocket) {
            this.websocket.close(1000, 'Client disconnect');
        }
    }
}

// 使用示例
async function initializeChatroom() {
    // 1. 获取 JWT Token
    const response = await fetch('http://localhost:5000/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username: 'your_username',
            password: 'your_password'
        })
    });

    const loginData = await response.json();
    const token = loginData.data.tokens.access_token;

    // 2. 建立 WebSocket 连接
    const chatroom = new ChatroomWebSocket(token);
    chatroom.connect();

    // 3. 等待连接建立后使用
    setTimeout(() => {
        chatroom.getChatrooms();
        chatroom.joinChatroom('general');
        chatroom.sendChatMessage('general', 'Hello, world!');
    }, 1000);
}
```

## 错误处理

### 常见错误

1. **认证失败** (1008)
   - JWT Token 无效或过期
   - 解决: 重新登录获取新 Token

2. **异常关闭** (1006)
   - 网络连接问题
   - 服务器重启
   - 解决: 实现重连机制

3. **协议错误** (1002)
   - 消息格式不正确
   - 解决: 检查 JSON 格式

### 重连机制示例

```javascript
class ReconnectingWebSocket extends ChatroomWebSocket {
    constructor(token, maxRetries = 5) {
        super(token);
        this.maxRetries = maxRetries;
        this.retryCount = 0;
        this.retryTimeout = null;
    }

    connect() {
        super.connect();

        this.websocket.onclose = (event) => {
            console.log(`WebSocket 连接关闭: ${event.code}`);
            this.isConnected = false;

            if (event.code !== 1000 && this.retryCount < this.maxRetries) {
                this.scheduleReconnect();
            }
        };
    }

    scheduleReconnect() {
        this.retryCount++;
        const delay = Math.pow(2, this.retryCount) * 1000; // 指数退避

        console.log(`${delay/1000}秒后尝试重连 (${this.retryCount}/${this.maxRetries})`);

        this.retryTimeout = setTimeout(() => {
            this.connect();
        }, delay);
    }

    disconnect() {
        if (this.retryTimeout) {
            clearTimeout(this.retryTimeout);
        }
        super.disconnect();
    }
}
```

## 技术规格

- **WebSocket 库**: websockets 15.0.1
- **认证**: JWT (HS256)
- **消息格式**: JSON
- **编码**: UTF-8
- **压缩**: 支持 permessage-deflate
- **最大消息大小**: 无限制
- **连接超时**: 10秒
- **心跳间隔**: 30秒

## 部署注意事项

### 开发环境
- WebSocket 服务器: `ws://localhost:6000/ws/chatroom`
- HTTP API 服务器: `http://localhost:5000`

### 生产环境
- 使用 WSS (WebSocket Secure) 协议
- 配置反向代理 (Nginx/Apache)
- 设置适当的防火墙规则

### 环境变量配置

```env
# WebSocket 配置
WEBSOCKET_HOST=127.0.0.1
WEBSOCKET_PORT=6000

# JWT 配置
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_TOKEN_EXPIRES=3600
```

## 故障排除

### 1. 连接被拒绝
- 检查 WebSocket 服务器是否运行
- 验证端口 6000 是否开放
- 确认防火墙设置

### 2. 认证失败
- 验证 JWT Token 格式
- 检查 Token 是否过期
- 确认 JWT 密钥配置

### 3. 浏览器兼容性
- 现代浏览器均支持 WebSocket
- VS Code Simple Browser 可能有限制
- 建议使用系统默认浏览器测试

### 4. 网络问题
- 检查本地网络连接
- 验证代理设置
- 测试 TCP 连接: `Test-NetConnection localhost -Port 6000`

---

**最后更新**: 2025-07-26
**版本**: 2.1.2
**维护者**: DifyChatBackend Team
