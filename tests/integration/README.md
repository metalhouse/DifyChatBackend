# 集成测试

本目录包含DifyChatBackend项目的集成测试文件。

## 📁 测试文件说明

### API集成测试
- `test_api_debug.py` - API路由调试和集成测试
- `test_dify_direct.py` - Dify API直接调用测试
- `test_dify_conversations.py` - Dify对话API集成测试
- `test_real_chat.py` - 真实聊天功能集成测试

### 基础设施集成测试
- `test_redis_connection.py` - Redis连接和基础功能测试
- `test_redis_with_external.py` - 外部Redis服务集成测试

## 🚀 运行测试

### 前置条件
1. **启动Redis服务** (如果测试需要):
   ```bash
   # Windows (如果安装了Redis)
   redis-server
   
   # 或使用Docker
   docker run -d -p 6379:6379 redis:alpine
   ```

2. **配置环境变量**:
   ```bash
   # 设置Dify API密钥(如果需要真实API测试)
   set DIFY_API_KEY=your_api_key_here
   set DIFY_BASE_URL=https://api.dify.ai/v1
   ```

### 运行测试
```bash
cd d:\ChatDify_Codes\DifyChatBackend

# 单个集成测试
python tests/integration/test_redis_connection.py

# 运行所有集成测试
python -m pytest tests/integration/ -v

# 运行特定类型的测试
python -m pytest tests/integration/test_dify_* -v
```

## 📊 测试类型

### 🔌 连接测试
- Redis连接和健康检查
- Dify API连接验证
- 网络超时和重试机制

### 🔄 数据流测试
- 端到端API调用流程
- 缓存读写一致性
- 实际数据处理验证

### 🚦 错误场景测试
- 服务不可用时的降级
- 网络异常处理
- 认证失败恢复

## ⚠️ 注意事项

1. **网络依赖**: 部分测试需要网络连接
2. **服务依赖**: Redis和Dify服务需要可访问
3. **API配额**: 真实API测试可能消耗API配额
4. **数据安全**: 不要在测试中使用生产数据

## 🔧 故障排查

### Redis连接问题
```bash
# 检查Redis是否运行
redis-cli ping

# 检查端口是否开放
netstat -an | findstr 6379
```

### Dify API问题
```bash
# 测试API连接
curl -H "Authorization: Bearer your_key" https://api.dify.ai/v1/apps
```

## 🔗 相关文档

- [单元测试](../unit/README.md)
- [测试配置](../../CONFIG.md)
- [API文档](../../API_DOCUMENTATION.md)
