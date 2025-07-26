# 聊天室 WebSocket API 文档

## 📡 连接信息

**WebSocket 端点**: `ws://localhost:5000/chatroom`

**认证方式**: JWT Token（通过查询参数或认证头传递）

```javascript
// 方式1: 查询参数
const socket = io('/chatroom?token=your_jwt_token');

// 方式2: 认证头
const socket = io('/chatroom', {
    auth: {
        token: 'your_jwt_token'
    }
});
```

## 🔌 连接生命周期

### 连接建立

客户端连接时，服务器会验证JWT token并发送连接确认：

```javascript
socket.on('connected', (data) => {
    console.log(data);
    // 输出:
    // {
    //     "success": true,
    //     "message": "连接成功",
    //     "user_id": "user123",
    //     "timestamp": "2024-01-15T10:30:00Z"
    // }
});
```

### 连接断开

```javascript
socket.on('disconnect', (reason) => {
    console.log('断开连接:', reason);
});
```

## 📤 客户端发送事件

### 1. 获取聊天室列表

**事件名**: `get_chatrooms`

**参数**: 无

```javascript
socket.emit('get_chatrooms');
```

**响应事件**: `chatroom_list`

---

### 2. 加入聊天室

**事件名**: `join_chatroom`

**参数**:
```javascript
{
    "chatroom_id": "chatroom-uuid"
}
```

**示例**:
```javascript
socket.emit('join_chatroom', {
    chatroom_id: 'f47ac10b-58cc-4372-a567-0e02b2c3d479'
});
```

**响应事件**: `chatroom_joined` 或 `error`

---

### 3. 离开聊天室

**事件名**: `leave_chatroom`

**参数**:
```javascript
{
    "chatroom_id": "chatroom-uuid"
}
```

**示例**:
```javascript
socket.emit('leave_chatroom', {
    chatroom_id: 'f47ac10b-58cc-4372-a567-0e02b2c3d479'
});
```

**响应事件**: `chatroom_left` 或 `error`

---

### 4. 发送消息

**事件名**: `send_message`

**参数**:

#### 普通消息
```javascript
{
    "chatroom_id": "chatroom-uuid",
    "message": "Hello, World!",
    "message_type": "text",  // 可选: text, image, file
    "timestamp": "2024-01-15T10:30:00Z"
}
```

#### 加密消息
```javascript
{
    "chatroom_id": "chatroom-uuid",
    "message": "Hello, World!",  // 原文
    "encrypted": true,
    "encryption_data": {
        "iv": "base64-encoded-iv",
        "ciphertext": "base64-encoded-ciphertext",
        "tag": "base64-encoded-auth-tag"
    },
    "message_hash": "sha256-hash-of-message",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

**示例**:
```javascript
// 发送普通消息
socket.emit('send_message', {
    chatroom_id: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    message: 'Hello everyone!',
    message_type: 'text',
    timestamp: new Date().toISOString()
});

// 发送加密消息
socket.emit('send_message', {
    chatroom_id: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    message: 'Secret message',
    encrypted: true,
    encryption_data: {
        iv: 'YWJjZGVmZ2g=',
        ciphertext: 'encrypted_content_here',
        tag: 'auth_tag_here'
    },
    message_hash: 'sha256_hash_here',
    timestamp: new Date().toISOString()
});
```

**响应事件**: `message_sent` 或 `error`

---

### 5. 获取历史消息

**事件名**: `get_history`

**参数**:
```javascript
{
    "chatroom_id": "chatroom-uuid",
    "limit": 50,        // 可选，默认50
    "offset": 0,        // 可选，默认0
    "before_id": "message-uuid"  // 可选，获取此消息之前的历史
}
```

**示例**:
```javascript
// 获取最新50条消息
socket.emit('get_history', {
    chatroom_id: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    limit: 50
});

// 分页获取历史消息
socket.emit('get_history', {
    chatroom_id: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    limit: 20,
    offset: 100
});
```

**响应事件**: `message_history` 或 `error`

---

### 6. 获取在线用户

**事件名**: `get_online_users`

**参数**:
```javascript
{
    "chatroom_id": "chatroom-uuid"
}
```

**示例**:
```javascript
socket.emit('get_online_users', {
    chatroom_id: 'f47ac10b-58cc-4372-a567-0e02b2c3d479'
});
```

**响应事件**: `online_users` 或 `error`

## 📥 服务端推送事件

### 1. 连接成功确认

**事件名**: `connected`

**数据格式**:
```javascript
{
    "success": true,
    "message": "连接成功",
    "user_id": "user123",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### 2. 聊天室列表

**事件名**: `chatroom_list`

**数据格式**:
```javascript
{
    "success": true,
    "chatrooms": [
        {
            "id": "chatroom-uuid",
            "name": "聊天室名称",
            "description": "聊天室描述",
            "is_public": true,
            "max_users": 100,
            "created_at": "2024-01-15T10:30:00Z",
            "member_count": 25,
            "online_count": 8,
            "user_role": "member"  // admin, moderator, member
        }
    ]
}
```

---

### 3. 加入聊天室成功

**事件名**: `chatroom_joined`

**数据格式**:
```javascript
{
    "success": true,
    "message": "加入聊天室成功",
    "chatroom": {
        "id": "chatroom-uuid",
        "name": "聊天室名称",
        "description": "聊天室描述",
        "online_users": [
            {
                "user_id": "user123",
                "username": "用户名",
                "joined_at": "2024-01-15T10:30:00Z"
            }
        ]
    }
}
```

---

### 4. 新消息推送

**事件名**: `message`

**数据格式**:

#### 普通消息
```javascript
{
    "id": "message-uuid",
    "chatroom_id": "chatroom-uuid",
    "user_id": "sender-uuid",
    "username": "发送者用户名",
    "message": "消息内容",
    "message_type": "text",
    "encrypted": false,
    "created_at": "2024-01-15T10:30:00Z",
    "is_system": false
}
```

#### 加密消息
```javascript
{
    "id": "message-uuid",
    "chatroom_id": "chatroom-uuid",
    "user_id": "sender-uuid",
    "username": "发送者用户名",
    "message": "原始消息内容",
    "message_type": "text",
    "encrypted": true,
    "encryption_data": {
        "iv": "base64-encoded-iv",
        "ciphertext": "base64-encoded-ciphertext",
        "tag": "base64-encoded-auth-tag"
    },
    "message_hash": "sha256-hash",
    "created_at": "2024-01-15T10:30:00Z",
    "is_system": false
}
```

#### 系统消息
```javascript
{
    "id": "message-uuid",
    "chatroom_id": "chatroom-uuid",
    "message": "用户 张三 加入了聊天室",
    "message_type": "system",
    "encrypted": false,
    "created_at": "2024-01-15T10:30:00Z",
    "is_system": true
}
```

---

### 5. 消息发送确认

**事件名**: `message_sent`

**数据格式**:
```javascript
{
    "success": true,
    "message": "消息发送成功",
    "message_id": "message-uuid",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### 6. 历史消息

**事件名**: `message_history`

**数据格式**:
```javascript
{
    "success": true,
    "chatroom_id": "chatroom-uuid",
    "messages": [
        {
            "id": "message-uuid",
            "user_id": "sender-uuid",
            "username": "发送者用户名",
            "message": "消息内容",
            "message_type": "text",
            "encrypted": false,
            "created_at": "2024-01-15T10:30:00Z",
            "is_system": false
        }
    ],
    "total": 150,
    "limit": 50,
    "offset": 0
}
```

---

### 7. 用户加入通知

**事件名**: `user_joined`

**数据格式**:
```javascript
{
    "chatroom_id": "chatroom-uuid",
    "user": {
        "user_id": "user123",
        "username": "新用户名",
        "joined_at": "2024-01-15T10:30:00Z"
    },
    "online_count": 9
}
```

---

### 8. 用户离开通知

**事件名**: `user_left`

**数据格式**:
```javascript
{
    "chatroom_id": "chatroom-uuid",
    "user": {
        "user_id": "user123",
        "username": "离开的用户名",
        "left_at": "2024-01-15T10:30:00Z"
    },
    "online_count": 8
}
```

---

### 9. 在线用户列表

**事件名**: `online_users`

**数据格式**:
```javascript
{
    "success": true,
    "chatroom_id": "chatroom-uuid",
    "users": [
        {
            "user_id": "user123",
            "username": "用户名1",
            "joined_at": "2024-01-15T10:30:00Z",
            "last_seen": "2024-01-15T10:35:00Z"
        },
        {
            "user_id": "user456",
            "username": "用户名2",
            "joined_at": "2024-01-15T10:25:00Z",
            "last_seen": "2024-01-15T10:35:00Z"
        }
    ],
    "count": 2
}
```

---

### 10. 错误消息

**事件名**: `error`

**数据格式**:
```javascript
{
    "success": false,
    "error": "错误类型",
    "message": "错误描述信息",
    "code": "ERROR_CODE",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

**常见错误类型**:
```javascript
// 权限不足
{
    "success": false,
    "error": "permission_denied",
    "message": "您没有权限执行此操作",
    "code": "CHATROOM_PERMISSION_DENIED"
}

// 聊天室不存在
{
    "success": false,
    "error": "chatroom_not_found",
    "message": "聊天室不存在",
    "code": "CHATROOM_NOT_FOUND"
}

// 消息格式错误
{
    "success": false,
    "error": "invalid_message",
    "message": "消息格式无效",
    "code": "INVALID_MESSAGE_FORMAT"
}

// 加密验证失败
{
    "success": false,
    "error": "encryption_error",
    "message": "消息加密验证失败",
    "code": "MESSAGE_ENCRYPTION_FAILED"
}
```

## 💻 客户端示例代码

### JavaScript (浏览器)

```javascript
class ChatroomClient {
    constructor(token) {
        this.socket = io('/chatroom', {
            auth: { token: token }
        });
        this.setupEventHandlers();
    }
    
    setupEventHandlers() {
        // 连接成功
        this.socket.on('connected', (data) => {
            console.log('连接成功:', data);
            this.getChatrooms();
        });
        
        // 聊天室列表
        this.socket.on('chatroom_list', (data) => {
            console.log('聊天室列表:', data.chatrooms);
            this.renderChatroomList(data.chatrooms);
        });
        
        // 新消息
        this.socket.on('message', (message) => {
            console.log('新消息:', message);
            this.displayMessage(message);
        });
        
        // 用户加入
        this.socket.on('user_joined', (data) => {
            console.log('用户加入:', data.user.username);
            this.updateOnlineUsers(data);
        });
        
        // 错误处理
        this.socket.on('error', (error) => {
            console.error('WebSocket错误:', error);
            this.showError(error.message);
        });
    }
    
    // 获取聊天室列表
    getChatrooms() {
        this.socket.emit('get_chatrooms');
    }
    
    // 加入聊天室
    joinChatroom(chatroomId) {
        this.socket.emit('join_chatroom', {
            chatroom_id: chatroomId
        });
    }
    
    // 发送消息
    sendMessage(chatroomId, message) {
        this.socket.emit('send_message', {
            chatroom_id: chatroomId,
            message: message,
            message_type: 'text',
            timestamp: new Date().toISOString()
        });
    }
    
    // 获取历史消息
    getHistory(chatroomId, limit = 50) {
        this.socket.emit('get_history', {
            chatroom_id: chatroomId,
            limit: limit
        });
    }
}

// 使用示例
const chatClient = new ChatroomClient('your_jwt_token');
```

### Python (客户端)

```python
import socketio
import json

class ChatroomClient:
    def __init__(self, token):
        self.sio = socketio.Client()
        self.token = token
        self.setup_handlers()
        
    def setup_handlers(self):
        @self.sio.event
        def connected(data):
            print(f'连接成功: {data}')
            self.get_chatrooms()
            
        @self.sio.event
        def chatroom_list(data):
            print(f'聊天室列表: {data["chatrooms"]}')
            
        @self.sio.event
        def message(data):
            print(f'新消息: {data["username"]}: {data["message"]}')
            
        @self.sio.event
        def error(data):
            print(f'错误: {data["message"]}')
    
    def connect(self):
        self.sio.connect(
            'http://localhost:5000/chatroom',
            auth={'token': self.token}
        )
        
    def get_chatrooms(self):
        self.sio.emit('get_chatrooms')
        
    def join_chatroom(self, chatroom_id):
        self.sio.emit('join_chatroom', {
            'chatroom_id': chatroom_id
        })
        
    def send_message(self, chatroom_id, message):
        self.sio.emit('send_message', {
            'chatroom_id': chatroom_id,
            'message': message,
            'message_type': 'text',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })

# 使用示例
client = ChatroomClient('your_jwt_token')
client.connect()
```

## 🔐 消息加密示例

### JavaScript 加密实现

```javascript
// 需要引入crypto-js库
// <script src="https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.1.1/crypto-js.min.js"></script>

class MessageCrypto {
    static generateKey() {
        return CryptoJS.lib.WordArray.random(256/8); // 256位密钥
    }
    
    static encrypt(message, key) {
        const iv = CryptoJS.lib.WordArray.random(96/8); // 96位IV
        
        const encrypted = CryptoJS.AES.encrypt(message, key, {
            iv: iv,
            mode: CryptoJS.mode.GCM,
            padding: CryptoJS.pad.NoPadding
        });
        
        return {
            iv: iv.toString(CryptoJS.enc.Base64),
            ciphertext: encrypted.ciphertext.toString(CryptoJS.enc.Base64),
            tag: encrypted.tag.toString(CryptoJS.enc.Base64)
        };
    }
    
    static decrypt(encryptionData, key) {
        const iv = CryptoJS.enc.Base64.parse(encryptionData.iv);
        const ciphertext = CryptoJS.enc.Base64.parse(encryptionData.ciphertext);
        const tag = CryptoJS.enc.Base64.parse(encryptionData.tag);
        
        const decrypted = CryptoJS.AES.decrypt({
            ciphertext: ciphertext,
            tag: tag
        }, key, {
            iv: iv,
            mode: CryptoJS.mode.GCM,
            padding: CryptoJS.pad.NoPadding
        });
        
        return decrypted.toString(CryptoJS.enc.Utf8);
    }
    
    static calculateHash(message, timestamp, userId) {
        const data = `${message}:${timestamp}:${userId}`;
        return CryptoJS.SHA256(data).toString();
    }
}

// 使用示例
const key = MessageCrypto.generateKey();
const message = "Hello, this is a secret message!";
const timestamp = new Date().toISOString();
const userId = "user123";

// 加密消息
const encryptionData = MessageCrypto.encrypt(message, key);
const messageHash = MessageCrypto.calculateHash(message, timestamp, userId);

// 发送加密消息
socket.emit('send_message', {
    chatroom_id: 'room-id',
    message: message,
    encrypted: true,
    encryption_data: encryptionData,
    message_hash: messageHash,
    timestamp: timestamp
});
```

## 📊 错误处理

### 错误码参考

| 错误码 | 错误类型 | 描述 |
|--------|----------|------|
| `CHATROOM_NOT_FOUND` | `chatroom_not_found` | 聊天室不存在 |
| `CHATROOM_PERMISSION_DENIED` | `permission_denied` | 权限不足 |
| `INVALID_MESSAGE_FORMAT` | `invalid_message` | 消息格式无效 |
| `MESSAGE_ENCRYPTION_FAILED` | `encryption_error` | 消息加密验证失败 |
| `USER_NOT_IN_CHATROOM` | `access_denied` | 用户不在聊天室中 |
| `CHATROOM_FULL` | `chatroom_full` | 聊天室已满 |
| `MESSAGE_TOO_LONG` | `message_too_long` | 消息过长 |
| `RATE_LIMIT_EXCEEDED` | `rate_limit` | 发送频率过快 |

### 错误处理最佳实践

```javascript
// 全局错误处理
socket.on('error', (error) => {
    switch(error.code) {
        case 'CHATROOM_NOT_FOUND':
            showNotification('聊天室不存在', 'error');
            redirectToChatroomList();
            break;
            
        case 'CHATROOM_PERMISSION_DENIED':
            showNotification('您没有权限执行此操作', 'warning');
            break;
            
        case 'MESSAGE_ENCRYPTION_FAILED':
            showNotification('消息加密失败，请重试', 'error');
            break;
            
        case 'RATE_LIMIT_EXCEEDED':
            showNotification('发送消息过快，请稍后再试', 'warning');
            enableMessageInput(false, 5000); // 禁用5秒
            break;
            
        default:
            showNotification(error.message, 'error');
    }
});
```

---

此文档涵盖了聊天室WebSocket API的完整使用方法。如有疑问，请参考集成指南或联系开发团队。
