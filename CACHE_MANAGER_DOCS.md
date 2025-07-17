# Redis缓存管理器使用文档

## 概述

Redis缓存管理器提供了统一的缓存接口，支持连接池、健康检查、缓存穿透保护等功能。

## 功能特性

### 核心功能
- ✅ Redis连接池管理
- ✅ 自动序列化/反序列化
- ✅ 健康检查和监控
- ✅ 缓存统计信息
- ✅ 缓存key命名规范
- ✅ 批量操作支持
- ✅ 分布式锁机制
- ✅ 缓存穿透保护
- ✅ 优雅降级（Redis不可用时）

### 安全特性
- ✅ 长key自动哈希
- ✅ 连接超时处理
- ✅ 异常安全处理
- ✅ 资源自动清理

## 配置说明

### 环境变量配置

```bash
# Redis基本配置
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_password

# 连接池配置
REDIS_MAX_CONNECTIONS=10
REDIS_SOCKET_TIMEOUT=5
REDIS_DECODE_RESPONSES=true
```

### 配置类说明

```python
@dataclass
class RedisConfig:
    enabled: bool = False              # 是否启用Redis
    host: str = 'localhost'           # Redis主机地址
    port: int = 6379                  # Redis端口
    db: int = 0                       # 数据库编号
    password: Optional[str] = None     # 密码
    decode_responses: bool = True      # 自动解码响应
    socket_timeout: int = 5           # 连接超时时间
    connection_pool_max_connections: int = 10  # 连接池大小
```

## 使用示例

### 1. 初始化缓存管理器

```python
from config import create_config
from utils.cache_manager import init_cache_manager, get_cache_manager

# 初始化配置
config = create_config()

# 初始化缓存管理器
cache_manager = init_cache_manager(config)

# 在应用中获取缓存管理器
cache = get_cache_manager()
```

### 2. 基本操作

```python
# 设置缓存
cache.set("user:123", {"name": "张三", "age": 25}, ttl=3600)

# 获取缓存
user_data = cache.get("user:123")

# 删除缓存
cache.delete("user:123")

# 检查是否存在
exists = cache.exists("user:123")

# 设置过期时间
cache.expire("user:123", 1800)

# 获取剩余生存时间
ttl = cache.ttl("user:123")
```

### 3. 批量操作

```python
# 批量设置
data = {
    "user:1": {"name": "用户1"},
    "user:2": {"name": "用户2"},
    "user:3": {"name": "用户3"}
}
cache.mset(data, ttl=3600)

# 批量获取
keys = ["user:1", "user:2", "user:3"]
values = cache.mget(keys)
```

### 4. 使用标准缓存Key

```python
from utils.cache_manager import CacheKeyGenerator

# 对话列表缓存key
conv_key = CacheKeyGenerator.conversation_list("user123")
# 结果: "conversations:user:user123"

# 智能体列表缓存key
agent_key = CacheKeyGenerator.agent_list("user123")
# 结果: "agents:user:user123"

# 用户权限缓存key
perm_key = CacheKeyGenerator.user_permissions("user123")
# 结果: "permissions:user:user123"

# 智能体访问权限缓存key
access_key = CacheKeyGenerator.agent_access("user123", "agent456")
# 结果: "access:user:user123:agent:agent456"

# 自定义key
custom_key = CacheKeyGenerator.custom("myapp", "feature", "123")
# 结果: "myapp:feature:123"
```

### 5. 计数器功能

```python
# 递增计数器
count = cache.increment("api_calls:user123", amount=1, ttl=3600)

# 速率限制
rate_key = CacheKeyGenerator.rate_limit("user123", "chat_api")
current_count = cache.increment(rate_key, ttl=60)
if current_count > 100:  # 每分钟最多100次
    raise RateLimitExceeded()
```

### 6. 分布式锁

```python
# 获取带锁的缓存
value, lock_acquired = cache.get_with_lock("critical_resource", lock_timeout=10)
if lock_acquired:
    try:
        # 执行需要锁保护的操作
        result = expensive_operation()
        cache.set("critical_resource", result, ttl=300)
    finally:
        # 释放锁
        cache.release_lock("critical_resource")
```

### 7. 使用缓存装饰器

```python
from utils.cache_manager import cached, CacheKeyGenerator

@cached(
    key_func=lambda user_id: CacheKeyGenerator.conversation_list(user_id),
    ttl=300  # 5分钟
)
def get_user_conversations(user_id: str):
    # 这个函数的结果会被自动缓存
    return expensive_database_query(user_id)

# 使用
conversations = get_user_conversations("user123")
```

### 8. 健康检查和监控

```python
# 健康检查
health_status = cache.health_check()
print(health_status)
# {
#     "status": "healthy",
#     "ping_time_ms": 1.23,
#     "redis_version": "7.0.0",
#     "connected_clients": 2,
#     "used_memory": "1.2M",
#     "stats": {
#         "hits": 150,
#         "misses": 30,
#         "hit_rate": 83.33
#     },
#     "enabled": True
# }

# 获取详细信息
info = cache.get_info()

# 获取统计信息
stats = cache.stats
print(f"缓存命中率: {stats.hit_rate:.2%}")
print(f"总操作数: {stats.total_operations}")
```

## 缓存Key命名规范

### 命名模式
- 使用冒号(:)分隔不同层级
- 使用小写字母和下划线
- 包含资源类型和标识符

### 标准Key格式
```
# 用户相关
conversations:user:{user_id}           # 对话列表
agents:user:{user_id}                  # 智能体列表
permissions:user:{user_id}             # 用户权限
session:user:{user_id}:device:{device_id}  # 用户会话

# 访问控制
access:user:{user_id}:agent:{agent_id}  # 智能体访问权限

# 速率限制
ratelimit:user:{user_id}:endpoint:{endpoint}  # 速率限制

# 锁
lock:{original_key}                    # 分布式锁

# 哈希key（长key处理）
hash:{md5_hash}                        # 哈希后的key
```

## 最佳实践

### 1. TTL设置建议
```python
# 不同类型数据的建议TTL
TTL_SETTINGS = {
    "conversations": 300,      # 5分钟 - 对话列表
    "agents": 3600,           # 1小时 - 智能体列表
    "permissions": 1800,      # 30分钟 - 用户权限
    "sessions": 7200,         # 2小时 - 用户会话
    "rate_limits": 60,        # 1分钟 - 速率限制
    "temporary": 300,         # 5分钟 - 临时数据
}
```

### 2. 错误处理
```python
# 缓存应该对业务逻辑透明
def get_user_data(user_id: str):
    # 先尝试缓存
    cached_data = cache.get(f"user:{user_id}")
    if cached_data:
        return cached_data
    
    # 缓存未命中，从数据库获取
    data = database.get_user(user_id)
    
    # 设置缓存（如果缓存可用）
    cache.set(f"user:{user_id}", data, ttl=1800)
    
    return data
```

### 3. 缓存穿透保护
```python
def get_expensive_data(key: str):
    # 使用分布式锁防止缓存穿透
    value, lock_acquired = cache.get_with_lock(f"data:{key}")
    
    if value is not None:
        return value
    
    if lock_acquired:
        try:
            # 只有获得锁的请求才执行昂贵操作
            result = expensive_operation(key)
            cache.set(f"data:{key}", result, ttl=600)
            return result
        finally:
            cache.release_lock(f"data:{key}")
    else:
        # 没有获得锁的请求等待并重试
        time.sleep(0.1)
        return cache.get(f"data:{key}")
```

### 4. 缓存失效策略
```python
def update_user_data(user_id: str, data: dict):
    # 更新数据库
    database.update_user(user_id, data)
    
    # 删除相关缓存
    cache.delete(f"user:{user_id}")
    cache.delete(CacheKeyGenerator.user_permissions(user_id))
    
    # 删除用户相关的所有缓存
    cache.delete_pattern(f"*:user:{user_id}*")
```

## 性能优化

### 1. 批量操作
```python
# 好的做法：使用批量操作
user_ids = ["user1", "user2", "user3"]
keys = [f"user:{uid}" for uid in user_ids]
user_data = cache.mget(keys)

# 避免：循环单独获取
# for uid in user_ids:
#     data = cache.get(f"user:{uid}")  # 避免这样做
```

### 2. 合理的数据结构
```python
# 存储用户的所有相关数据在一个key中
user_cache_data = {
    "profile": user_profile,
    "permissions": user_permissions,
    "preferences": user_preferences
}
cache.set(f"user_all:{user_id}", user_cache_data, ttl=1800)
```

### 3. 预热缓存
```python
def warmup_cache():
    """应用启动时预热常用缓存"""
    # 预热活跃用户的权限数据
    active_users = get_active_users()
    for user_id in active_users:
        permissions = get_user_permissions(user_id)
        cache.set(
            CacheKeyGenerator.user_permissions(user_id),
            permissions,
            ttl=1800
        )
```

## 监控和调试

### 1. 日志记录
缓存管理器会自动记录关键操作的日志：
- DEBUG级别：缓存命中/设置/删除
- ERROR级别：连接失败、操作异常
- WARNING级别：清空缓存等危险操作

### 2. 统计信息
```python
# 定期检查缓存性能
stats = cache.stats
if stats.hit_rate < 0.8:  # 命中率低于80%
    logger.warning(f"缓存命中率较低: {stats.hit_rate:.2%}")

# 检查错误率
if stats.errors > stats.total_operations * 0.05:  # 错误率超过5%
    logger.error("缓存错误率过高，请检查Redis连接")
```

### 3. 健康检查接口
```python
# 在Flask应用中添加健康检查端点
@app.route('/health/cache')
def cache_health():
    health_status = cache.health_check()
    status_code = 200 if health_status.get("status") == "healthy" else 503
    return jsonify(health_status), status_code
```

## 故障排除

### 常见问题

1. **Redis连接失败**
   - 检查Redis服务是否运行
   - 验证连接参数（host、port、password）
   - 检查网络连接

2. **缓存命中率低**
   - 检查TTL设置是否合理
   - 验证缓存key的一致性
   - 分析业务逻辑是否适合缓存

3. **内存使用过高**
   - 检查是否有大对象被缓存
   - 设置合理的TTL
   - 使用`get_info()`监控内存使用

4. **性能问题**
   - 使用批量操作代替循环操作
   - 避免缓存过大的对象
   - 检查Redis服务器性能

### 调试技巧

```python
# 启用详细日志
import logging
logging.getLogger('utils.cache_manager').setLevel(logging.DEBUG)

# 检查特定key的信息
key = "user:123"
print(f"Key存在: {cache.exists(key)}")
print(f"TTL: {cache.ttl(key)}秒")
print(f"值: {cache.get(key)}")

# 监控缓存统计
stats = cache.stats
print(f"命中: {stats.hits}, 错过: {stats.misses}, 命中率: {stats.hit_rate:.2%}")
```

## 升级和维护

### 版本兼容性
- Redis >= 5.0.0
- Python >= 3.8
- redis-py >= 5.0.0

### 数据迁移
在升级Redis版本或更改配置时：
1. 导出重要缓存数据
2. 更新配置
3. 重启服务
4. 验证缓存功能正常

### 定期维护
- 监控Redis内存使用
- 清理过期key
- 检查连接池状态
- 更新Redis和redis-py版本
