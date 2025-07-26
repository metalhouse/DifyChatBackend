# 备份管理配置说明

## 概述
项目现在包含了完整的备份管理系统，可以自动管理用户数据文件的备份，防止数据丢失。

## 备份功能特性

### 自动备份
- 每次保存用户数据时自动创建备份文件
- 备份文件使用时间戳命名格式：`users.json.backup.YYYYMMDD_HHMMSS`
- 备份文件存储在与原文件相同的目录中

### 备份清理
- 自动清理旧备份文件，避免磁盘空间浪费
- 保留最新的指定数量备份文件（默认5个）
- 删除超过保留数量的旧备份文件

### 配置选项
通过`.env`文件可以配置以下参数：

```properties
# 备份配置
BACKUP_ENABLED=true              # 是否启用备份功能
BACKUP_MAX_FILES=5              # 最大保留备份文件数量
BACKUP_ON_SAVE=true            # 保存时自动备份
BACKUP_CLEANUP_ON_STARTUP=false # 启动时清理旧备份
```

## 配置说明

### BACKUP_ENABLED
- **默认值**: `true`
- **说明**: 控制是否启用整个备份系统
- **值**: `true`/`false`

### BACKUP_MAX_FILES
- **默认值**: `5`
- **说明**: 保留的最大备份文件数量
- **建议**: 3-10个，根据数据重要性和磁盘空间决定

### BACKUP_ON_SAVE
- **默认值**: `true`
- **说明**: 是否在每次保存用户数据时创建备份
- **值**: `true`/`false`

### BACKUP_CLEANUP_ON_STARTUP
- **默认值**: `false`
- **说明**: 是否在应用启动时清理旧备份文件
- **值**: `true`/`false`

## 手动清理工具

项目还提供了手动清理备份文件的脚本：

```bash
python cleanup_backups.py
```

该脚本会：
1. 扫描所有备份文件
2. 显示将要删除和保留的文件列表
3. 要求用户确认删除操作
4. 执行清理并显示结果

## 使用建议

### 开发环境
- `BACKUP_ENABLED=true` - 保护开发数据
- `BACKUP_MAX_FILES=3` - 减少文件数量
- `BACKUP_ON_SAVE=true` - 实时备份

### 生产环境
- `BACKUP_ENABLED=true` - 必须启用
- `BACKUP_MAX_FILES=10` - 保留更多备份
- `BACKUP_ON_SAVE=true` - 实时备份
- `BACKUP_CLEANUP_ON_STARTUP=true` - 启动时清理

### 测试环境
- `BACKUP_ENABLED=false` - 可以禁用以减少干扰
- 或者设置 `BACKUP_MAX_FILES=2` - 最小化备份

## 故障恢复

如果需要恢复数据，可以：

1. 查看data目录中的备份文件
2. 选择需要恢复的时间点
3. 将备份文件复制为`users.json`

```bash
# 恢复到指定时间点的备份
cp data/users.json.backup.20250726_101554 data/users.json
```

## 注意事项

1. **备份文件格式**: 备份文件与原文件格式完全相同
2. **时间戳格式**: `YYYYMMDD_HHMMSS`，按时间自然排序
3. **自动清理**: 清理基于文件名时间戳，确保保留最新的文件
4. **错误处理**: 如果备份创建或清理失败，不会影响主要功能
5. **日志记录**: 所有备份操作都会记录到应用日志中

## 监控建议

建议定期检查：
- 备份文件数量是否在预期范围内
- 备份文件是否正常创建
- 磁盘空间是否充足
- 日志中是否有备份相关错误
