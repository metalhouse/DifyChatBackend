# DifyChatBackend API 路由重构文档

## 概述

DifyChatBackend API已完成标准化重构，实现了统一的响应格式、完整的认证保护和版本化路径管理。

## API版本路径

所有新API使用 `/api/v1/` 前缀，遵循RESTful设计原则。

### 路径结构
```
/api/v1/
├── auth/          # 认证相关
├── chat/          # 聊天功能
├── cache/         # 缓存管理
├── user/          # 用户管理
├── agent/         # 智能体管理
└── conversations/ # 对话管理
```

## 认证和授权

### JWT认证
- 所有需要认证的API都使用JWT Bearer Token
- Token通过 `Authorization: Bearer <token>` 头部传递
- 支持自动令牌刷新机制

### 权限控制
- 基于用户权限的细粒度访问控制
- 智能体级别的访问权限验证
- 自动权限检查装饰器

## 统一响应格式

所有API响应都遵循以下格式：

### 成功响应
```json
{
  "success": true,
  "data": {...},
  "message": "操作成功",
  "timestamp": 1752797158,
  "request_id": "c3233efa-26e0-4151-ae53-cac1a13c852e"
}
```

### 错误响应
```json
{
  "success": false,
  "error_code": "AUTHENTICATION_REQUIRED",
  "message": "需要身份验证",
  "timestamp": 1752797158,
  "request_id": "c3233efa-26e0-4151-ae53-cac1a13c852e"
}
```

### 分页响应
```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5
  },
  "message": "获取成功",
  "timestamp": 1752797158,
  "request_id": "c3233efa-26e0-4151-ae53-cac1a13c852e"
}
```

## API端点详情

### 认证端点

#### POST /api/v1/auth/login
用户登录

**请求体:**
```json
{
  "username": "string",
  "password": "string",
  "remember_me": false
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "user": {...},
    "tokens": {
      "access_token": "...",
      "refresh_token": "...",
      "expires_in": 3600
    },
    "session_info": {...}
  }
}
```

#### POST /api/v1/auth/refresh
刷新访问令牌

**请求体:**
```json
{
  "refresh_token": "string"
}
```

#### POST /api/v1/auth/logout
用户登出 (需要认证)

#### GET /api/v1/auth/me
获取当前用户信息 (需要认证)

### 聊天端点

#### GET /api/v1/chat/agents
获取用户可用智能体列表 (需要认证)

**查询参数:**
- `use_cache`: boolean (默认true)
- `search`: string
- `category`: string

#### GET /api/v1/chat/conversations
获取对话列表 (需要认证)

**查询参数:**
- `agent_id`: string
- `limit`: integer
- `use_cache`: boolean

#### POST /api/v1/chat/conversations
创建新对话 (需要认证)

#### POST /api/v1/chat/messages
发送聊天消息 (需要认证)

### 缓存管理端点

#### GET /api/v1/cache/health
缓存健康检查 (需要认证)

#### GET /api/v1/cache/stats
缓存统计信息 (需要认证)

#### POST /api/v1/cache/preload
预热缓存 (需要认证)

#### POST /api/v1/cache/refresh
刷新特定缓存 (需要认证)

#### DELETE /api/v1/cache/invalidate
清除缓存 (需要认证)

### 用户管理端点

#### GET /api/v1/user/permissions
获取用户权限信息 (需要认证)

### 智能体管理端点

#### GET /api/v1/agent/config
获取智能体配置 (需要认证)

### 系统端点

#### GET /api/v1/health
系统健康检查 (公开访问)

#### GET /api/v1/info
系统信息 (公开访问)

## 向后兼容性

为保持向后兼容，以下传统路径仍然可用：
- `/login` → `/api/v1/auth/login`
- `/api/conversations` → `/api/v1/chat/conversations`
- `/api/chat` → `/api/v1/chat/messages`
- `/api/agents` → `/api/v1/chat/agents`

## 错误处理

### 标准错误码
- `AUTHENTICATION_REQUIRED`: 需要身份验证
- `INVALID_CREDENTIALS`: 凭据无效
- `ACCESS_DENIED`: 访问被拒绝
- `INVALID_REQUEST`: 请求格式错误
- `VALIDATION_ERROR`: 参数验证失败
- `RATE_LIMITED`: 请求过于频繁
- `INTERNAL_ERROR`: 服务器内部错误
- `EXTERNAL_SERVICE_ERROR`: 外部服务错误

### HTTP状态码映射
- 200: 成功
- 400: 请求错误
- 401: 未授权
- 403: 禁止访问
- 404: 资源不存在
- 429: 频率限制
- 500: 服务器错误

## 请求验证

所有API端点都实现了严格的请求验证：
- Pydantic模型验证
- 参数类型检查
- 必需字段验证
- 敏感词过滤
- 文件上传验证

## 安全特性

- JWT令牌认证
- 权限细粒度控制
- 请求频率限制
- 敏感信息脱敏
- 安全头部设置
- CORS配置

## 性能优化

- Redis缓存支持
- 智能缓存失效
- 缓存预热机制
- 请求压缩
- 数据库连接池

## 监控和日志

- 结构化日志记录
- 请求ID追踪
- 性能指标收集
- 错误率统计
- 健康检查端点
