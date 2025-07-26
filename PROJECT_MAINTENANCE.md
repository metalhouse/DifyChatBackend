# 项目维护指南

## 🚫 禁止创建的文件类型

为了保持项目整洁，请避免在根目录创建以下类型的文件：

### 临时测试文件
- `test_*.py` - 临时测试脚本
- `*_test.py` - 临时测试脚本  
- `debug_*.py` - 调试脚本
- `demo_*.py` - 演示脚本
- `verify_*.py` - 验证脚本
- `analyze_*.py` - 分析脚本
- `fix_*.py` - 修复脚本
- `diagnose_*.py` - 诊断脚本
- `quick_*.py` - 快速测试脚本
- `simple_*.py` - 简单测试脚本
- `run_*.py` - 运行脚本

### 临时文件
- `temp_*.*` - 临时文件
- `tmp_*.*` - 临时文件
- `*.tmp` - 临时文件
- `*.temp` - 临时文件
- 空文件（大小为0的文件）

## ✅ 正确的做法

1. **测试文件** → 放在 `tests/` 目录下
2. **调试脚本** → 放在 `archived_files/` 目录下  
3. **临时文件** → 使用系统临时目录或立即删除

## 🧹 清理工具

### 自动清理脚本
运行清理脚本来删除不需要的文件：
```powershell
.\cleanup.ps1
```

### Git 钩子保护
项目已配置 Git pre-commit 钩子，会自动检查并阻止提交：
- 空文件
- 临时测试文件

### .gitignore 保护
`.gitignore` 文件已配置忽略常见的临时文件模式。

## 📁 目录结构规范

```
DifyChatBackend/
├── api/                 # API路由
├── auth/               # 认证模块  
├── data/               # 数据文件
├── middleware/         # 中间件
├── models/            # 数据模型
├── services/          # 业务服务
├── tests/             # ✅ 测试文件放这里
├── utils/             # 工具函数
├── archived_files/    # ✅ 临时文件放这里
└── logs/              # 日志文件
```

## 🚨 如果意外创建了这些文件

1. **立即删除**：
   ```powershell
   Remove-Item "不需要的文件.py" -Force
   ```

2. **运行清理脚本**：
   ```powershell
   .\cleanup.ps1
   ```

3. **检查Git状态**：
   ```powershell
   git status
   ```

## 🔄 定期维护

建议每周运行一次清理脚本：
```powershell
# 每周清理命令
.\cleanup.ps1
git status
```

这样可以确保项目始终保持整洁状态。
