# 错误码说明文档

## 概述

本文档详细说明了DifyChatBackend API中使用的所有错误码，包括错误码分类、使用场景、处理建议等信息。

## 错误码体系设计

### 分类原则

错误码采用4位数字分类体系：

- **0**: 成功状态
- **4xxx**: 客户端错误（对应HTTP 4xx状态码）
- **5xxx**: 服务器错误（对应HTTP 5xx状态码）

### 细分规则

每个主分类下按功能模块进一步细分：

- **40xx**: 通用客户端错误
- **401x**: 认证相关错误
- **403x**: 权限相关错误
- **404x**: 资源不存在错误
- **409x**: 冲突相关错误
- **422x**: 验证相关错误
- **429x**: 限流相关错误
- **50xx**: 通用服务器错误
- **501x**: 数据库相关错误
- **502x**: 缓存服务相关错误
- **503x**: 外部API相关错误

## 详细错误码列表

### 成功状态码

| 错误码 | 消息 | HTTP状态码 | 说明 | 处理建议 |
|--------|------|------------|------|----------|
| 0 | 操作成功 | 200 | 请求成功完成 | 继续正常处理 |

### 客户端错误 (4xxx)

#### 通用请求错误 (400x)

| 错误码 | 消息 | HTTP状态码 | 说明 | 处理建议 |
|--------|------|------------|------|----------|
| 4000 | 请求参数错误 | 400 | 请求参数格式或内容有误 | 检查请求参数格式和内容 |
| 4001 | JSON格式错误 | 400 | 请求体JSON格式不正确 | 检查JSON语法是否正确 |
| 4002 | 缺少必需字段 | 400 | 请求中缺少必需的参数 | 补充缺少的必需参数 |
| 4003 | 字段值无效 | 400 | 某个字段的值不在允许范围内 | 检查字段值是否符合要求 |
| 4004 | 字段类型错误 | 400 | 字段类型与预期不符 | 确保字段类型正确 |

**使用场景示例**:
```python
# 4000 - 请求参数错误
GET /api/users?page=abc  # page参数应为数字

# 4001 - JSON格式错误
POST /api/users
Content-Type: application/json
{"name": "张三"  # 缺少闭合括号

# 4002 - 缺少必需字段
POST /api/users
{"name": "张三"}  # 缺少必需的email字段

# 4003 - 字段值无效
POST /api/users
{"name": "张三", "role": "invalid_role"}  # role值不在允许列表中

# 4004 - 字段类型错误
POST /api/users
{"name": "张三", "age": "25"}  # age应为数字类型
```

#### 认证错误 (401x)

| 错误码 | 消息 | HTTP状态码 | 说明 | 处理建议 |
|--------|------|------------|------|----------|
| 4010 | 未授权访问 | 401 | 缺少认证信息 | 提供有效的认证凭据 |
| 4011 | 无效的访问令牌 | 401 | 访问令牌格式错误或无效 | 使用有效的访问令牌 |
| 4012 | 访问令牌已过期 | 401 | 访问令牌已超过有效期 | 刷新访问令牌 |
| 4013 | 访问令牌已被撤销 | 401 | 访问令牌已被主动撤销 | 重新登录获取新令牌 |
| 4014 | 需要登录 | 401 | 需要用户登录才能访问 | 跳转到登录页面 |

**使用场景示例**:
```python
# 4010 - 未授权访问
GET /api/protected-resource
# 请求头中没有Authorization字段

# 4011 - 无效的访问令牌
GET /api/protected-resource
Authorization: Bearer invalid_token_format

# 4012 - 访问令牌已过期
GET /api/protected-resource
Authorization: Bearer eyJ0eXAiOiJKV1Q...  # 令牌已过期

# 4013 - 访问令牌已被撤销
GET /api/protected-resource
Authorization: Bearer eyJ0eXAiOiJKV1Q...  # 令牌已被撤销

# 4014 - 需要登录
GET /api/user/profile  # 访问需要登录的用户信息
```

#### 权限错误 (403x)

| 错误码 | 消息 | HTTP状态码 | 说明 | 处理建议 |
|--------|------|------------|------|----------|
| 4030 | 权限不足 | 403 | 用户权限不足以执行操作 | 申请相应权限或联系管理员 |
| 4031 | 访问被拒绝 | 403 | 访问被系统拒绝 | 确认用户角色和权限配置 |
| 4032 | 需要特定权限 | 403 | 需要特定的权限才能访问 | 获取对应的权限 |
| 4033 | 智能体访问被拒绝 | 403 | 对特定智能体的访问被拒绝 | 确认智能体访问权限 |

**使用场景示例**:
```python
# 4030 - 权限不足
DELETE /api/users/123  # 普通用户尝试删除其他用户

# 4031 - 访问被拒绝
GET /api/admin/settings  # 非管理员用户访问管理功能

# 4032 - 需要特定权限
POST /api/agents  # 用户没有创建智能体的权限

# 4033 - 智能体访问被拒绝
GET /api/agents/private_agent_id  # 访问私有智能体
```

#### 资源不存在错误 (404x)

| 错误码 | 消息 | HTTP状态码 | 说明 | 处理建议 |
|--------|------|------------|------|----------|
| 4040 | 资源不存在 | 404 | 请求的资源不存在 | 确认资源ID是否正确 |
| 4041 | 用户不存在 | 404 | 指定的用户不存在 | 确认用户ID是否正确 |
| 4042 | 智能体不存在 | 404 | 指定的智能体不存在 | 确认智能体ID是否正确 |
| 4043 | 对话不存在 | 404 | 指定的对话不存在 | 确认对话ID是否正确 |

**使用场景示例**:
```python
# 4040 - 资源不存在
GET /api/nonexistent-endpoint

# 4041 - 用户不存在
GET /api/users/999999  # 用户ID不存在

# 4042 - 智能体不存在
GET /api/agents/invalid_agent_id

# 4043 - 对话不存在
GET /api/conversations/invalid_conversation_id
```

#### 冲突错误 (409x)

| 错误码 | 消息 | HTTP状态码 | 说明 | 处理建议 |
|--------|------|------------|------|----------|
| 4090 | 请求冲突 | 409 | 请求与当前状态冲突 | 检查资源当前状态 |
| 4091 | 用户已存在 | 409 | 尝试创建已存在的用户 | 使用不同的用户名或邮箱 |
| 4092 | 资源被锁定 | 409 | 资源正在被其他操作使用 | 等待资源释放后重试 |

**使用场景示例**:
```python
# 4090 - 请求冲突
PUT /api/users/123
{"status": "active"}  # 用户已经是活跃状态

# 4091 - 用户已存在
POST /api/users
{"username": "existing_user", "email": "existing@example.com"}

# 4092 - 资源被锁定
DELETE /api/agents/agent123  # 智能体正在被其他用户使用
```

#### 验证错误 (422x)

| 错误码 | 消息 | HTTP状态码 | 说明 | 处理建议 |
|--------|------|------------|------|----------|
| 4220 | 无法处理的实体 | 422 | 请求格式正确但无法处理 | 检查请求内容的语义正确性 |
| 4221 | 数据验证失败 | 422 | 数据未通过验证规则 | 根据验证错误修正数据 |
| 4222 | 违反业务规则 | 422 | 请求违反了业务逻辑规则 | 确保请求符合业务规则 |

**使用场景示例**:
```python
# 4220 - 无法处理的实体
POST /api/users
{"email": "invalid-email-format"}  # 邮箱格式错误

# 4221 - 数据验证失败
POST /api/users
{"password": "123"}  # 密码长度不足

# 4222 - 违反业务规则
POST /api/conversations
{"agent_id": "agent123", "user_id": "user456"}  # 用户没有权限使用该智能体
```

#### 限流错误 (429x)

| 错误码 | 消息 | HTTP状态码 | 说明 | 处理建议 |
|--------|------|------------|------|----------|
| 4290 | 请求过于频繁 | 429 | 超出了API调用频率限制 | 减少请求频率，稍后重试 |
| 4291 | 超过速率限制 | 429 | 超过了用户级别的速率限制 | 等待限制重置后重试 |

**使用场景示例**:
```python
# 4290 - 请求过于频繁
# 用户在1分钟内发送了超过100个请求

# 4291 - 超过速率限制
# 用户今日API调用次数已达上限
```

### 服务器错误 (5xxx)

#### 通用服务器错误 (500x)

| 错误码 | 消息 | HTTP状态码 | 说明 | 处理建议 |
|--------|------|------------|------|----------|
| 5000 | 服务器内部错误 | 500 | 服务器发生未预期的错误 | 联系技术支持，提供请求ID |
| 5003 | 服务暂时不可用 | 503 | 服务正在维护或暂时不可用 | 稍后重试 |

#### 数据库错误 (501x)

| 错误码 | 消息 | HTTP状态码 | 说明 | 处理建议 |
|--------|------|------------|------|----------|
| 5010 | 数据库错误 | 500 | 数据库操作失败 | 稍后重试，持续失败请联系技术支持 |

#### 缓存服务错误 (502x)

| 错误码 | 消息 | HTTP状态码 | 说明 | 处理建议 |
|--------|------|------------|------|----------|
| 5020 | 缓存服务错误 | 500 | 缓存服务不可用或操作失败 | 功能可能降级，稍后重试 |

#### 外部API错误 (503x)

| 错误码 | 消息 | HTTP状态码 | 说明 | 处理建议 |
|--------|------|------------|------|----------|
| 5030 | 外部API调用失败 | 500 | 调用外部API服务失败 | 检查外部服务状态，稍后重试 |
| 5031 | Dify平台接口错误 | 500 | Dify平台API调用失败 | 检查Dify服务状态，稍后重试 |

## 错误响应格式

### 标准错误响应

```json
{
  "success": false,
  "code": 4041,
  "message": "用户不存在",
  "data": null,
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-07-18T10:30:00.000Z"
}
```

### 包含详细信息的错误响应

```json
{
  "success": false,
  "code": 4221,
  "message": "数据验证失败",
  "data": {
    "validation_errors": {
      "username": ["用户名不能为空", "用户名长度必须在3-20字符之间"],
      "email": ["邮箱格式不正确"],
      "password": ["密码长度至少8位", "密码必须包含字母和数字"]
    }
  },
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-07-18T10:30:00.000Z"
}
```

### 限流错误响应

```json
{
  "success": false,
  "code": 4290,
  "message": "请求过于频繁",
  "data": {
    "retry_after": 60,
    "limit": 100,
    "remaining": 0,
    "reset_time": "2025-07-18T10:31:00.000Z"
  },
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-07-18T10:30:00.000Z"
}
```

## 客户端处理指南

### 错误分类处理

```python
def handle_api_response(response):
    data = response.json()
    code = data.get('code', 0)
    
    if code == 0:
        # 成功处理
        return data['data']
    
    elif 4000 <= code <= 4999:
        # 客户端错误
        if 4010 <= code <= 4019:
            # 认证错误 - 重新登录
            redirect_to_login()
        elif 4030 <= code <= 4039:
            # 权限错误 - 显示权限不足提示
            show_permission_denied_message()
        elif 4040 <= code <= 4049:
            # 资源不存在 - 显示不存在提示
            show_not_found_message()
        elif code == 4290 or code == 4291:
            # 限流错误 - 延迟重试
            retry_after = data.get('data', {}).get('retry_after', 60)
            schedule_retry(retry_after)
        else:
            # 其他客户端错误 - 显示错误信息
            show_error_message(data['message'])
    
    elif 5000 <= code <= 5999:
        # 服务器错误 - 可以重试
        if code == 5003:
            # 服务不可用 - 显示维护提示
            show_maintenance_message()
        else:
            # 其他服务器错误 - 稍后重试
            schedule_retry(30)  # 30秒后重试
```

### 重试策略

```python
import time
import random

def retry_with_backoff(func, max_retries=3, base_delay=1):
    """指数退避重试策略"""
    for attempt in range(max_retries):
        try:
            return func()
        except ServerError as e:
            if attempt == max_retries - 1:
                raise e
            
            # 计算退避时间
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

### 错误日志记录

```python
import logging

def log_api_error(response, request_info):
    """记录API错误日志"""
    data = response.json()
    
    logger.error(
        f"API Error: {data['code']} - {data['message']}, "
        f"Request ID: {data['request_id']}, "
        f"URL: {request_info['url']}, "
        f"Method: {request_info['method']}, "
        f"User: {request_info.get('user_id', 'anonymous')}"
    )
```

## 监控和告警

### 错误码统计指标

建议监控以下错误码指标：

1. **高频错误码**: 监控出现频率最高的错误码
2. **认证错误率**: 4010-4019 错误码的比例
3. **权限错误率**: 4030-4039 错误码的比例  
4. **服务器错误率**: 5xxx 错误码的比例
5. **限流触发频率**: 4290-4291 错误码的频率

### 告警阈值建议

| 错误类型 | 告警阈值 | 处理优先级 |
|----------|----------|------------|
| 服务器错误率 > 1% | 立即告警 | 高 |
| 认证错误率 > 10% | 5分钟内告警 | 中 |
| 限流触发频率异常高 | 10分钟内告警 | 中 |
| 特定错误码激增 | 15分钟内告警 | 低 |

### 错误码趋势分析

```python
# 示例：错误码统计查询
def get_error_code_stats(start_time, end_time):
    """获取指定时间范围内的错误码统计"""
    query = """
    SELECT 
        error_code,
        COUNT(*) as count,
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
    FROM api_logs 
    WHERE timestamp BETWEEN %s AND %s 
        AND error_code != 0
    GROUP BY error_code 
    ORDER BY count DESC
    """
    return execute_query(query, (start_time, end_time))
```

## 版本兼容性

### 错误码演进规则

1. **新增错误码**: 可以随时新增，不影响现有客户端
2. **修改错误码**: 需要版本化处理，保持向后兼容
3. **删除错误码**: 需要提前通知，逐步废弃

### 废弃错误码处理

```python
# 示例：废弃错误码的处理
DEPRECATED_ERROR_CODES = {
    4001: {
        'replacement': 4000,
        'deprecated_since': '2025-01-01',
        'removal_date': '2025-07-01'
    }
}

def map_deprecated_error_code(code):
    """将废弃的错误码映射到新的错误码"""
    if code in DEPRECATED_ERROR_CODES:
        deprecated_info = DEPRECATED_ERROR_CODES[code]
        logger.warning(
            f"Error code {code} is deprecated since {deprecated_info['deprecated_since']}, "
            f"will be removed on {deprecated_info['removal_date']}, "
            f"use {deprecated_info['replacement']} instead"
        )
        return deprecated_info['replacement']
    return code
```

## 常见问题

### Q: 如何选择合适的错误码？

A: 选择错误码时应考虑：
1. 错误的根本原因（客户端 vs 服务器）
2. 错误的具体类型（认证、权限、验证等）
3. 客户端需要采取的处理动作
4. 错误的严重程度和紧急程度

### Q: 什么时候使用自定义错误信息？

A: 在以下情况下使用自定义错误信息：
1. 需要提供更具体的错误描述
2. 需要指导用户如何修正错误
3. 需要包含动态的错误详情
4. 需要支持多语言错误信息

### Q: 如何处理同时出现多个错误的情况？

A: 建议的处理策略：
1. 优先返回最严重的错误
2. 在data字段中包含所有错误详情
3. 使用4221（数据验证失败）作为统一错误码
4. 提供结构化的错误详情列表

### Q: 错误码是否需要国际化？

A: 错误码本身不需要国际化，但错误消息应该支持国际化：
- 错误码作为程序处理的依据，保持不变
- 错误消息根据客户端语言设置返回对应语言版本
- 可以在响应中同时提供错误码和本地化消息
