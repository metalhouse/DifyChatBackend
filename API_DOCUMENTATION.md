# DifyChatBackend API 文档 v2.1 - 前端集成优化版

## 📖 概述

DifyChatBackend API v2.1 是基于Dify平台的智能对话后端服务的标准化版本。本版本在v2.0基础上新增了前端急需的API端点，并实施了分层信息披露的安全机制。

### 🎯 核心特性

- **标准化响应格式**: 所有API端点返回统一的JSON响应格式
- **完整的错误码系统**: 30+种错误码覆盖所有业务场景
- **请求验证**: 基于Pydantic的自动请求参数验证
- **JWT认证**: 现代化的令牌认证系统，支持自动刷新
- **Redis缓存**: 高性能缓存系统，显著提升响应速度
- **权限控制**: 细粒度的用户权限和智能体访问控制
- **API版本控制**: 使用`/api/v1/`路径支持版本管理
- **向后兼容**: 保持对旧版本API路径的兼容支持
- **🆕 分层信息披露**: 基础信息公开，敏感信息需认证
- **🆕 单资源详情**: 支持获取单个智能体和对话的详细信息
- **🆕 系统统计**: 提供实时系统运行统计信息

### 🔧 技术栈

- **框架**: Flask 2.0+
- **认证**: JWT (PyJWT)
- **缓存**: Redis
- **验证**: Pydantic v2
- **日志**: 结构化日志系统
- **文档**: 完整的API文档和错误码说明
- **🆕 安全**: 分层权限控制和信息披露

## 🏗️ API 架构

### 基础URL

```
# 生产环境
https://api.yourcompany.com

# 开发环境
http://localhost:5000
```

### API版本

当前版本: `v2.1`  
所有API端点使用路径前缀: `/api/v1/`

### 认证方式

```http
Authorization: Bearer <access_token>
```

## 📋 标准响应格式

### 成功响应

```json
{
  "success": true,
  "message": "操作成功的描述",
  "data": {
    // 响应数据，根据具体API而定
  },
  "pagination": {  // 仅在列表接口中存在
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1642147200
}
```

### 错误响应

```json
{
  "success": false,
  "error_code": "VALIDATION_ERROR",
  "message": "请求参数验证失败",
  "data": {  // 可选，包含额外的错误信息
    "username": ["字段长度至少3位"],
    "password": ["字段长度至少6位"]
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1642147200
}
```

## 🔐 认证系统

### 登录

**端点**: `POST /api/v1/auth/login`

**请求体**:
```json
{
  "username": "admin",
  "password": "password123",
  "remember_me": false
}
```

**响应**:
```json
{
  "success": true,
  "message": "登录成功",
  "data": {
    "user": {
      "username": "admin",
      "display_name": "管理员",
      "email": "admin@example.com",
      "permissions": ["access_agents", "send_messages", "view_conversations"]
    },
    "tokens": {
      "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
      "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",
      "expires_in": 3600,
      "token_type": "Bearer"
    },
    "session_info": {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "device_id": "desktop-chrome-001",
      "ip_address": "192.168.1.100",
      "active_sessions": 1
    }
  }
}
```

### 刷新令牌

**端点**: `POST /api/v1/auth/refresh`

**请求体**:
```json
{
  "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4..."
}
```

### 获取当前用户

**端点**: `GET /api/v1/auth/me`

**需要认证**: ✅

### 登出

**端点**: `POST /api/v1/auth/logout`

**需要认证**: ✅

## 🤖 智能体管理

### 获取智能体列表

**端点**: `GET /api/v1/chat/agents` ⭐ **数据格式已修复 v2.1.1**

**需要认证**: ✅  
**需要权限**: `access_agents`

**查询参数**:
- `page` (int, 可选): 页码，默认为1
- `page_size` (int, 可选): 每页数量，默认为20，最大100
- `search` (string, 可选): 搜索关键词（搜索名称和描述）
- `category` (string, 可选): 智能体分类
- `use_cache` (bool, 可选): 是否使用缓存，默认为true

**响应格式更新**:
```json
{
  "success": true,
  "message": "获取智能体列表成功",
  "data": [
    {
      "id": "agent_1751526225_7744",           // ✅ 字段名已修复 (v2.1.1)
      "name": "财务助手_A",                      // 智能体名称
      "welcome_message": "您好！我是您的财务助手，可以高效协助您记录或查询收支信息。\n\n使用方式举例：\n📝 添加记录 → \"不使用预算刷交行卡补交去年个税，费用5800元\"\n🔍 查询记录 → \"请显示2023年所有个税缴纳记录\"\n\n我会自动归类消费类型（如\"税费\"）、支付渠道（如\"交行卡\"）并标注非预算支出。需要其他财务服务也可随时告诉我！\n\n查一下这个月消费情况\n查一下这个月预算使用情况\n请生成本周财务报告，分析支出趋势和预算执行情况。"  // 🆕 欢迎语文本 (v2.1.2)
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 1,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  },
  "request_id": "req_123456789",
  "timestamp": 1753314738
}
```

**重要说明**:
- 🔧 **v2.1.1修复**: 字段名从 `agent_id` 更改为 `id`，符合前端JavaScript标准
- 🆕 **v2.1.2新增**: 添加 `welcome_message` 字段，提供智能体欢迎语用于前端展示
- 📋 实际返回的数据基于用户权限和智能体配置
- 🎯 前端可以直接使用 `agent.id` 访问智能体ID

### 获取智能体配置

**端点**: `GET /api/v1/agent/config`

**需要认证**: ✅  
**需要权限**: `view_agent_config`

**查询参数**:
- `agent_id` (string, 必需): 智能体ID
- `use_cache` (bool, 可选): 是否使用缓存

### 🆕 获取单个智能体详情

**端点**: `GET /api/v1/agents/{id}`

**需要认证**: ✅  
**需要权限**: `access_agents`

**路径参数**:
- `id` (string, 必需): 智能体ID

**查询参数**:
- `use_cache` (bool, 可选): 是否使用缓存，默认为true

**响应**:
```json
{
  "success": true,
  "message": "获取智能体详情成功",
  "data": {
    "id": "chatgpt-001",
    "name": "ChatGPT助手",
    "description": "智能对话助手，具备强大的自然语言理解能力",
    "category": "assistant",
    "is_active": true,
    "owner_only": false,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-02T12:00:00Z",
    "settings": {
      "temperature": 0.7,
      "max_tokens": 2000,
      "system_prompt": "你是一个专业的AI助手..."
    },
    "stats": {
      "total_conversations": 150,
      "total_messages": 1200,
      "avg_response_time": "1.2s"
    }
  }
}
```

## 💬 对话管理

### 获取对话列表

**端点**: `GET /api/v1/conversations`

**需要认证**: ✅  
**需要权限**: `view_conversations`

**查询参数**:
- `agent_id` (string, 可选): 智能体ID
- `page` (int, 可选): 页码
- `page_size` (int, 可选): 每页数量
- `search` (string, 可选): 搜索关键词
- `no_cache` (bool, 可选): 禁用缓存

### 🆕 获取单个对话详情

**端点**: `GET /api/v1/conversations/{id}`

**需要认证**: ✅  
**需要权限**: `view_conversations`

**路径参数**:
- `id` (string, 必需): 对话ID

**查询参数**:
- `use_cache` (bool, 可选): 是否使用缓存，默认为true
- `include_messages` (bool, 可选): 是否包含消息历史，默认为false

**响应**:
```json
{
  "success": true,
  "message": "获取对话详情成功",
  "data": {
    "id": "conv_12345",
    "agent_id": "chatgpt-001",
    "agent_name": "ChatGPT助手",
    "title": "关于Python编程的讨论",
    "status": "active",
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T11:30:00Z",
    "message_count": 15,
    "last_message_at": "2024-01-01T11:30:00Z",
    "metadata": {
      "tags": ["programming", "python"],
      "priority": "normal"
    },
    "messages": [
      {
        "id": "msg_001",
        "role": "user",
        "content": "请介绍Python的基础语法",
        "created_at": "2024-01-01T10:00:00Z"
      }
    ]
  }
}
```

### 创建新对话

**端点**: `POST /api/v1/conversations`

**需要认证**: ✅  
**需要权限**: `create_conversations`

**请求体**:
```json
{
  "agent_id": "chatgpt-001",
  "first_message": "你好，这是一个新对话",
  "inputs": {}
}
```

### 发送聊天消息

**端点**: `POST /api/v1/chat`

**需要认证**: ✅  
**需要权限**: `send_messages`

**请求体**:
```json
{
  "agent_id": "chatgpt-001",
  "message": "你好，请介绍一下你自己",
  "conversation_id": null,
  "stream": false,
  "inputs": {},
  "files": [],
  "auto_generate_name": true
}
```

**流式响应**:
设置 `"stream": true` 来启用流式响应（Server-Sent Events）。

## � 消息反馈系统

### 发送消息反馈（点赞/点踩）

**端点**: `POST /api/v1/messages/{message_id}/feedbacks`  
**兼容端点**: `POST /api/v1/chat/messages/{message_id}/rating` ⭐ **前端兼容**

**需要认证**: ✅  
**需要权限**: `send_messages`  
**智能体功能**: 需要启用 `message_feedback` 功能

**路径参数**:
- `message_id` (string, 必需): 消息ID

**请求体**:
```json
{
  "rating": "like",           // "like" 或 "dislike"
  "content": "回答很有帮助",    // 可选，反馈内容
  "agent_id": "4de73be9-b87c-470a-bd20-9b8c4e7b6c3b"  // 必需，智能体ID
}
```

**响应**:
```json
{
  "success": true,
  "message": "反馈提交成功",
  "data": {
    "message_id": "msg_12345",
    "rating": "like",
    "content": "回答很有帮助",
    "user": "metalhouse",
    "created_at": "2025-07-27T15:05:00Z"
  },
  "request_id": "req_feedback_001",
  "timestamp": 1753570500
}
```

### 获取消息反馈状态

**端点**: `GET /api/v1/messages/{message_id}/feedbacks`  
**兼容端点**: `GET /api/v1/chat/messages/{message_id}/rating` ⭐ **前端兼容**

**需要认证**: ✅  
**需要权限**: `view_conversations`  
**智能体功能**: 需要启用 `message_feedback` 功能

**路径参数**:
- `message_id` (string, 必需): 消息ID

**查询参数**:
- `agent_id` (string, 必需): 智能体ID

**响应**:
```json
{
  "success": true,
  "message": "反馈状态获取成功",
  "data": {
    "message_id": "msg_12345",
    "user": "metalhouse",
    "rating": null,          // null=未评价, "like"=点赞, "dislike"=点踩
    "content": null,
    "can_feedback": true     // 是否可以提交反馈
  },
  "request_id": "req_feedback_get_001",
  "timestamp": 1753570500
}
```

### 🚨 消息反馈功能对接注意事项

#### 1. **路径兼容性**
```javascript
// ✅ 推荐使用标准Dify API路径
POST /api/v1/messages/{messageId}/feedbacks
GET  /api/v1/messages/{messageId}/feedbacks?agent_id=xxx

// ✅ 前端兼容路径（推荐前端使用）
POST /api/v1/chat/messages/{messageId}/rating
GET  /api/v1/chat/messages/{messageId}/rating?agent_id=xxx
```

#### 2. **必需参数检查**
```javascript
// ❌ 错误：缺少agent_id参数
const response = await fetch('/api/v1/messages/123/feedbacks', {
  method: 'POST',
  body: JSON.stringify({
    rating: 'like',
    content: '很好的回答'
  })
});

// ✅ 正确：包含agent_id参数
const response = await fetch('/api/v1/chat/messages/123/rating', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    rating: 'like',
    content: '很好的回答',
    agent_id: '4de73be9-b87c-470a-bd20-9b8c4e7b6c3b'  // 必需！
  })
});
```

#### 3. **智能体功能配置检查**
在使用反馈功能前，确保智能体已启用 `message_feedback` 功能：

```json
// data/agent_features.json 配置示例
{
  "4de73be9-b87c-470a-bd20-9b8c4e7b6c3b": {
    "agent_id": "4de73be9-b87c-470a-bd20-9b8c4e7b6c3b",
    "agent_name": "测试智能体",
    "enabled_features": [
      "suggested_questions",
      "message_feedback",        // ✅ 必须启用此功能
      "conversation_rename",
      "text_to_audio"
    ],
    "disabled_features": [
      "audio_to_text",
      "message_annotation",
      "file_upload"
    ]
  }
}
```

#### 4. **错误处理示例**
```javascript
async function submitFeedback(messageId, rating, agentId, content = null) {
  try {
    const response = await fetch(`/api/v1/chat/messages/${messageId}/rating`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        rating: rating,
        content: content,
        agent_id: agentId
      })
    });

    const data = await response.json();
    
    if (!data.success) {
      // 处理业务错误
      switch (data.error_code) {
        case 'MISSING_PARAMETER':
          console.error('缺少必需参数:', data.message);
          break;
        case 'FEATURE_NOT_SUPPORTED':
          console.error('智能体不支持反馈功能:', data.message);
          break;
        case 'AGENT_CONFIG_NOT_FOUND':
          console.error('智能体配置未找到:', data.message);
          break;
        default:
          console.error('提交反馈失败:', data.message);
      }
      return false;
    }
    
    console.log('反馈提交成功:', data.data);
    return true;
    
  } catch (error) {
    console.error('网络错误:', error);
    return false;
  }
}

// 使用示例
submitFeedback('msg_12345', 'like', '4de73be9-b87c-470a-bd20-9b8c4e7b6c3b', '回答很有帮助');
```

#### 5. **CORS预检请求处理**
系统已配置CORS支持，OPTIONS请求会正常处理：

```javascript
// 浏览器会自动发送OPTIONS预检请求
// 服务器返回允许的方法和头部
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
Access-Control-Allow-Headers: authorization, content-type
```

#### 6. **实时反馈状态查询**
```javascript
async function getFeedbackStatus(messageId, agentId) {
  try {
    const response = await fetch(
      `/api/v1/chat/messages/${messageId}/rating?agent_id=${agentId}`,
      {
        headers: {
          'Authorization': `Bearer ${getToken()}`
        }
      }
    );

    const data = await response.json();
    
    if (data.success) {
      return {
        hasRated: data.data.rating !== null,
        rating: data.data.rating,        // null, "like", "dislike"
        content: data.data.content,
        canFeedback: data.data.can_feedback
      };
    }
    
    return null;
  } catch (error) {
    console.error('获取反馈状态失败:', error);
    return null;
  }
}
```

#### 7. **测试验证**
使用以下测试数据验证功能：
- **智能体ID**: `4de73be9-b87c-470a-bd20-9b8c4e7b6c3b`（已配置message_feedback功能）
- **测试用户**: `metalhouse` / `Iwhyi3589`
- **测试消息ID**: 任何有效的消息ID

#### 8. **性能优化建议**
- 使用防抖（debounce）避免重复提交
- 本地缓存反馈状态减少API调用
- 批量获取多个消息的反馈状态

```javascript
// 防抖提交反馈
const debouncedSubmitFeedback = debounce(submitFeedback, 300);

// 批量获取反馈状态（如果需要）
async function getBatchFeedbackStatus(messageIds, agentId) {
  const promises = messageIds.map(id => getFeedbackStatus(id, agentId));
  return await Promise.all(promises);
}
```

## �🗂️ 缓存管理

### 获取用户权限

**端点**: `GET /api/v1/user/permissions`

**需要认证**: ✅  
**需要权限**: `view_permissions`

### 缓存健康检查

**端点**: `GET /api/v1/cache/health`

**需要认证**: ✅  
**需要权限**: `manage_cache` 或 `admin`

### 获取缓存统计

**端点**: `GET /api/v1/cache/stats`

**需要认证**: ✅  
**需要权限**: `view_stats`

### 预热缓存

**端点**: `POST /api/v1/cache/preload`

**需要认证**: ✅  
**需要权限**: `manage_cache` 或 `admin`

### 刷新智能体配置缓存

**端点**: `POST /api/v1/cache/refresh`

**需要认证**: ✅  
**需要权限**: `manage_cache` 或 `admin`

### 清除缓存

**端点**: `DELETE /api/v1/cache/invalidate`

**需要认证**: ✅  
**需要权限**: `manage_cache` 或 `admin`

**请求体**:
```json
{
  "username": "admin",
  "agent_id": "chatgpt-001",
  "cache_type": "conversations"  // all, conversations, agents, permissions
}
```

## 🔧 系统端点

### 健康检查

**端点**: `GET /health` 或 `GET /api/v1/health`

**响应**:
```json
{
  "success": true,
  "message": "服务健康检查完成",
  "data": {
    "service": "DifyChatBackend",
    "status": "healthy",
    "environment": "development",
    "version": "2.0.0-standard",
    "timestamp": 1642147200,
    "cache": {
      "enabled": true,
      "status": "connected"
    },
    "dify_service": {
      "status": "available"
    }
  }
}
```

### API信息

**端点**: `GET /api/v1/info`

**响应**:
```json
{
  "success": true,
  "message": "API信息获取成功",
  "data": {
    "name": "DifyChatBackend API",
    "version": "2.0.0-standard",
    "description": "基于Dify的智能对话后端服务 - 标准化版本",
    "environment": "development",
    "features": [
      "JWT认证系统",
      "Redis缓存管理",
      "智能体对话",
      "会话管理",
      "权限控制",
      "标准化API响应"
    ],
    "api_version": "v1",
    "documentation": {
      "response_format": "/docs/api-response-format",
      "error_codes": "/docs/error-codes",
      "authentication": "/docs/authentication"
    }
  }
}
```

## ❌ 错误处理

### HTTP状态码

- `200` - 请求成功
- `400` - 请求参数错误
- `401` - 需要身份验证或认证失败
- `403` - 访问被拒绝（权限不足）
- `404` - 资源不存在
- `405` - 请求方法不被允许
- `429` - 请求频率过高
- `500` - 服务器内部错误
- `502` - 外部服务错误
- `503` - 服务不可用

### 错误码系统

详细的错误码说明请参考：[错误码文档](ERROR_CODES.md)

常见错误码：

| 错误码 | 描述 | HTTP状态码 |
|-------|------|-----------|
| `VALIDATION_ERROR` | 请求参数验证失败 | 400 |
| `AUTHENTICATION_REQUIRED` | 需要身份验证 | 401 |
| `INVALID_CREDENTIALS` | 用户名或密码错误 | 401 |
| `ACCESS_DENIED` | 访问被拒绝 | 403 |
| `RESOURCE_NOT_FOUND` | 资源不存在 | 404 |
| `RATE_LIMITED` | 请求频率过高 | 429 |
| `INTERNAL_ERROR` | 服务器内部错误 | 500 |

## 🔒 权限系统

### 用户权限

- `access_agents` - 访问智能体列表
- `view_conversations` - 查看对话列表
- `send_messages` - 发送消息
- `create_conversations` - 创建新对话
- `view_permissions` - 查看用户权限
- `view_agent_config` - 查看智能体配置
- `view_stats` - 查看统计信息
- `manage_cache` - 管理缓存
- `admin` - 管理员权限

### 智能体访问控制

用户只能访问有权限的智能体。系统会自动验证：

1. 用户是否有访问该智能体的权限
2. 智能体是否为`owner_only`（仅所有者可访问）
3. 智能体是否处于活跃状态

## 📊 系统管理

### 🆕 获取系统统计信息

**端点**: `GET /api/v1/stats`

**需要认证**: ✅  
**需要权限**: `admin`

**查询参数**:
- `include_details` (bool, 可选): 是否包含详细统计，默认为false
- `time_range` (string, 可选): 时间范围（'24h', '7d', '30d'），默认为'24h'

**响应**:
```json
{
  "success": true,
  "message": "获取系统统计成功",
  "data": {
    "system": {
      "uptime": "72h 15m",
      "version": "v2.1.0",
      "environment": "production",
      "cache_hit_rate": 0.85,
      "avg_response_time": "125ms"
    },
    "users": {
      "total": 1250,
      "active_today": 89,
      "new_today": 5
    },
    "agents": {
      "total": 25,
      "active": 23,
      "most_used": "chatgpt-001"
    },
    "conversations": {
      "total": 5670,
      "today": 156,
      "avg_per_user": 4.5
    },
    "messages": {
      "total": 45230,
      "today": 890,
      "avg_per_conversation": 8.0
    },
    "performance": {
      "requests_per_minute": 45.2,
      "error_rate": 0.02,
      "cpu_usage": "25%",
      "memory_usage": "68%"
    }
  }
}
```

### 🔄 系统信息（分层披露）

#### 公开系统信息

**端点**: `GET /api/v1/info/public`

**需要认证**: ❌

**响应**:
```json
{
  "success": true,
  "message": "获取系统信息成功",
  "data": {
    "service_name": "DifyChatBackend",
    "version": "v2.1.0",
    "api_version": "v1",
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00Z",
    "features": [
      "chat",
      "agents",
      "conversations",
      "jwt_auth"
    ]
  }
}
```

#### 认证用户系统信息

**端点**: `GET /api/v1/info`

**需要认证**: ✅

**响应**:
```json
{
  "success": true,
  "message": "获取完整系统信息成功",
  "data": {
    "service_name": "DifyChatBackend",
    "version": "v2.1.0",
    "api_version": "v1",
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00Z",
    "features": [
      "chat",
      "agents",
      "conversations",
      "jwt_auth",
      "redis_cache",
      "admin_panel"
    ],
    "environment": "production",
    "uptime": "72h 15m",
    "cache_status": "connected",
    "dify_status": "connected",
    "user_permissions": [
      "access_agents",
      "view_conversations",
      "create_conversations"
    ],
    "rate_limits": {
      "requests_per_minute": 60,
      "remaining": 58
    }
  }
}
```

## 🚀 自动化功能

### 令牌自动刷新

当访问令牌即将过期时，系统会自动刷新令牌并在响应头中返回新令牌：

```http
X-New-Access-Token: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

客户端应该检查此响应头并更新存储的访问令牌。

### 缓存自动管理

- **自动缓存**: 频繁访问的数据自动缓存
- **智能失效**: 数据更新时自动清除相关缓存
- **预热机制**: 系统启动时预热关键数据

## 📊 性能优化

### 缓存策略

- **对话列表**: 5分钟TTL
- **智能体列表**: 1小时TTL
- **用户权限**: 30分钟TTL
- **智能体配置**: 1小时TTL

### 分页支持

所有列表接口都支持分页：

- 默认页面大小: 20
- 最大页面大小: 100
- 分页信息包含总数和总页数

### 请求追踪

每个请求都有唯一的`request_id`，便于日志追踪和问题排查。

## 🔄 向后兼容性

为了保持与旧版本的兼容性，以下路径仍然可用：

- `/login` → `/api/v1/auth/login`
- `/api/agents` → `/api/v1/agents`
- `/api/conversations` → `/api/v1/conversations`
- `/api/chat` → `/api/v1/chat`

建议使用新的v1路径以获得完整的标准化响应格式。

## 📚 SDK和工具

### Postman集合

提供完整的Postman测试集合：`DifyChatBackend_API_v2_Standard.postman_collection.json`

### 测试工具

- `test_api_standard.py` - Python测试脚本
- `test_request_validator.py` - 请求验证测试

## 🛠️ 开发指南

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python app_standard.py
```

### 环境配置

复制 `.env.example` 为 `.env` 并配置相应的环境变量。

### 日志级别

- `DEBUG` - 详细调试信息
- `INFO` - 一般信息（默认）
- `WARNING` - 警告信息
- `ERROR` - 错误信息

## 📞 支持

如有问题，请通过以下方式联系：

- **GitHub Issues**: [项目Issues页面]
- **邮箱**: support@yourcompany.com
- **文档**: [完整API文档]

---

**版本**: v2.1.0-frontend-optimized  
**更新时间**: 2025年1月15日  
**维护团队**: 后端开发团队  
**更新内容**: 
- 🆕 新增单资源详情端点（agents/{id}, conversations/{id}）
- 🆕 新增系统统计端点（/api/v1/stats）
- 🔒 实施分层信息披露安全机制
- 📈 优化前端集成支持
