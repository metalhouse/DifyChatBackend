# Redis 配置指南

## 📋 概述

本项目支持主应用和聊天室系统使用同一个 Redis 服务器的不同数据库，实现数据完全隔离，避免相互干扰。

## 🔧 配置架构

### 双 Redis 数据库架构
```
Redis 服务器 (192.168.1.195:6379)
├── 数据库 0 (主应用)
│   ├── 用户会话数据
│   ├── API 缓存
│   ├── 临时数据存储
│   └── 认证令牌缓存
└── 数据库 1 (聊天室)
    ├── 在线用户列表
    ├── 聊天室状态
    ├── 消息队列
    └── WebSocket 会话管理
```

## ⚙️ 配置选项

### 基础配置 (.env 文件)
```bash
# 主应用 Redis 配置
REDIS_ENABLED=true
REDIS_HOST=192.168.1.195
REDIS_PORT=6379
REDIS_DB=0                    # 主应用使用数据库 0
REDIS_PASSWORD=               # 如果设置了密码
REDIS_DECODE_RESPONSES=true
REDIS_SOCKET_TIMEOUT=5
REDIS_MAX_CONNECTIONS=10

# 聊天室 Redis 配置
CHATROOM_REDIS_DB=1          # 聊天室使用数据库 1
```

### 高级配置 - 完全独立的 Redis 实例
如果需要使用完全独立的 Redis 服务器：

```bash
# 主应用 Redis
REDIS_HOST=192.168.1.195
REDIS_PORT=6379
REDIS_DB=0

# 聊天室专用 Redis 服务器
CHATROOM_REDIS_HOST=192.168.1.196
CHATROOM_REDIS_PORT=6380
CHATROOM_REDIS_DB=0
CHATROOM_REDIS_PASSWORD=chatroom_redis_pass
```

## 🚀 使用方式

### 在代码中获取 Redis 配置

```python
from config import get_redis_config, get_chatroom_redis_config

# 获取主应用 Redis 配置
main_redis_config = get_redis_config()
print(f"主应用Redis: {main_redis_config.host}:{main_redis_config.port}/{main_redis_config.db}")

# 获取聊天室 Redis 配置
chatroom_redis_config = get_chatroom_redis_config()
print(f"聊天室Redis: {chatroom_redis_config.host}:{chatroom_redis_config.port}/{chatroom_redis_config.db}")
```

### 创建 Redis 连接

```python
import redis
from config import get_redis_config, get_chatroom_redis_config

# 主应用 Redis 连接
main_config = get_redis_config()
main_redis = redis.Redis(
    host=main_config.host,
    port=main_config.port,
    db=main_config.db,
    password=main_config.password,
    decode_responses=main_config.decode_responses,
    socket_timeout=main_config.socket_timeout
)

# 聊天室 Redis 连接
chatroom_config = get_chatroom_redis_config()
chatroom_redis = redis.Redis(
    host=chatroom_config.host,
    port=chatroom_config.port,
    db=chatroom_config.db,
    password=chatroom_config.password,
    decode_responses=chatroom_config.decode_responses,
    socket_timeout=chatroom_config.socket_timeout
)
```

## 📊 数据使用规划

### 主应用 Redis (数据库 0)
| 数据类型 | 键前缀 | 示例 | 用途 |
|---------|--------|------|------|
| 用户会话 | `session:` | `session:user123` | JWT 会话管理 |
| API 缓存 | `api_cache:` | `api_cache:dify_response_hash` | Dify API 响应缓存 |
| 登录尝试 | `login_attempts:` | `login_attempts:192.168.1.100` | 防暴力破解 |
| 临时数据 | `temp:` | `temp:verification_code_123` | 验证码等临时数据 |

### 聊天室 Redis (数据库 1)
| 数据类型 | 键前缀 | 示例 | 用途 |
|---------|--------|------|------|
| 在线用户 | `online:` | `online:room_abc123` | 聊天室在线用户列表 |
| 用户状态 | `user_status:` | `user_status:user456` | 用户在线状态 |
| 消息队列 | `msg_queue:` | `msg_queue:room_abc123` | 消息分发队列 |
| Socket 会话 | `socket:` | `socket:connection_789` | WebSocket 连接管理 |

## 🔍 监控和调试

### 查看 Redis 使用情况
```bash
# 连接到主应用数据库
redis-cli -h 192.168.1.195 -p 6379 -n 0

# 连接到聊天室数据库
redis-cli -h 192.168.1.195 -p 6379 -n 1

# 查看数据库信息
INFO keyspace

# 查看特定前缀的键
KEYS session:*
KEYS online:*
```

### Python 调试代码
```python
import redis
from config import get_redis_config, get_chatroom_redis_config

def debug_redis_usage():
    """调试 Redis 使用情况"""
    main_config = get_redis_config()
    chatroom_config = get_chatroom_redis_config()
    
    main_redis = redis.Redis(**main_config.__dict__)
    chatroom_redis = redis.Redis(**chatroom_config.__dict__)
    
    print("主应用 Redis 键数量:", main_redis.dbsize())
    print("聊天室 Redis 键数量:", chatroom_redis.dbsize())
    
    # 显示键样例
    main_keys = main_redis.keys("*")[:5]  # 前5个键
    chatroom_keys = chatroom_redis.keys("*")[:5]  # 前5个键
    
    print("主应用键样例:", main_keys)
    print("聊天室键样例:", chatroom_keys)
```

## ⚠️ 注意事项

### 1. 数据库编号不要冲突
- 主应用固定使用数据库 0
- 聊天室固定使用数据库 1
- 如有其他服务，使用数据库 2、3 等

### 2. 密码配置一致性
- 如果 Redis 设置了密码，确保两个配置都正确设置
- 可以为不同数据库设置不同密码（如果使用 Redis ACL）

### 3. 连接池配置
- 根据并发需求调整 `REDIS_MAX_CONNECTIONS`
- 聊天室可能需要更多连接，可单独配置 `CHATROOM_REDIS_MAX_CONNECTIONS`

### 4. 性能优化建议
```bash
# 高并发环境推荐配置
REDIS_MAX_CONNECTIONS=20
CHATROOM_REDIS_MAX_CONNECTIONS=30
REDIS_SOCKET_TIMEOUT=3
REDIS_CONNECTION_POOL_TIMEOUT=10
```

## 🛠️ 故障排除

### 常见问题

1. **连接被拒绝**
   - 检查 Redis 服务是否启动
   - 验证 IP 地址和端口是否正确
   - 确认防火墙设置

2. **认证失败**
   - 检查密码配置是否正确
   - 验证 Redis 的 ACL 设置

3. **数据混乱**
   - 确认数据库编号配置正确
   - 检查键前缀是否有冲突

4. **性能问题**
   - 监控连接池使用情况
   - 调整超时时间设置
   - 考虑增加连接池大小

### 测试连接脚本
```bash
# 在项目根目录运行
python -c "
from config import get_redis_config, get_chatroom_redis_config
import redis

# 测试主应用连接
main_config = get_redis_config()
main_redis = redis.Redis(host=main_config.host, port=main_config.port, db=main_config.db)
print('主应用Redis连接:', main_redis.ping())

# 测试聊天室连接
chatroom_config = get_chatroom_redis_config()
chatroom_redis = redis.Redis(host=chatroom_config.host, port=chatroom_config.port, db=chatroom_config.db)
print('聊天室Redis连接:', chatroom_redis.ping())
"
```

---

**配置完成后，主应用和聊天室将使用同一 Redis 服务器的不同数据库，实现完全的数据隔离！** 🎉
