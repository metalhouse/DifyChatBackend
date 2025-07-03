# DifyChatBackend

本项目为 Python Flask 后端，适配 DifyChat 安卓客户端，统一中转 dify API，保障安全，支持会话、聊天、流式等多种能力。

## 快速开始
1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. 配置 .env：
   ```ini
   FLASK_ENV=development
   FLASK_DEBUG=1
   DIFY_BASE_URL=http://192.168.1.5/v1
   DIFY_API_KEY=你的dify后台API-Key
   ```
3. 启动服务：
   ```bash
   python app.py
   ```

## 主要接口
- `POST /api/login`：校验用户名和密码，返回用户信息（不再返回 dify_token，安全性更高）
- `GET /api/conversations`：获取会话列表，参数 user
- `POST /api/chat`：发送对话消息，支持 blocking/streaming 两种模式

所有接口均返回统一结构：
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
