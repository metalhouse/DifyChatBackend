# API响应格式规范

## 概述

本文档定义了DifyChatBackend API的统一响应格式和错误码系统，确保所有API接口返回一致的数据结构。

## 统一响应格式

### 基础响应结构

所有API接口都应返回以下统一格式：

```json
{
  "success": true,
  "code": 0,
  "message": "操作成功",
  "data": null,
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-07-18T10:30:00.000Z"
}
```

### 字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `success` | boolean | ✅ | 操作是否成功 |
| `code` | integer | ✅ | 状态码，0表示成功，非0表示错误 |
| `message` | string | ✅ | 操作结果描述信息 |
| `data` | any | ❌ | 响应数据，成功时包含具体数据，失败时可能包含错误详情 |
| `request_id` | string | ✅ | 请求唯一标识符，用于追踪和调试 |
| `timestamp` | string | ✅ | 响应时间戳（ISO 8601格式） |

## 成功响应示例

### 简单成功响应

```json
{
  "success": true,
  "code": 0,
  "message": "操作成功",
  "data": null,
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-07-18T10:30:00.000Z"
}
```

### 包含数据的成功响应

```json
{
  "success": true,
  "code": 0,
  "message": "获取用户信息成功",
  "data": {
    "user_id": "user123",
    "username": "张三",
    "email": "zhangsan@example.com",
    "created_at": "2025-01-01T00:00:00.000Z"
  },
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-07-18T10:30:00.000Z"
}
```

### 分页响应

```json
{
  "success": true,
  "code": 0,
  "message": "获取智能体列表成功",
  "data": {
    "items": [
      {
        "id": "agent1",
        "name": "ChatGPT助手",
        "description": "智能对话助手"
      },
      {
        "id": "agent2", 
        "name": "代码助手",
        "description": "编程辅助工具"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 50,
      "total_pages": 3,
      "has_next": true,
      "has_prev": false
    }
  },
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-07-18T10:30:00.000Z"
}
```

## 错误响应示例

### 客户端错误（4xxx）

```json
{
  "success": false,
  "code": 4002,
  "message": "缺少必需字段",
  "data": {
    "validation_errors": {
      "username": ["用户名不能为空"],
      "password": ["密码长度至少8位"]
    }
  },
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-07-18T10:30:00.000Z"
}
```

### 认证错误（401x）

```json
{
  "success": false,
  "code": 4012,
  "message": "访问令牌已过期",
  "data": null,
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-07-18T10:30:00.000Z"
}
```

### 权限错误（403x）

```json
{
  "success": false,
  "code": 4033,
  "message": "智能体访问被拒绝",
  "data": {
    "required_permission": "agent:read",
    "user_permissions": ["chat:read", "chat:write"]
  },
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-07-18T10:30:00.000Z"
}
```

### 服务器错误（5xxx）

```json
{
  "success": false,
  "code": 5031,
  "message": "Dify平台接口错误",
  "data": {
    "error_detail": "连接超时",
    "retry_after": 30
  },
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-07-18T10:30:00.000Z"
}
```

## 错误码定义

### 成功码
- **0**: 操作成功

### 客户端错误（4xxx）
- **4000**: 请求参数错误
- **4001**: JSON格式错误
- **4002**: 缺少必需字段
- **4003**: 字段值无效
- **4004**: 字段类型错误

### 认证错误（401x）
- **4010**: 未授权访问
- **4011**: 无效的访问令牌
- **4012**: 访问令牌已过期
- **4013**: 访问令牌已被撤销
- **4014**: 需要登录

### 权限错误（403x）
- **4030**: 权限不足
- **4031**: 访问被拒绝
- **4032**: 需要特定权限
- **4033**: 智能体访问被拒绝

### 资源错误（404x）
- **4040**: 资源不存在
- **4041**: 用户不存在
- **4042**: 智能体不存在
- **4043**: 对话不存在

### 冲突错误（409x）
- **4090**: 请求冲突
- **4091**: 用户已存在
- **4092**: 资源被锁定

### 验证错误（422x）
- **4220**: 无法处理的实体
- **4221**: 数据验证失败
- **4222**: 违反业务规则

### 限流错误（429x）
- **4290**: 请求过于频繁
- **4291**: 超过速率限制

### 服务器错误（5xxx）
- **5000**: 服务器内部错误
- **5003**: 服务暂时不可用
- **5010**: 数据库错误
- **5020**: 缓存服务错误
- **5030**: 外部API调用失败
- **5031**: Dify平台接口错误

## 请求ID追踪

### 请求ID生成规则
- 使用UUID v4格式：`xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`
- 客户端可通过`X-Request-ID`请求头传递自定义请求ID
- 如果客户端未提供，服务器自动生成

### 请求ID用途
- **调试追踪**: 通过请求ID快速定位特定请求的日志
- **重复请求检测**: 防止重复提交相同操作
- **性能监控**: 追踪请求的完整生命周期
- **错误排查**: 客户端可提供请求ID协助问题排查

## 分页设计

### 分页参数
- `page`: 页码，从1开始（默认值：1）
- `page_size`: 每页数量（默认值：20，最大值：100）

### 分页响应结构
```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

### 分页字段说明
- `page`: 当前页码
- `page_size`: 每页数量
- `total`: 总记录数
- `total_pages`: 总页数
- `has_next`: 是否有下一页
- `has_prev`: 是否有上一页

## 时间戳格式

所有时间戳使用ISO 8601格式，UTC时区：
- 格式：`YYYY-MM-DDTHH:mm:ss.sssZ`
- 示例：`2025-07-18T10:30:00.000Z`

## HTTP状态码映射

| 业务状态码范围 | HTTP状态码 | 说明 |
|---------------|-----------|------|
| 0 | 200 | 成功 |
| 4000-4099 | 400 | 客户端请求错误 |
| 4010-4019 | 401 | 认证失败 |
| 4030-4039 | 403 | 权限不足 |
| 4040-4049 | 404 | 资源不存在 |
| 4090-4099 | 409 | 请求冲突 |
| 4220-4229 | 422 | 无法处理的实体 |
| 4290-4299 | 429 | 请求过于频繁 |
| 5000-5999 | 500 | 服务器错误 |

## 使用示例

### Python代码示例

```python
from utils.response_builder import ResponseBuilder, ErrorCode

# 成功响应
response = ResponseBuilder.success(
    data={"user_id": "123", "username": "张三"},
    message="获取用户信息成功"
)

# 错误响应
response = ResponseBuilder.error(
    ErrorCode.USER_NOT_FOUND,
    message="用户不存在"
)

# 分页响应
response = ResponseBuilder.paginated(
    items=user_list,
    page=1,
    page_size=20,
    total=100,
    message="获取用户列表成功"
)

# 验证错误响应
response = ResponseBuilder.validation_error({
    "username": ["用户名不能为空"],
    "email": ["邮箱格式不正确"]
})
```

### Flask路由示例

```python
from flask import request
from utils.response_builder import ResponseBuilder, RequestIdManager

@app.route('/api/users/<user_id>')
def get_user(user_id):
    request_id = RequestIdManager.ensure_request_id(request.headers)
    
    try:
        user = user_service.get_user(user_id)
        if not user:
            return ResponseBuilder.not_found("用户", request_id).to_dict()
        
        return ResponseBuilder.success(
            data=user,
            message="获取用户信息成功",
            request_id=request_id
        ).to_dict()
    
    except Exception as e:
        return ResponseBuilder.internal_error(
            message="获取用户信息失败",
            request_id=request_id
        ).to_dict()
```

## 最佳实践

### 1. 错误信息国际化
- 错误消息应支持多语言
- 使用错误码进行客户端错误处理逻辑
- 错误消息应具有一致的格式和风格

### 2. 数据字段命名
- 使用snake_case命名风格
- 字段名应具有明确的含义
- 避免使用缩写，优先使用完整单词

### 3. 敏感信息处理
- 错误响应中不应包含敏感信息
- 生产环境下应隐藏详细的错误堆栈信息
- 使用请求ID进行问题追踪，避免暴露内部信息

### 4. 缓存策略
- 成功响应可以缓存，错误响应通常不缓存
- 分页响应的缓存策略需要考虑数据时效性
- 请求ID可以用于缓存键的一部分

### 5. 版本兼容性
- 新增字段向后兼容
- 废弃字段应有明确的迁移计划
- 重大变更应提供API版本管理

## 验证工具

可以使用以下JSON Schema验证响应格式：

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["success", "code", "message", "request_id", "timestamp"],
  "properties": {
    "success": {"type": "boolean"},
    "code": {"type": "integer"},
    "message": {"type": "string"},
    "data": {},
    "request_id": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```
