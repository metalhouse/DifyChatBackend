# DifyChatBackend API 文档 v2.0 - 标准化版本

## 📖 概述

DifyChatBackend API v2.0 是基于Dify平台的智能对话后端服务的标准化版本。本版本完全重构了API响应格式，引入了统一的错误处理机制，并提供了完整的请求验证系统。

### 🎯 核心特性

- **标准化响应格式**: 所有API端点返回统一的JSON响应格式
- **完整的错误码系统**: 30+种错误码覆盖所有业务场景
- **请求验证**: 基于Pydantic的自动请求参数验证
- **JWT认证**: 现代化的令牌认证系统，支持自动刷新
- **Redis缓存**: 高性能缓存系统，显著提升响应速度
- **权限控制**: 细粒度的用户权限和智能体访问控制
- **API版本控制**: 使用`/api/v1/`路径支持版本管理
- **向后兼容**: 保持对旧版本API路径的兼容支持

### 🔧 技术栈

- **框架**: Flask 2.0+
- **认证**: JWT (PyJWT)
- **缓存**: Redis
- **验证**: Pydantic v2
- **日志**: 结构化日志系统
- **文档**: 完整的API文档和错误码说明

## 🏗️ API 架构

### 基础URL

```
# 生产环境
https://api.yourcompany.com

# 开发环境
http://localhost:5000
```

### API版本

当前版本: `v1`  
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

**端点**: `GET /api/v1/agents`

**需要认证**: ✅  
**需要权限**: `access_agents`

**查询参数**:
- `page` (int, 可选): 页码，默认为1
- `page_size` (int, 可选): 每页数量，默认为20，最大100
- `search` (string, 可选): 搜索关键词（搜索名称和描述）
- `category` (string, 可选): 智能体分类
- `use_cache` (bool, 可选): 是否使用缓存，默认为true

**响应**:
```json
{
  "success": true,
  "message": "获取智能体列表成功",
  "data": [
    {
      "id": "chatgpt-001",
      "name": "ChatGPT助手",
      "description": "智能对话助手",
      "category": "assistant",
      "is_active": true,
      "owner_only": false,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 1,
    "total_pages": 1
  }
}
```

### 获取智能体配置

**端点**: `GET /api/v1/agent/config`

**需要认证**: ✅  
**需要权限**: `view_agent_config`

**查询参数**:
- `agent_id` (string, 必需): 智能体ID
- `use_cache` (bool, 可选): 是否使用缓存

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

## 🗂️ 缓存管理

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

**版本**: v2.0.0-standard  
**更新时间**: 2025年7月18日  
**维护团队**: 后端开发团队
