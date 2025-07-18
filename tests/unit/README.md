# 单元测试

本目录包含DifyChatBackend项目的单元测试文件。

## 📁 测试文件说明

### 核心架构测试
- `test_architecture.py` - 项目架构和模块化测试
- `test_config.py` - 配置管理系统测试

### 认证系统测试
- `test_jwt_acceptance.py` - JWT认证功能验收测试
- `test_jwt_auth.py` - JWT认证系统完整测试

### 缓存系统测试
- `test_agent_cache.py` - 智能体缓存功能测试
- `test_cache_validation.py` - 缓存验证测试
- `test_conversation_cache_validation.py` - 对话缓存测试

### API系统测试
- `test_api_standard.py` - API标准化测试
- `test_request_validator.py` - 请求验证系统测试

## 🚀 运行测试

### 单个测试文件
```bash
cd d:\ChatDify_Codes\DifyChatBackend
python -m pytest tests/unit/test_config.py -v
```

### 运行所有单元测试
```bash
python -m pytest tests/unit/ -v
```

### 带覆盖率报告
```bash
python -m pytest tests/unit/ --cov=. --cov-report=html
```

## 📊 测试覆盖范围

- **配置管理**: ✅ 6个测试用例全部通过
- **JWT认证**: ✅ 44项测试通过，成功率100%
- **缓存系统**: ✅ 9/9测试通过，功能验证完成
- **API标准化**: ✅ 请求验证和响应格式测试完成

## 📋 测试准则

1. 每个核心功能模块都应有对应的单元测试
2. 测试覆盖率应保持在80%以上
3. 所有测试应该是独立的，不依赖外部服务
4. 使用Mock对象模拟外部依赖

## 🔗 相关文档

- [集成测试](../integration/README.md)
- [测试运行器](../test_runner.py)
- [项目文档](../../README.md)
