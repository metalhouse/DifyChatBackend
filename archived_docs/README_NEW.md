# DifyChatBackend - 现代化智能对话后端服务

> 🚀 **企业级智能对话API服务** - 基于Flask的现代化后端，为DCApp安卓应用提供安全、高性能的Dify API中转服务

## ✨ 项目特色

- 🔐 **JWT认证系统** - 现代化的无状态认证机制
- ⚡ **Redis缓存** - 高性能缓存，大幅提升响应速度
- 🌊 **SSE流式响应** - 实时对话体验，支持大量并发连接
- 🛡️ **权限控制** - 细粒度的RBAC权限管理
- 🎛️ **功能配置** - 智能体功能开关和配置管理
- 📊 **监控统计** - 完善的监控和统计系统
- 🔧 **标准化API** - 统一的响应格式和错误处理

## 🚀 快速开始

### 环境要求
- Python 3.11+
- Redis 6.0+
- Flask 2.0+

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd DifyChatBackend
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/macOS
   source .venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境**
   ```bash
   cp .env.example .env
   # 编辑.env文件配置必要参数
   ```

5. **启动服务**
   ```bash
   python app.py
   ```

## ⚙️ 环境配置

### 基础配置 (.env)
```ini
# 应用配置
FLASK_ENV=development
FLASK_DEBUG=1
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# JWT认证配置
JWT_SECRET_KEY=your-super-secret-key-here
JWT_EXPIRE_HOURS=24
JWT_REFRESH_DAYS=7

# Redis配置
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Dify API配置
DIFY_BASE_URL=http://your-dify-server/v1
DIFY_API_KEY=your-dify-api-key
DIFY_TIMEOUT=30

# 缓存配置
CACHE_DEFAULT_TIMEOUT=300
CONVERSATION_CACHE_TIMEOUT=300
AGENT_CACHE_TIMEOUT=3600
USER_PERMISSION_CACHE_TIMEOUT=1800

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

## 🏗️ 系统架构

### 核心模块
```
DifyChatBackend/
├── api/                    # API路由层
│   ├── auth_routes.py      # 认证相关API
│   ├── chat_routes.py      # 聊天相关API
│   ├── cache_routes.py     # 缓存管理API
│   └── agent_config_routes.py # 智能体配置API
├── auth/                   # 认证模块
│   ├── auth_manager.py     # JWT认证管理
│   ├── decorators.py       # 认证装饰器
│   └── utils.py            # 认证工具
├── services/               # 业务服务层
│   ├── dify_service.py     # Dify API服务
│   ├── user_service.py     # 用户管理服务
│   └── streaming_service.py # 流式响应服务
├── models/                 # 数据模型
│   ├── agent_features.py   # 智能体功能模型
│   ├── request_models.py   # 请求验证模型
│   └── user_config.py      # 用户配置模型
├── middleware/             # 中间件
│   └── feature_check.py    # 功能检查中间件
├── utils/                  # 工具模块
│   ├── cache_manager.py    # 缓存管理器
│   ├── response_builder.py # 响应构建器
│   └── request_validator.py # 请求验证器
└── admin/                  # 管理后台
    └── admin_app.py        # 管理界面
```

## 🔐 认证系统

### JWT认证流程
1. **用户登录** - 验证用户名密码，返回JWT令牌
2. **令牌验证** - 每次请求自动验证JWT令牌
3. **自动刷新** - 令牌即将过期时自动刷新
4. **安全登出** - 支持令牌撤销和黑名单

### 使用示例
```python
# 登录获取令牌
POST /api/v1/auth/login
{
    "username": "user123",
    "password": "password123"
}

# 响应
{
    "success": true,
    "data": {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "expires_in": 86400,
        "user": {
            "username": "user123",
            "permissions": ["send_messages", "view_conversations"]
        }
    }
}
```

## ⚡ 缓存系统

### 缓存策略
- **对话列表缓存** - 5分钟，发送消息时自动失效
- **智能体列表缓存** - 1小时，配置变更时失效
- **用户权限缓存** - 30分钟，权限变更时失效
- **API响应缓存** - 根据数据特性动态设置

### 缓存管理API
```bash
# 获取缓存统计
GET /api/v1/cache/stats

# 清除指定缓存
DELETE /api/v1/cache/invalidate?pattern=user:*

# 刷新缓存
POST /api/v1/cache/refresh
```

## 🌊 流式响应

### SSE流式聊天
支持Server-Sent Events实时流式响应，提供更好的用户体验：

```javascript
// 客户端示例
const eventSource = new EventSource('/api/v1/chat/messages?stream=true');

eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('收到消息:', data);
};

eventSource.addEventListener('completion', function(event) {
    console.log('对话完成');
    eventSource.close();
});
```

### 流式监控
```bash
# 获取流式连接统计
GET /api/v1/streaming/stats

# 重置统计信息
POST /api/v1/streaming/reset
```

## 🎛️ 智能体功能配置

### 支持的功能类型
- **问题建议** (suggested_questions) - 智能问题推荐
- **文件上传** (file_upload) - 文件上传支持
- **文字转语音** (text_to_audio) - TTS功能
- **语音转文字** (audio_to_text) - STT功能
- **消息反馈** (message_feedback) - 点赞/点踩
- **对话重命名** (conversation_rename) - 自动/手动重命名

### 配置管理
```bash
# 获取智能体功能配置
GET /api/v1/agent/features/{agent_id}

# 更新功能配置
PUT /api/v1/agent/features/{agent_id}
{
    "features": {
        "suggested_questions": {"enabled": true},
        "file_upload": {"enabled": false},
        "text_to_audio": {"enabled": true}
    }
}
```

## 📡 主要API接口

### 认证相关
```bash
POST /api/v1/auth/login        # 用户登录
POST /api/v1/auth/refresh      # 刷新令牌
POST /api/v1/auth/logout       # 用户登出
GET  /api/v1/auth/me          # 获取当前用户信息
```

### 聊天相关
```bash
GET  /api/v1/chat/agents           # 获取智能体列表
GET  /api/v1/chat/conversations    # 获取对话列表
POST /api/v1/chat/messages         # 发送消息(支持流式)
POST /api/v1/chat/conversations    # 创建新对话
DELETE /api/v1/conversations/{id}  # 删除对话
POST /api/v1/conversations/{id}/name # 重命名对话
```

### 功能相关
```bash
POST /api/v1/messages/{id}/feedbacks  # 消息反馈
GET  /api/v1/messages/{id}/suggested  # 获取建议问题
POST /api/v1/audio-to-text            # 语音转文字
POST /api/v1/text-to-audio            # 文字转语音
```

### 管理相关
```bash
GET /api/v1/cache/stats         # 缓存统计
GET /api/v1/streaming/stats     # 流式统计
GET /api/v1/agent/features/{id} # 智能体功能配置
```

### 统一响应格式
```json
{
  "success": true,
  "code": 200,
  "message": "操作成功",
  "timestamp": 1642694400,
  "data": {...},
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "has_next": true
  },
  "request_id": "uuid-string"
}
```

## 🛡️ 权限系统

### 权限类型
- `send_messages` - 发送消息
- `view_conversations` - 查看对话
- `create_conversations` - 创建对话
- `delete_conversations` - 删除对话
- `edit_conversations` - 编辑对话
- `access_agents` - 访问智能体
- `manage_agents` - 管理智能体
- `view_app_info` - 查看应用信息
- `system_admin` - 系统管理

### 使用装饰器保护API
```python
@require_auth()
@require_permissions(['send_messages'])
@require_agent_feature(AgentFeatureType.TEXT_TO_AUDIO)
def api_text_to_audio():
    # API实现
```

## 📊 监控与统计

### 系统健康检查
```bash
GET /health           # 基础健康检查
GET /api/v1/health    # 详细健康状态
```

### 性能监控
- **响应时间监控** - API响应时间统计
- **缓存命中率** - 缓存效果评估
- **错误率监控** - 4xx/5xx错误率追踪
- **并发量监控** - 实时并发请求数
- **业务监控** - 用户活跃度、功能使用情况

## 🔧 用户数据与加密

### 密码安全
- 采用PBKDF2算法进行密码哈希
- 随机盐值增强安全性
- 支持密码强度验证
- 登录失败次数限制

### 数据存储
```json
// users.json示例
{
  "user1": {
    "password_hash": "pbkdf2:sha256:...",
    "permissions": ["send_messages", "view_conversations"],
    "created_at": "2024-01-01T00:00:00Z",
    "last_login": "2024-01-15T10:30:00Z",
    "status": "active"
  }
}
```

## 🏢 管理后台

### 功能特色
- **统一风格** - 基于Bootstrap 5的现代化界面
- **智能体管理** - 添加、编辑、删除智能体，API Key脱敏显示
- **用户管理** - 用户CRUD操作，权限分配
- **功能配置** - 智能体功能开关配置
- **监控面板** - 实时系统状态和统计

### 访问方式
```bash
# 管理后台入口
http://localhost:5000/admin

# 登录凭据（仅admin用户）
用户名: admin
密码: [配置的管理员密码]
```

## 🚢 部署指南

### Docker部署
```bash
# 构建镜像
docker build -t difychat-backend .

# 运行容器
docker run -d \
  --name difychat-backend \
  -p 5000:5000 \
  -e REDIS_HOST=redis \
  -e DIFY_BASE_URL=http://dify-server/v1 \
  -e DIFY_API_KEY=your-api-key \
  difychat-backend
```

### 生产环境配置
```bash
# 使用Gunicorn
pip install gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app

# 使用Nginx反向代理
# 配置HTTPS和负载均衡
```

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
python -m pytest tests/

# 运行特定模块测试
python test_task_5_1.py  # 智能体功能配置测试
python test_task_5_2.py  # 用户服务测试
python test_task_5_3.py  # 流式响应测试
```

### API测试
```bash
# 使用Postman集合
# 导入 DifyChatBackend_API_v1_Collection.postman_collection.json

# 或使用curl测试
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test_user", "password": "password"}'
```

## 📈 性能优化

### 缓存优化
- **多层缓存架构** - 内存 + Redis双重缓存
- **智能缓存失效** - 数据变更时自动失效相关缓存
- **缓存预热** - 系统启动时预加载热点数据
- **缓存穿透防护** - 空结果缓存避免重复查询

### 数据库优化
- **连接池** - 数据库连接复用
- **批量操作** - 减少数据库交互次数
- **索引优化** - 为查询字段建立适当索引

## 🔍 故障排查

### 常见问题

**1. Redis连接失败**
```bash
# 检查Redis服务状态
redis-cli ping

# 检查配置
echo $REDIS_HOST
```

**2. JWT令牌验证失败**
```bash
# 检查密钥配置
echo $JWT_SECRET_KEY

# 检查令牌格式
curl -H "Authorization: Bearer your-token" /api/v1/auth/me
```

**3. Dify API调用失败**
```bash
# 检查网络连接
curl $DIFY_BASE_URL/health

# 检查API密钥
curl -H "Authorization: Bearer $DIFY_API_KEY" $DIFY_BASE_URL/info
```

### 日志查看
```bash
# 实时日志
tail -f logs/app.log

# 错误日志过滤
grep "ERROR" logs/app.log

# 特定用户日志
grep "user123" logs/app.log
```

## 📚 文档链接

- [API详细文档](API_DOCUMENTATION.md) - 完整的API接口说明
- [配置说明](CONFIG.md) - 详细的配置参数说明
- [项目完成总结](PROJECT_COMPLETION_SUMMARY.md) - 项目优化成果
- [Postman使用指南](POSTMAN_USAGE_GUIDE.md) - API测试工具使用

## 🤝 贡献指南

1. Fork本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 👨‍💻 作者

**Metalhouse** - [GitHub](https://github.com/metalhouse)

## 🙏 致谢

感谢以下开源项目：
- [Flask](https://flask.palletsprojects.com/) - Web框架
- [Redis](https://redis.io/) - 缓存数据库
- [PyJWT](https://pyjwt.readthedocs.io/) - JWT实现
- [Pydantic](https://pydantic-docs.helpmanual.io/) - 数据验证

---

## 📋 更新日志

### v2.0.0 (2025-07-18) - 全面优化版本
- ✅ **JWT认证系统** - 现代化无状态认证
- ✅ **Redis缓存** - 高性能缓存机制
- ✅ **SSE流式响应** - 实时对话体验
- ✅ **权限控制** - 细粒度RBAC权限
- ✅ **功能配置** - 智能体功能开关
- ✅ **API标准化** - 统一响应格式
- ✅ **监控统计** - 完善的监控体系
- ✅ **管理后台** - 现代化管理界面

### v1.0.0 (2024-12-01) - 初始版本
- 基础Flask应用
- 简单用户认证
- Dify API中转
- 基础聊天功能

---

> 🚀 **DifyChatBackend** 现已达到企业级标准，可直接投入生产使用！
