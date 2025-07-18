# 🔒 安全指南

## 📋 安全检查清单

### ✅ 环境配置安全
- [ ] 所有敏感配置都在`.env`文件中，已添加到`.gitignore`
- [ ] 生产环境使用强密码和随机密钥
- [ ] API密钥不在代码中硬编码
- [ ] 数据库连接字符串不包含在版本控制中

### ✅ 认证和授权
- [ ] JWT密钥足够复杂（建议32字符以上）
- [ ] 用户密码使用PBKDF2加密存储
- [ ] 实施权限控制和访问限制
- [ ] 定期轮换API密钥

### ✅ 数据保护
- [ ] 敏感数据不记录在日志中
- [ ] 用户数据加密存储
- [ ] 定期备份重要配置文件
- [ ] 清理测试数据和临时文件

## 🚨 敏感文件清单

以下文件包含敏感信息，**不应提交到版本控制**：

### 环境配置
- `.env` - 开发环境配置
- `.env.dev` - 开发环境配置  
- `.env.prod` - 生产环境配置
- `.env.redis*` - Redis配置

### 数据文件
- `users.json` - 用户账户和密码
- `agents.json` - 智能体配置和API密钥
- `agent_features.json` - 功能配置

### 日志文件
- `*.log` - 所有日志文件
- `logs/` - 日志目录

## 🛡️ 安全最佳实践

### 1. 环境配置
```bash
# 开发环境
cp .env.example .env
# 编辑.env文件，设置安全的密钥

# 生产环境
# 使用强随机密钥
JWT_SECRET_KEY=$(openssl rand -base64 32)
```

### 2. 用户管理
```bash
# 创建管理员用户时使用强密码
# 密码要求：至少8位，包含大小写字母和数字
```

### 3. API密钥管理
- 定期轮换Dify API密钥
- 不同环境使用不同的API密钥
- 监控API密钥使用情况

### 4. 部署安全
```bash
# 生产环境部署前检查
# 1. 确保所有敏感文件在.gitignore中
# 2. 验证环境变量正确设置
# 3. 检查文件权限设置
chmod 600 .env
chmod 600 users.json
chmod 600 agents.json
```

## 🔍 安全审计

### 定期检查项目
```bash
# 检查是否有敏感信息泄露
git log --all --full-history -- .env
git log --all --full-history -- users.json
git log --all --full-history -- agents.json

# 清理Git历史中的敏感信息（如需要）
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' \
  --prune-empty --tag-name-filter cat -- --all
```

### 监控和报警
- 监控异常登录活动
- 设置API调用频率限制
- 记录安全相关事件

## 📞 安全事件响应

如果发现安全问题：

1. **立即行动**
   - 更换所有受影响的密钥
   - 撤销可能泄露的API令牌
   - 检查访问日志

2. **评估影响**
   - 确定数据泄露范围
   - 分析攻击向量
   - 评估系统完整性

3. **恢复和改进**
   - 修复安全漏洞
   - 更新安全策略
   - 加强监控措施

## 🔗 相关资源

- [Flask安全文档](https://flask.palletsprojects.com/en/2.0.x/security/)
- [JWT最佳实践](https://auth0.com/blog/a-look-at-the-latest-draft-for-jwt-bcp/)
- [OWASP Web应用安全](https://owasp.org/www-project-top-ten/)

---

> ⚠️ **重要提醒**：定期审查和更新安全配置，确保项目始终遵循最新的安全最佳实践。
