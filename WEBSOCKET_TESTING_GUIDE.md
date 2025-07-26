# WebSocket 测试指南

## 快速检查服务状态

### PowerShell 脚本检查
```powershell
.\websocket_check.ps1
```
这个脚本会检查：
- HTTP API服务状态 (端口5000)
- WebSocket服务状态 (端口6000)
- 端口监听状态

## 重要说明

### 426错误是正常的！
当你看到"426 Upgrade Required"错误时，**这是正常的**，表示：
- WebSocket服务正在运行
- 端口6000只接受WebSocket连接
- HTTP请求被正确拒绝并要求升级到WebSocket协议

### 错误的测试方法 ❌
```bash
# 这些会返回426错误 - 但服务是正常的！
curl http://127.0.0.1:6000/
Invoke-WebRequest -Uri "http://127.0.0.1:6000/"
```

### 正确的测试方法 ✅

#### 1. 使用HTML测试工具 (推荐)
打开 `websocket_diagnostic.html` 在浏览器中测试

#### 2. 使用浏览器WebSocket API
```javascript
const socket = new WebSocket('ws://127.0.0.1:6000/ws/chatroom?token=YOUR_TOKEN');
socket.onopen = () => console.log('连接成功');
```

#### 3. 使用wscat命令行工具
```bash
wscat -c "ws://127.0.0.1:6000/ws/chatroom?token=YOUR_TOKEN"
```

## 获取Token流程

1. 先通过HTTP API登录获取token：
```bash
curl -X POST http://127.0.0.1:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

2. 使用返回的access_token连接WebSocket

## 服务架构

- **端口5000**: HTTP REST API (登录、用户管理等)
- **端口6000**: WebSocket服务 (实时聊天)

两个服务独立运行，前端需要先从HTTP API获取token，然后连接WebSocket服务。
