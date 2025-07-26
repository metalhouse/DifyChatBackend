# WebSocket 前端开发指南

## 📋 概述

本文档为前端开发者提供DifyChatBackend系统WebSocket连接的完整使用指南。系统支持实时聊天室功能，包含消息加密、在线状态管理等特性。

## 🔗 连接配置

### 基本连接信息

```javascript
// WebSocket连接地址
const WEBSOCKET_HOST = '127.0.0.1';
const WEBSOCKET_PORT = 6000;
const WEBSOCKET_URL = `ws://${WEBSOCKET_HOST}:${WEBSOCKET_PORT}/ws/chatroom`;

// 生产环境建议使用wss://
const WEBSOCKET_URL_PROD = `wss://your-domain.com:${WEBSOCKET_PORT}/ws/chatroom`;
```

### 认证配置

WebSocket连接需要JWT token进行认证：

```javascript
// 获取token（通过登录API获得）
const token = localStorage.getItem('auth_token'); // 或从你的状态管理中获取

// 连接WebSocket
const socket = new WebSocket(`${WEBSOCKET_URL}?token=${token}`);
```

## 🚀 快速开始

### 基本连接示例

```javascript
class ChatWebSocket {
    constructor(token) {
        this.token = token;
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    connect() {
        try {
            this.socket = new WebSocket(`${WEBSOCKET_URL}?token=${this.token}`);
            this.setupEventHandlers();
        } catch (error) {
            console.error('WebSocket连接失败:', error);
        }
    }

    setupEventHandlers() {
        this.socket.onopen = (event) => {
            console.log('WebSocket连接已建立');
            this.isConnected = true;
            this.reconnectAttempts = 0;
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('消息解析失败:', error);
            }
        };

        this.socket.onclose = (event) => {
            console.log('WebSocket连接已关闭:', event.code, event.reason);
            this.isConnected = false;
            this.handleReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket错误:', error);
        };
    }

    handleMessage(data) {
        switch (data.type) {
            case 'connected':
                console.log('连接成功确认:', data);
                break;
            case 'chatroom_list':
                this.handleChatroomList(data.data);
                break;
            case 'message':
                this.handleNewMessage(data.data);
                break;
            case 'user_joined':
                this.handleUserJoined(data.data);
                break;
            case 'user_left':
                this.handleUserLeft(data.data);
                break;
            case 'error':
                console.error('服务器错误:', data.message);
                break;
            default:
                console.log('未知事件:', data);
        }
    }

    // 发送消息到服务器
    send(type, data = {}) {
        if (this.isConnected && this.socket.readyState === WebSocket.OPEN) {
            const message = JSON.stringify({ type, ...data });
            this.socket.send(message);
        } else {
            console.error('WebSocket未连接，无法发送消息');
        }
    }

    // 断线重连机制
    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`尝试重连... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.connect();
            }, Math.pow(2, this.reconnectAttempts) * 1000); // 指数退避
        } else {
            console.error('重连失败，已达到最大重试次数');
        }
    }

    // 关闭连接
    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}
```

## 📡 API事件参考

### 发送事件（客户端 → 服务器）

#### 1. 获取聊天室列表
```javascript
websocket.send(JSON.stringify({
    type: 'get_chatrooms'
}));
```

#### 2. 加入聊天室
```javascript
websocket.send(JSON.stringify({
    type: 'join_chatroom',
    chatroom_id: 'your-chatroom-id'
}));
```

#### 3. 离开聊天室
```javascript
websocket.send(JSON.stringify({
    type: 'leave_chatroom',
    chatroom_id: 'your-chatroom-id'
}));
```

#### 4. 发送消息
```javascript
websocket.send(JSON.stringify({
    type: 'send_message',
    chatroom_id: 'your-chatroom-id',
    message: '你好，世界！',
    message_type: 'text' // 可选: text, image, file
}));
```

#### 5. 获取历史消息
```javascript
websocket.send(JSON.stringify({
    type: 'get_messages',
    chatroom_id: 'your-chatroom-id',
    limit: 50,        // 可选，默认20
    offset: 0         // 可选，用于分页
}));
```

### 接收事件（服务器 → 客户端）

#### 1. 连接确认
```javascript
{
    "type": "connected",
    "data": {
        "connection_id": "uuid",
        "user_id": "user123",
        "username": "用户名",
        "server_time": "2025-07-26T10:30:00Z"
    },
    "status": "success",
    "message": "连接成功"
}
```

#### 2. 聊天室列表
```javascript
{
    "type": "chatroom_list",
    "data": {
        "chatrooms": [
            {
                "id": "general",
                "name": "综合讨论",
                "description": "全员可见的综合讨论区",
                "member_count": 15,
                "is_public": true
            }
        ]
    },
    "status": "success"
}
```

#### 3. 新消息
```javascript
{
    "event": "message",
    "data": {
        "id": "message-uuid",
        "chatroom_id": "chatroom-uuid",
        "user_id": "user123",
        "username": "张三",
        "message": "大家好！",
        "message_type": "text",
        "timestamp": "2025-07-26T10:30:00Z",
        "encrypted": false
    }
}
```

#### 4. 用户加入/离开
```javascript
// 用户加入
{
    "event": "user_joined",
    "data": {
        "user_id": "user456",
        "username": "李四",
        "chatroom_id": "chatroom-uuid",
        "timestamp": "2025-07-26T10:30:00Z"
    }
}

// 用户离开
{
    "event": "user_left", 
    "data": {
        "user_id": "user456",
        "username": "李四",
        "chatroom_id": "chatroom-uuid",
        "timestamp": "2025-07-26T10:30:00Z"
    }
}
```

#### 5. 错误消息
```javascript
{
    "event": "error",
    "data": {
        "code": "PERMISSION_DENIED",
        "message": "您没有权限访问此聊天室",
        "timestamp": "2025-07-26T10:30:00Z"
    }
}
```

## 🔐 安全与加密

### JWT Token获取

首先通过登录API获取token：

```javascript
// 登录获取token
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
        // 注意：根据API文档，token在tokens.access_token中
        localStorage.setItem('auth_token', data.data.tokens.access_token);
        return data.data.tokens.access_token;
    } else {
        throw new Error(data.message);
    }
}
```

### 消息加密（可选）

系统支持AES-256-GCM消息加密：

```javascript
// 加密配置
const ENCRYPTION_CONFIG = {
    algorithm: 'AES-256-GCM',
    keySize: 256,
    ivSize: 96
};

// 发送加密消息
websocket.send('send_message', {
    chatroom_id: 'your-chatroom-id',
    message: 'encrypted_message_content',
    encrypted: true,
    encryption_method: 'AES-256-GCM'
});
```

## 🛠️ 完整示例

```javascript
class ChatApp {
    constructor() {
        this.websocket = null;
        this.currentChatroom = null;
        this.messages = [];
        this.chatrooms = [];
    }

    async init() {
        // 获取token
        const token = localStorage.getItem('auth_token');
        if (!token) {
            throw new Error('未找到认证token，请先登录');
        }

        // 建立WebSocket连接
        this.websocket = new ChatWebSocket(token);
        this.setupWebSocketHandlers();
        this.websocket.connect();
    }

    setupWebSocketHandlers() {
        // 重写消息处理方法
        this.websocket.handleChatroomList = (data) => {
            this.chatrooms = data.chatrooms;
            this.renderChatroomList();
        };

        this.websocket.handleNewMessage = (data) => {
            if (data.chatroom_id === this.currentChatroom) {
                this.messages.push(data);
                this.renderMessages();
            }
        };

        this.websocket.handleUserJoined = (data) => {
            if (data.chatroom_id === this.currentChatroom) {
                this.showNotification(`${data.username} 加入了聊天室`);
            }
        };

        this.websocket.handleUserLeft = (data) => {
            if (data.chatroom_id === this.currentChatroom) {
                this.showNotification(`${data.username} 离开了聊天室`);
            }
        };
    }

    // 加入聊天室
    joinChatroom(chatroomId) {
        if (this.currentChatroom) {
            this.websocket.send('leave_chatroom', {
                chatroom_id: this.currentChatroom
            });
        }

        this.currentChatroom = chatroomId;
        this.websocket.send('join_chatroom', {
            chatroom_id: chatroomId
        });

        // 获取历史消息
        this.websocket.send('get_messages', {
            chatroom_id: chatroomId,
            limit: 50
        });
    }

    // 发送消息
    sendMessage(message) {
        if (!this.currentChatroom) {
            console.error('未选择聊天室');
            return;
        }

        this.websocket.send('send_message', {
            chatroom_id: this.currentChatroom,
            message: message,
            message_type: 'text'
        });
    }

    // UI渲染方法（示例）
    renderChatroomList() {
        const container = document.getElementById('chatroom-list');
        container.innerHTML = this.chatrooms.map(room => `
            <div class="chatroom-item" onclick="app.joinChatroom('${room.id}')">
                <h3>${room.name}</h3>
                <p>${room.description}</p>
                <span class="member-count">${room.member_count} 成员</span>
            </div>
        `).join('');
    }

    renderMessages() {
        const container = document.getElementById('messages');
        container.innerHTML = this.messages.map(msg => `
            <div class="message">
                <span class="username">${msg.username}:</span>
                <span class="content">${msg.message}</span>
                <span class="timestamp">${new Date(msg.timestamp).toLocaleTimeString()}</span>
            </div>
        `).join('');
        container.scrollTop = container.scrollHeight;
    }

    showNotification(message) {
        // 显示通知
        console.log('通知:', message);
    }
}

// 使用示例
const app = new ChatApp();
app.init().catch(console.error);
```

## 🐛 错误处理

### 常见错误代码

| 错误代码 | 说明 | 解决方案 |
|---------|------|----------|
| `INVALID_TOKEN` | JWT token无效或过期 | 重新登录获取新token |
| `PERMISSION_DENIED` | 权限不足 | 检查用户权限设置 |
| `CHATROOM_NOT_FOUND` | 聊天室不存在 | 检查聊天室ID是否正确 |
| `MESSAGE_TOO_LONG` | 消息过长 | 限制消息长度（建议<1000字符） |
| `RATE_LIMIT_EXCEEDED` | 发送频率过高 | 降低消息发送频率 |

### 连接问题排查

1. **连接失败**
   - 检查WebSocket地址和端口（127.0.0.1:6000）
   - 确认后端服务已启动
   - 检查防火墙设置
   - **注意**: 6000端口只支持WebSocket协议，不能用HTTP请求测试

2. **认证失败**
   - 验证JWT token是否有效
   - 检查token格式是否正确
   - 确认token未过期

3. **消息丢失**
   - 检查网络连接稳定性
   - 实现消息确认机制
   - 添加重发机制

### WebSocket服务测试方法

**❌ 错误的测试方式**:
```bash
# 这样测试会失败，因为6000端口只支持WebSocket
curl http://127.0.0.1:6000
# 结果: 426 Upgrade Required
```

**✅ 正确的测试方式**:

#### 方法1: 使用浏览器控制台
```javascript
// 在浏览器控制台中执行
const socket = new WebSocket('ws://127.0.0.1:6000/ws/chatroom?token=your_token');
socket.onopen = () => console.log('WebSocket连接成功');
socket.onclose = (e) => console.log('连接关闭:', e.code, e.reason);
socket.onerror = (e) => console.log('连接错误:', e);
```

#### 方法2: 使用测试工具

项目提供了专业的WebSocket测试工具：

**websocket_diagnostic.html (推荐)**
- 位置：项目根目录
- 功能：全面的WebSocket服务诊断工具
- 特性：
  - 自动检查HTTP API和WebSocket服务状态
  - 提供详细的连接步骤指导
  - 实时连接日志和状态显示
  - 集成登录功能快速获取token
  - 错误诊断和解决建议

**websocket_test.html**
- 位置：项目根目录
- 功能：基础WebSocket连接测试

#### 方法3: 使用专业工具
- **WebSocket King**: Chrome扩展
- **wscat**: 命令行工具 `npm install -g wscat`
```bash
wscat -c "ws://127.0.0.1:6000/ws/chatroom?token=your_token"
```

## 📞 技术支持

如果在使用过程中遇到问题，请：

1. 查看浏览器控制台错误信息
2. 检查WebSocket连接状态
3. 确认后端服务运行状态
4. 联系后端开发团队

---

**文档版本**: v1.1  
**最后更新**: 2025-07-26  
**WebSocket端口**: 6000  
**适用后端版本**: DifyChatBackend v2.0+
