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
```json
{
  "success": true/false,
  "message": "提示或错误信息",
  "data": { ... } // 仅 success 为 true 时返回
}
```

## 用户数据存储与加密
- 用户名、密码存储在 users.json 文件中（已移除 dify_token 字段）。
- 密码使用 SHA256 加密存储。
- 登录时自动对密码加密校验。

## 示例 users.json
```json
{
  "user1": {
    "password": "flkdf86jnmmhslk3mjs776jsbtqqllm15fee63a12f659aae9"
  }
}
```

## 适配说明
- 安卓端登录时 POST 请求本服务，获取用户信息后可直接调用 /api/chat 进行 AI 聊天。
- 所有 dify 相关请求由后端统一带 API-Key 转发，前端永远拿不到真正的 dify token，安全性高。
- streaming 模式下安卓端需用支持 SSE 的方式处理响应。

## 更多说明
- 详细接口文档见 API_DOC.md
- 可根据实际需求扩展更多 dify API 封装。

## License
Metalhouse

## 管理后台功能说明

本项目内置管理后台（/admin_app.py + /admin/templates/index.html），支持如下功能：

- 统一风格的侧边栏+内容区布局，基于 Bootstrap 5。
- 智能体管理：
  - 查看、添加、编辑、删除智能体（API Key 脱敏显示，可一键显示/隐藏）。
- 用户-智能体分配：
  - 支持为每个用户分配多个智能体，分配/移除操作直观。
- 用户管理：
  - 仅 admin 用户可登录后台。
  - 查看所有用户，支持新增、编辑、禁用、删除用户。
  - 用户管理区已集成到 index.html 单页，无需跳转，内容区切换流畅。
  - “状态”列采用蓝绿色块（#2fb380）+白色字体，风格统一。
- 权限控制：所有后台操作需登录且仅限 admin 用户。
- 退出登录：侧边栏一键退出。
- 路由与页面跳转：所有主功能均为单页切换，无 404 问题。
- 代码结构清晰，支持后续扩展（如弹窗编辑、AJAX、无刷新等）。

> 后台入口：访问 `/` 登录，登录后进入主后台页面。

如需二次开发或体验优化，可参考 `admin_app.py` 及 `index.html` 进一步扩展。
