# 前端对接聊天室系统指南

## 📋 概述

本文档为前端开发者提供完整的聊天室系统对接指南，包括API接口、认证流程、错误处理和调试信息。

**系统版本**: v2.1.3  
**API版本**: v1  
**基础URL**: `http://127.0.0.1:5000`  
**最后更新**: 2025年7月26日

---

## 🔐 认证系统

### JWT认证流程

#### 1. 用户登录
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "metalhouse",
  "password": "Iwhyi3589"
}
```

**成功响应** (200):
```json
{
  "success": true,
  "message": "登录成功",
  "data": {
    "user": {
      "user_id": "metalhouse",
      "username": "metalhouse",
      "user_name": "metalhouse的昵称",
      "role": "user",
      "email": null,
      "avatar_url": "https://api.dicebear.com/7.x/miniavs/svg?seed=metalhouse"
    },
    "tokens": {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "Bearer",
      "expires_in": 3600,
      "issued_at": 1753493366,
      "device_id": "f342c0467dc8b9c9"
    },
    "session_info": {
      "device_id": "f342c0467dc8b9c9",
      "ip_address": "127.0.0.1",
      "login_time": "2025-07-26T09:29:26.640199",
      "active_sessions": 1,
      "remember_me": false
    }
  },
  "request_id": "110d26af-084f-481b-98f8-9625200bdf03",
  "timestamp": 1753464566
}
```

#### 2. 使用JWT Token
所有聊天室API请求都需要在请求头中包含JWT token：

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### 用户权限说明

| 用户 | 默认角色 | 聊天室权限 |
|------|----------|------------|
| metalhouse | admin | 所有权限 (创建、管理、删除聊天室) |
| 其他用户 | chatroom_user | 访问权限 (加入聊天室、发送消息) |

---

## 🏠 聊天室API接口

### 基础信息

**API前缀**: `/api/v1/chatroom`  
**认证方式**: JWT Bearer Token  
**响应格式**: JSON  

### 1. 创建聊天室

```http
POST /api/v1/chatroom/create
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "name": "AI讨论室",
  "description": "人工智能技术讨论专区",
  "is_public": true,
  "max_users": 50
}
```

**成功响应** (200):
```json
{
  "success": true,
  "message": "创建聊天室成功",
  "data": {
    "id": "a00e2d25-de74-440b-9d68-67642b6fd2b2",
    "name": "AI讨论室",
    "description": "人工智能技术讨论专区",
    "is_public": true,
    "max_users": 50,
    "created_at": "2025-07-26T00:17:15"
  },
  "timestamp": "2025-07-26T00:17:14.811133"
}
```

**权限要求**: `chatroom_admin` (仅管理员)

### 2. 获取聊天室详情

```http
GET /api/v1/chatroom/{chatroom_id}
Authorization: Bearer YOUR_TOKEN
```

**成功响应** (200):
```json
{
  "success": true,
  "message": "获取聊天室详情成功",
  "data": {
    "id": "a00e2d25-de74-440b-9d68-67642b6fd2b2",
    "name": "AI技术讨论室",
    "description": "专业的人工智能技术交流平台",
    "is_public": true,
    "max_users": 100,
    "created_at": "2025-07-26T00:17:15",
    "members": [
      {
        "user_id": "metalhouse",
        "role": "admin",
        "joined_at": "2025-07-26T00:17:15",
        "last_active_at": "2025-07-26T00:17:15"
      }
    ],
    "online_users": [],
    "member_count": 1,
    "online_count": 0
  },
  "timestamp": "2025-07-26T01:34:25.257295"
}
```

**权限要求**: `chatroom_access`

### 3. 更新聊天室

```http
PUT /api/v1/chatroom/{chatroom_id}
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "name": "AI技术讨论室",
  "description": "专业的人工智能技术交流平台",
  "max_users": 100
}
```

**成功响应** (200):
```json
{
  "success": true,
  "message": "更新聊天室成功",
  "timestamp": "2025-07-25T16:22:25.154579"
}
```

**权限要求**: `chatroom_admin` (仅管理员)

### 4. 删除聊天室

```http
DELETE /api/v1/chatroom/{chatroom_id}
Authorization: Bearer YOUR_TOKEN
```

**成功响应** (200):
```json
{
  "success": true,
  "message": "删除聊天室成功",
  "timestamp": "2025-07-26T01:34:05.978408"
}
```

**权限要求**: `chatroom_admin` (仅管理员)

### 5. 获取聊天室列表

```http
GET /api/v1/chatroom/list?page=1&page_size=20
Authorization: Bearer YOUR_TOKEN
```

**成功响应** (200):
```json
{
  "success": true,
  "message": "获取聊天室列表成功",
  "data": {
    "chatrooms": [
      {
        "id": "a00e2d25-de74-440b-9d68-67642b6fd2b2",
        "name": "AI技术讨论室",
        "description": "专业的人工智能技术交流平台",
        "is_public": true,
        "max_users": 100,
        "created_at": "2025-07-26T00:17:15",
        "member_count": 1
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 1,
      "total_pages": 1
    }
  },
  "timestamp": "2025-07-26T01:35:00.000000"
}
```

**权限要求**: `chatroom_access`

---

## 🚨 错误响应格式

### 标准错误响应

```json
{
  "success": false,
  "message": "错误描述信息",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-07-26T01:32:06.292256"
}
```

### 常见错误代码

| 错误代码 | HTTP状态码 | 说明 | 解决方案 |
|----------|------------|------|----------|
| `AUTH_TOKEN_REQUIRED` | 401 | 缺少认证令牌 | 在请求头添加 Authorization |
| `INVALID_TOKEN` | 401 | 令牌无效或过期 | 重新登录获取新令牌 |
| `TOKEN_EXPIRED` | 401 | 令牌已过期 | 使用refresh_token刷新或重新登录 |
| `INSUFFICIENT_PERMISSIONS` | 403 | 权限不足 | 检查用户权限或联系管理员 |
| `CHATROOM_NOT_FOUND` | 404 | 聊天室不存在 | 检查聊天室ID是否正确 |
| `CHATROOM_NAME_REQUIRED` | 400 | 聊天室名称不能为空 | 提供有效的name字段 |
| `DATABASE_SERVICE_UNAVAILABLE` | 500 | 数据库服务不可用 | 联系技术支持 |

### 错误处理示例 (JavaScript)

```javascript
// 使用fetch API的错误处理示例
async function createChatroom(chatroomData, token) {
  try {
    const response = await fetch('/api/v1/chatroom/create', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(chatroomData)
    });

    const data = await response.json();

    if (!response.ok) {
      // 处理HTTP错误状态
      switch (data.error_code) {
        case 'INVALID_TOKEN':
        case 'TOKEN_EXPIRED':
          // 重新登录
          redirectToLogin();
          break;
        case 'INSUFFICIENT_PERMISSIONS':
          showError('您没有权限执行此操作');
          break;
        case 'CHATROOM_NAME_REQUIRED':
          showError('请输入聊天室名称');
          break;
        default:
          showError(data.message || '创建聊天室失败');
      }
      return null;
    }

    return data.data; // 返回聊天室数据
  } catch (error) {
    console.error('网络错误:', error);
    showError('网络连接失败，请重试');
    return null;
  }
}
```

---

## 🛠️ 开发调试

### 健康检查

系统提供了健康检查脚本，可以快速验证系统状态：

```bash
python health_check.py
```

### 测试用户凭据

- **管理员账户**: metalhouse / Iwhyi3589
- **权限**: 所有聊天室管理权限

### 环境配置检查

确保以下环境变量正确配置：

```bash
# 聊天室功能开关
CHATROOM_ENABLED=true

# MariaDB数据库配置
MARIADB_ENABLED=true
MARIADB_HOST=192.168.1.10
MARIADB_PORT=3307
MARIADB_DATABASE=chatroom_db
MARIADB_USERNAME=chatroom_user
MARIADB_PASSWORD=k^yWqm7g1xemL3@S

# JWT密钥配置
JWT_SECRET_KEY=jwt-secret-key-for-chatroom-system
SECRET_KEY=dev-secret-key-for-testing
```

### API测试工具

#### 使用curl测试

```bash
# 1. 登录获取token
curl -X POST http://127.0.0.1:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"metalhouse","password":"Iwhyi3589"}'

# 2. 创建聊天室
curl -X POST http://127.0.0.1:5000/api/v1/chatroom/create \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试室","description":"测试聊天室","is_public":true}'

# 3. 获取聊天室详情
curl -X GET http://127.0.0.1:5000/api/v1/chatroom/CHATROOM_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 使用Postman

项目包含Postman集合文件：
- `DifyChatBackend_API_Standard.postman_collection.json`
- `DifyChatBackend_API_v1_Collection.postman_collection.json`

---

## 📊 数据结构定义

### 聊天室对象 (Chatroom)

```typescript
interface Chatroom {
  id: string;                    // 聊天室唯一ID (UUID)
  name: string;                  // 聊天室名称
  description: string;           // 聊天室描述
  is_public: boolean;            // 是否公开
  max_users: number;            // 最大用户数
  created_at: string;           // 创建时间 (ISO 8601)
  member_count: number;         // 成员数量
  online_count: number;         // 在线用户数
}
```

### 聊天室成员 (ChatroomMember)

```typescript
interface ChatroomMember {
  user_id: string;              // 用户ID
  role: string;                 // 成员角色 (admin, member)
  joined_at: string;            // 加入时间 (ISO 8601)
  last_active_at: string;       // 最后活跃时间 (ISO 8601)
}
```

### 用户对象 (User)

```typescript
interface User {
  user_id: string;              // 用户ID
  username: string;             // 用户名
  user_name: string;            // 显示名称
  role: string;                 // 系统角色
  email: string | null;         // 邮箱
  avatar_url: string;           // 头像URL
}
```

---

## 🔄 前端集成示例

### React Hook示例

```javascript
import { useState, useEffect } from 'react';

// 聊天室管理Hook
function useChatrooms(token) {
  const [chatrooms, setChatrooms] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const API_BASE = 'http://127.0.0.1:5000/api/v1/chatroom';

  // 获取聊天室列表
  const fetchChatrooms = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/list`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();
      
      if (data.success) {
        setChatrooms(data.data.chatrooms);
      } else {
        setError(data.message);
      }
    } catch (err) {
      setError('网络错误');
    } finally {
      setLoading(false);
    }
  };

  // 创建聊天室
  const createChatroom = async (chatroomData) => {
    try {
      const response = await fetch(`${API_BASE}/create`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(chatroomData)
      });

      const data = await response.json();
      
      if (data.success) {
        await fetchChatrooms(); // 刷新列表
        return data.data;
      } else {
        throw new Error(data.message);
      }
    } catch (err) {
      setError(err.message);
      return null;
    }
  };

  useEffect(() => {
    if (token) {
      fetchChatrooms();
    }
  }, [token]);

  return {
    chatrooms,
    loading,
    error,
    createChatroom,
    refreshChatrooms: fetchChatrooms
  };
}

export default useChatrooms;
```

### Vue.js组合式API示例

```javascript
import { ref, onMounted } from 'vue';

// 聊天室服务
export function useChatroomService(token) {
  const chatrooms = ref([]);
  const loading = ref(false);
  const error = ref(null);

  const API_BASE = 'http://127.0.0.1:5000/api/v1/chatroom';

  // 获取聊天室列表
  const getChatrooms = async () => {
    loading.value = true;
    error.value = null;

    try {
      const response = await fetch(`${API_BASE}/list`, {
        headers: {
          'Authorization': `Bearer ${token.value}`
        }
      });

      const data = await response.json();
      
      if (data.success) {
        chatrooms.value = data.data.chatrooms;
      } else {
        error.value = data.message;
      }
    } catch (err) {
      error.value = '网络连接失败';
    } finally {
      loading.value = false;
    }
  };

  onMounted(() => {
    if (token.value) {
      getChatrooms();
    }
  });

  return {
    chatrooms,
    loading,
    error,
    getChatrooms
  };
}
```

---

## 📞 技术支持

### 相关文档
- **[详细测试报告](CHATROOM_SYSTEM_TESTING_REPORT.md)** - 完整的功能测试和技术细节
- **[快速部署指南](CHATROOM_QUICK_START.md)** - 快速启动指南
- **[问题排查指南](CHATROOM_TROUBLESHOOTING.md)** - 常见问题解决方案

### 常见问题

1. **Token过期处理**: Access Token有效期1小时，建议实现自动刷新机制
2. **权限问题**: 确认用户具有相应权限，metalhouse用户默认为管理员
3. **网络连接**: 确保服务运行在正确的地址和端口
4. **CORS问题**: 如果前端跨域，需要在后端添加CORS支持

### 联系方式

- **项目仓库**: DifyChatBackend
- **技术文档**: 项目根目录文档文件
- **健康检查**: `python health_check.py`

---

**文档版本**: v1.0  
**维护者**: DifyChatBackend开发团队  
**最后更新**: 2025年7月26日
