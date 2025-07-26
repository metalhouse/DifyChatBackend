# 聊天室系统问题排查指南

## 🚨 常见问题及解决方案

### 1. JWT认证问题

#### 问题：API返回401 "无效的认证令牌"
**症状**：
```json
{
  "error_code": "INVALID_TOKEN",
  "message": "无效的认证令牌",
  "success": false
}
```

**可能原因**：
1. JWT密钥配置不一致
2. Token已过期
3. Token格式错误

**解决步骤**：
```bash
# 1. 检查配置
echo $JWT_SECRET_KEY
echo $SECRET_KEY

# 2. 重新登录获取新token
curl -X POST http://127.0.0.1:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"metalhouse","password":"Iwhyi3589"}'

# 3. 验证token格式
echo "YOUR_TOKEN" | base64 -d
```

**修复方案**：
- 确保 `chatroom/services/permissions.py` 中使用 `jwt_secret_key`
- 检查环境变量配置

### 2. 数据库连接问题

#### 问题：数据库服务不可用
**症状**：
```json
{
  "error_code": "DATABASE_SERVICE_UNAVAILABLE",
  "message": "数据库服务不可用"
}
```

**排查步骤**：
```bash
# 1. 测试MariaDB连接
python -c "
from chatroom.mariadb_config import db_manager
print('✅' if db_manager.test_connection() else '❌')
"

# 2. 检查数据库配置
python -c "
from chatroom.mariadb_config import MariaDBConfig
config = MariaDBConfig()
print(f'Host: {config.host}:{config.port}')
print(f'Database: {config.database}')
print(f'Enabled: {config.enabled}')
"

# 3. 手动测试连接
mysql -h 192.168.1.10 -P 3307 -u root -p
```

**常见解决方案**：
1. 检查MariaDB服务是否运行
2. 验证网络连接和端口
3. 确认用户名密码正确
4. 检查数据库权限

### 3. 聊天室操作问题

#### 问题：删除聊天室失败
**症状**: "Data truncated for column 'status'"

**原因**: 使用了数据库不支持的status值

**解决方案**：
```python
# 错误的删除操作
UPDATE chatrooms SET status = 'inactive'  # 不支持

# 正确的删除操作  
UPDATE chatrooms SET status = 'disabled'  # 支持
```

#### 问题：创建聊天室权限不足
**症状**：
```json
{
  "error_code": "INSUFFICIENT_PERMISSIONS",
  "message": "没有足够的权限访问此资源"
}
```

**检查权限**：
```python
# 确认用户角色
from chatroom.services.permissions import get_current_user
user = get_current_user()
print(f"User roles: {user.get('roles', [])}")
```

### 4. 系统启动问题

#### 问题：聊天室系统初始化失败
**检查清单**：
```bash
# 1. 环境变量
echo $CHATROOM_ENABLED  # 应该是 'true'
echo $MARIADB_ENABLED   # 应该是 'true'

# 2. 依赖检查
pip list | grep -E "(pymysql|sqlalchemy|flask|jwt)"

# 3. 文件权限
ls -la chatroom/
ls -la chatroom_database_*.sql

# 4. 数据库表检查
python check_table.py
```

#### 问题：连接管理器警告
**症状**: "ConnectionManager object has no attribute 'connections'"

**临时解决方案**: 这是WebSocket连接管理器的问题，不影响HTTP API功能，可以忽略。

**长期修复**: 需要完善WebSocket连接管理器实现。

### 5. 性能问题

#### 问题：响应速度慢
**排查步骤**：
```bash
# 1. 检查数据库连接池
python -c "
from chatroom.mariadb_config import db_manager
print(f'Pool size: {db_manager.config.pool_size}')
print(f'Max overflow: {db_manager.config.max_overflow}')
"

# 2. 查看慢查询
tail -f logs/app.log | grep -E "(slow|timeout|error)"

# 3. 数据库性能检查
mysql -h 192.168.1.10 -P 3307 -u root -p -e "SHOW PROCESSLIST;"
```

**优化建议**：
1. 增加连接池大小
2. 添加数据库索引
3. 使用连接预热

## 🔍 调试工具和技巧

### 1. 日志分析
```bash
# 查看特定时间的日志
grep "2025-07-26 09:" logs/app.log

# 查看特定用户的操作
grep "metalhouse" logs/app.log

# 查看错误信息
grep -E "(ERROR|WARN)" logs/app.log
```

### 2. 数据库调试
```python
# 开启SQL日志
# 在 mariadb_config.py 中设置
echo=True  # 在 create_engine 中

# 手动执行SQL查询
from chatroom.mariadb_config import get_mariadb_connection
with get_mariadb_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM chatrooms LIMIT 5")
    print(cursor.fetchall())
```

### 3. JWT调试
```python
# 解码JWT token查看内容
import jwt
token = "YOUR_JWT_TOKEN"
payload = jwt.decode(token, options={"verify_signature": False})
print(payload)
```

### 4. 权限调试
```python
# 检查用户权限
from chatroom.services.permissions import ChatroomPermissionManager
roles = ["admin"]
permissions = ChatroomPermissionManager.get_user_permissions(roles)
print(f"Permissions: {permissions}")
```

## 📋 健康检查脚本

创建自动化健康检查脚本：

```python
#!/usr/bin/env python3
# health_check.py

import requests
import json

def check_health():
    """完整的系统健康检查"""
    
    print("🏥 开始系统健康检查...")
    
    # 1. 基础连接检查
    try:
        response = requests.get("http://127.0.0.1:5000/health", timeout=5)
        print(f"✅ 应用服务: {response.status_code}")
    except Exception as e:
        print(f"❌ 应用服务: {e}")
        return False
    
    # 2. 数据库检查
    try:
        from chatroom.mariadb_config import initialize_mariadb_for_chatroom
        if initialize_mariadb_for_chatroom():
            print("✅ 数据库连接: 正常")
        else:
            print("❌ 数据库连接: 失败")
            return False
    except Exception as e:
        print(f"❌ 数据库检查: {e}")
        return False
    
    # 3. 登录功能检查
    try:
        login_data = {
            "username": "metalhouse",
            "password": "Iwhyi3589"
        }
        response = requests.post(
            "http://127.0.0.1:5000/api/v1/auth/login",
            json=login_data,
            timeout=5
        )
        if response.status_code == 200:
            print("✅ 用户认证: 正常")
            return True
        else:
            print(f"❌ 用户认证: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 认证检查: {e}")
        return False

if __name__ == "__main__":
    success = check_health()
    exit(0 if success else 1)
```

## 📞 紧急处理流程

### 系统完全无法访问
1. 检查服务进程: `ps aux | grep python`
2. 检查端口占用: `netstat -tulpn | grep 5000`
3. 重启服务: `python app.py`
4. 检查防火墙设置

### 数据库连接全部失败
1. 检查MariaDB服务状态
2. 重置连接池: 重启应用
3. 检查网络连接
4. 验证数据库权限

### 大量401错误
1. 立即重新生成JWT密钥
2. 通知所有用户重新登录
3. 检查系统时间同步
4. 验证密钥配置

---

**紧急联系**: 遇到严重问题请立即查看应用日志并保存现场信息
