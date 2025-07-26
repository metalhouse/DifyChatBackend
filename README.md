# DifyChatBackend - 现代化智能对话后端服务 v2.1.4

> 🚀 **企业级智能对话API服务** - 基于Flask的现代化后端，为DCApp安卓应用提供安全、高性能的Dify API中转服务

## ✨ 项目特色

- 🔐 **JWT认证系统** - 现代化的无状态认证机制
- ⚡ **Redis缓存** - 高性能缓存，大幅提升响应速度
- 🌊 **SSE流式响应** - 实时对话体验，支持大量并发连接
- 🛡️ **权限控制** - 细粒度的RBAC权限管理
- 🎛️ **功能配置** - 智能体功能开关和配置管理
- 📊 **监控统计** - 完善的监控和统计系统
- 🔧 **标准化API** - 统一的响应格式和错误处理
- 🆕 **分层信息披露** - 基础信息公开，敏感信息需认证
- 🆕 **单资源详情** - 支持获取单个智能体和对话的详细信息
- 🆕 **实时系统统计** - 为管理员提供系统运行状态监控
- 🆕 **智能体欢迎语** - 支持自定义智能体欢迎信息
- 🔥 **聊天室系统** - 完整的实时聊天室功能 (v2.1.4)
- ⚡ **WebSocket支持** - 原生WebSocket实时通信 (v2.1.4)

## 🔥 v2.1.4 版本更新 - WebSocket实时通信

### 🌐 原生WebSocket支持
- **完整WebSocket服务器**: 基于websockets 15.0.1的高性能实现
- **JWT认证集成**: WebSocket连接支持JWT Token认证
- **实时消息推送**: 支持聊天室实时消息广播
- **连接管理**: 智能连接管理和自动重连机制
- **标准化协议**: 遵循WebSocket RFC 6455标准

### 📡 WebSocket API
- **连接端点**: `ws://localhost:6000/ws/chatroom`
- **认证方式**: URL参数或消息认证
- **支持消息**:
  - `get_chatrooms` - 获取聊天室列表
  - `join_chatroom` - 加入聊天室
  - `leave_chatroom` - 离开聊天室
  - `send_message` - 发送消息
  - `get_messages` - 获取历史消息

### 🛠️ 技术实现
- **双端口架构**: HTTP API(5000) + WebSocket(6000)
- **异步处理**: 完全异步的消息处理机制
- **错误处理**: 完善的连接错误处理和恢复
- **兼容性**: 支持现代浏览器和移动端WebSocket

### 🔧 聊天室系统增强
- **完整CRUD操作**: 创建、查询、更新、删除聊天室
- **权限管理**: 基于角色的聊天室访问控制
- **成员管理**: 支持聊天室成员的添加和管理
- **MariaDB集成**: 聊天室数据持久化存储
- **双Redis架构**: 主应用DB0，聊天室DB1，完全数据隔离
- **智能初始化**: 避免重复数据库初始化，优化启动速度

### � HTTP API端点
```
POST   /api/v1/chatroom/create       - 创建聊天室
GET    /api/v1/chatroom/list         - 获取聊天室列表  
GET    /api/v1/chatroom/{id}         - 获取聊天室详情
PUT    /api/v1/chatroom/{id}         - 更新聊天室信息
DELETE /api/v1/chatroom/{id}         - 删除聊天室
GET    /api/v1/chatroom/{id}/members - 获取聊天室成员
POST   /api/v1/chatroom/{id}/members - 添加聊天室成员
```

### 🌐 WebSocket端点
```
ws://localhost:6000/ws/chatroom?token=JWT_TOKEN
```

### 🏗️ 系统架构增强
- **多协议支持**: HTTP REST API + WebSocket实时通信
- **双数据库**: SQLite(主应用) + MariaDB(聊天室)
- **双缓存**: Redis DB0(主应用) + Redis DB1(聊天室)
- **双端口**: 5000(HTTP) + 6000(WebSocket)  
- **权限统一**: 聊天室权限集成到现有RBAC系统
- **配置优化**: 环境变量统一管理数据库和缓存配置

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

# 聊天室系统配置 (v2.1.3)
CHATROOM_ENABLED=true
MARIADB_ENABLED=true
MARIADB_HOST=192.168.1.10
MARIADB_PORT=3307
MARIADB_DATABASE=chatroom_db
MARIADB_USERNAME=root
MARIADB_PASSWORD=your_password
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

## 🆕 新增功能端点

### 单资源详情端点
```bash
# 获取单个智能体详情
GET /api/v1/agents/{id}

# 获取单个对话详情  
GET /api/v1/conversations/{id}?include_messages=true
```

### 系统管理端点
```bash
# 获取系统统计（需要管理员权限）
GET /api/v1/stats?time_range=24h&include_details=true

# 获取公开系统信息
GET /api/v1/info/public

# 获取认证用户系统信息
GET /api/v1/info
```

### 端点特性
- ✅ **权限控制** - 根据用户权限返回相应数据
- ✅ **缓存优化** - 智能缓存策略，提升性能
- ✅ **参数灵活** - 支持多种查询参数自定义返回内容
- ✅ **错误处理** - 完善的错误处理和状态码

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
- [WebSocket前端指南](WEBSOCKET_FRONTEND_GUIDE.md) - WebSocket集成完整指南
- [WebSocket测试指南](WEBSOCKET_TESTING_GUIDE.md) - 快速测试WebSocket连接
- [项目架构文档](PROJECT_ARCHITECTURE.md) - 系统架构说明
- [配置说明](CONFIG.md) - 详细的配置参数说明
- [项目完成总结](PROJECT_COMPLETION_SUMMARY.md) - 项目优化成果
- [Postman使用指南](POSTMAN_USAGE_GUIDE.md) - API测试工具使用

## 🧪 测试工具

### WebSocket连接测试
- **websocket_diagnostic.html** - 完整的WebSocket服务诊断工具 (推荐)
- **websocket_test.html** - 基础WebSocket连接测试
- **websocket_check.ps1** - PowerShell状态检查脚本

### 快速服务检查
```powershell
# Windows PowerShell
.\websocket_check.ps1
```

**重要**: 如果看到"426 Upgrade Required"错误，这是**正常的**！说明WebSocket服务正在运行。

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

---

## 🏠 聊天室系统文档 (v2.1.3)

### 📚 相关文档
- **[聊天室系统测试报告](CHATROOM_SYSTEM_TESTING_REPORT.md)** - 完整的功能测试结果和技术细节
- **[聊天室快速部署指南](CHATROOM_QUICK_START.md)** - 快速启动和API测试指南  
- **[聊天室问题排查指南](CHATROOM_TROUBLESHOOTING.md)** - 常见问题解决方案

### 🚀 聊天室快速启动
```bash
# 1. 启用聊天室系统
export CHATROOM_ENABLED=true
export MARIADB_ENABLED=true

# 2. 配置数据库
export MARIADB_HOST=192.168.1.10
export MARIADB_PORT=3307
export MARIADB_DATABASE=chatroom_db

# 3. 启动服务
python app.py

# 4. 健康检查
python health_check.py
```

### 🔑 管理员账户
- **用户名**: metalhouse
- **密码**: Iwhyi3589  
- **权限**: 聊天室管理员 (自动分配)

### 📡 聊天室API示例
```bash
# 登录获取Token
curl -X POST http://127.0.0.1:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"metalhouse","password":"Iwhyi3589"}'

# 创建聊天室
curl -X POST http://127.0.0.1:5000/api/v1/chatroom/create \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试室","description":"测试聊天室","is_public":true}'

# 获取聊天室详情
curl -X GET http://127.0.0.1:5000/api/v1/chatroom/CHATROOM_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 🏗️ 架构特点
- **双数据库架构**: SQLite(主应用) + MariaDB(聊天室)
- **双Redis缓存**: DB0(主应用) + DB1(聊天室)  
- **智能初始化**: 自动检查表存在性，避免重复初始化
- **权限集成**: 聊天室权限融入现有RBAC系统
- **软删除机制**: 数据安全保护

---

## 🙏 致谢

感谢以下开源项目：
- [Flask](https://flask.palletsprojects.com/) - Web框架
- [Redis](https://redis.io/) - 缓存数据库
- [PyJWT](https://pyjwt.readthedocs.io/) - JWT实现
- [Pydantic](https://pydantic-docs.helpmanual.io/) - 数据验证
- [MariaDB](https://mariadb.org/) - 关系型数据库
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL工具包

---

## 📋 更新日志

### v2.1.3 (2025-07-26) - 聊天室系统
- 🆕 **完整聊天室功能** - CRUD操作、权限管理、成员管理
- 🆕 **MariaDB集成** - 聊天室数据持久化存储
- 🆕 **双Redis架构** - 主应用与聊天室数据完全隔离
- 🔧 **数据库优化** - 智能初始化，避免重复SQL执行
- 🔧 **JWT修复** - 修复聊天室API的JWT密钥验证问题
- 📚 **完整文档** - 测试报告、部署指南、故障排除

### v2.1.2 (2025-07-20) - 智能体欢迎语
- 🆕 **智能体欢迎语功能** - 支持自定义欢迎信息
- 🔧 **API响应优化** - 前端友好的数据格式

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
