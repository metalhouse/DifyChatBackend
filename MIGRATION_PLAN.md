# 数据文件迁移计划

## 当前状况分析

### 文件位置现状
- `agents.json` - 根目录 (包含敏感API密钥)
- `agent_features.json` - 根目录 (功能配置)
- 应该迁移到: `data/` 目录

### 代码依赖分析

#### ✅ 已支持data目录的模块
- `config.py` - 通过环境变量 `AGENTS_FILE` 支持自定义路径，默认为 `data/agents.json`

#### ❌ 需要修改的模块
- `admin/admin_app.py` - 硬编码 `../agents.json`
- `dify_api.py` - 硬编码 `agents.json`
- `models/agent_features.py` - 硬编码 `agent_features.json`

## 迁移方案

### 阶段1: 更新代码支持data目录
1. 修改硬编码路径的模块
2. 统一使用config.py的配置
3. 添加向后兼容性

### 阶段2: 创建data目录结构
```
data/
├── users.json
├── agents.json
└── agent_features.json
```

### 阶段3: 安全迁移
1. 创建数据目录
2. 移动现有文件
3. 更新环境配置
4. 验证功能正常

## 风险评估

### 高风险点
- admin后台可能无法加载智能体配置
- API服务可能无法获取智能体信息
- 功能配置丢失

### 缓解措施
- 保留原文件作为备份
- 分步骤验证每个模块
- 提供回滚方案

## 实施步骤

### 1. 代码更新 (安全，可回滚)
- 修改admin_app.py使用config
- 修改dify_api.py使用config  
- 修改agent_features.py支持配置路径

### 2. 创建迁移脚本
- 自动创建data目录
- 安全移动文件
- 验证数据完整性

### 3. 环境配置
- 更新.env文件指向data目录
- 更新docker-compose配置

### 4. 验证测试
- 测试admin后台功能
- 测试API服务
- 测试功能配置加载
