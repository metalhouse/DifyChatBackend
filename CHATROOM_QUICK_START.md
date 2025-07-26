# 聊天室系统快速部署指南

## 🚀 快速启动

### 环境配置
```bash
# 1. 环境变量配置
MARIADB_ENABLED=true
MARIADB_HOST=192.168.1.10
MARIADB_PORT=3307
MARIADB_DATABASE=chatroom_db
MARIADB_USERNAME=root
MARIADB_PASSWORD=your_password
CHATROOM_ENABLED=true

# 2. JWT配置
JWT_SECRET_KEY=your_jwt_secret_key
SECRET_KEY=your_app_secret_key

# 3. Redis配置（聊天室使用DB 1）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1
```

### 启动服务
```bash
python app.py
```

## 🔑 核心用户凭据
- **管理员用户**: metalhouse
- **密码**: Iwhyi3589
- **权限**: 所有聊天室管理权限

## 📡 API快速测试

### 1. 登录获取Token
```bash
curl -X POST http://127.0.0.1:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"metalhouse","password":"Iwhyi3589"}'
```

### 2. 创建聊天室
```bash
curl -X POST http://127.0.0.1:5000/api/v1/chatroom/create \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试室","description":"测试用聊天室","is_public":true,"max_users":50}'
```

### 3. 获取聊天室详情
```bash
curl -X GET http://127.0.0.1:5000/api/v1/chatroom/CHATROOM_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## ⚠️ 重要提醒

### 数据库注意事项
1. **首次启动**: 系统会自动检查表是否存在，避免重复初始化
2. **状态字段**: 删除操作使用 'disabled' 状态，不是 'inactive'
3. **连接管理**: 使用连接池，注意连接释放

### JWT认证注意事项
1. **密钥一致性**: 确保生成和验证使用相同的JWT密钥
2. **Token过期**: Access Token 1小时有效期
3. **权限验证**: metalhouse自动获得admin权限

### 常见问题解决
1. **401错误**: 检查JWT_SECRET_KEY配置
2. **数据库错误**: 检查MariaDB连接和表结构
3. **权限不足**: 确认用户角色和权限配置

## 📊 系统状态检查

### 健康检查
```bash
# 检查应用状态
curl http://127.0.0.1:5000/health

# 检查数据库连接
python -c "from chatroom.mariadb_config import initialize_mariadb_for_chatroom; print('✅' if initialize_mariadb_for_chatroom() else '❌')"
```

### 日志监控
```bash
# 查看实时日志
tail -f logs/app.log

# 查看错误日志
grep ERROR logs/app.log
```

## 🎯 核心功能验证清单

- [ ] 用户登录成功，获得JWT token
- [ ] 创建聊天室成功，返回聊天室ID
- [ ] 获取聊天室详情，显示成员信息
- [ ] 更新聊天室信息成功
- [ ] 删除聊天室成功（软删除）
- [ ] 权限验证正常工作

---

**快速支持**: 遇到问题请查看 `CHATROOM_SYSTEM_TESTING_REPORT.md` 详细文档
