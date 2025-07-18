# 示例和演示脚本

本目录包含DifyChatBackend项目的演示脚本和示例代码。

## 📁 文件说明

### 缓存系统演示
- `demo_cache_manager.py` - Redis缓存管理器功能演示
- `demo_cache_system.py` - 缓存系统综合演示

### 认证系统演示  
- `demo_jwt_auth.py` - JWT认证系统演示脚本
- `demo_login_api.py` - 登录接口功能演示脚本

## 🚀 如何使用

1. **确保虚拟环境已激活**:
   ```bash
   cd d:\ChatDify_Codes\DifyChatBackend
   .venv\Scripts\activate
   ```

2. **运行演示脚本**:
   ```bash
   python docs/examples/demo_cache_manager.py
   python docs/examples/demo_jwt_auth.py
   ```

## 📋 注意事项

- 这些脚本仅用于演示和学习目的
- 运行前请确保相关服务（如Redis）已启动
- 部分脚本可能需要配置环境变量

## 🔗 相关文档

- [项目架构文档](../README.md)
- [API文档](../API_DOCUMENTATION.md)
- [配置指南](../CONFIG.md)
