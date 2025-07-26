# Navicat 连接 MariaDB 聊天室数据库指南

## 📋 准备工作

### 1. 确保MariaDB服务运行
```bash
# 启动MariaDB服务（根据你的系统）
# Windows (XAMPP):
C:\xampp\mysql\bin\mysqld.exe

# Linux:
sudo systemctl start mariadb

# Docker:
docker run -d --name mariadb -e MYSQL_ROOT_PASSWORD=root_password -p 3306:3306 mariadb:10
```

### 2. 创建数据库用户（可选）
如果需要专门的聊天室数据库用户，可以执行：

```sql
-- 连接到MariaDB根用户
-- 创建聊天室数据库用户
CREATE USER 'chatroom_user'@'%' IDENTIFIED BY 'your_secure_password';

-- 创建聊天室数据库
CREATE DATABASE chatroom_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 给用户授权
GRANT ALL PRIVILEGES ON chatroom_db.* TO 'chatroom_user'@'%';
FLUSH PRIVILEGES;
```

### ⚠️ 权限问题解决方案

如果遇到 **ERROR 1044: Access denied for user 'root'@'%'** 错误，说明当前用户没有 GRANT 权限。请按以下步骤解决：

#### 方法1: 使用本地root用户连接
```sql
-- 确保使用 root@localhost 而不是 root@% 连接
-- 在Navicat中修改连接：
-- 主机: localhost (不要使用IP地址)
-- 用户名: root
-- 然后重新执行授权命令
```

#### 方法2: 检查并修复root用户权限
```sql
-- 1. 先检查当前用户权限
SHOW GRANTS FOR CURRENT_USER();

-- 2. 如果权限不足，需要用管理员权限登录MySQL
-- 在命令行中执行：
mysql -u root -p

-- 3. 检查root用户的权限
SELECT user, host, Grant_priv, Super_priv FROM mysql.user WHERE user='root';

-- 4. 如果Grant_priv为'N'，需要修复：
UPDATE mysql.user SET Grant_priv='Y' WHERE user='root' AND host='localhost';
FLUSH PRIVILEGES;
```

#### 方法3: 重新创建root用户权限
```sql
-- 如果root用户权限损坏，重新授权：
GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
```

#### 方法4: 使用命令行直接创建
```bash
# 在系统命令行中执行（不在Navicat中）
mysql -u root -p -e "
CREATE USER 'chatroom_user'@'%' IDENTIFIED BY 'your_secure_password';
CREATE DATABASE chatroom_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON chatroom_db.* TO 'chatroom_user'@'%';
FLUSH PRIVILEGES;
"
```

## 🔧 Navicat 连接配置

### 1. 创建新连接
1. 打开 Navicat for MySQL/MariaDB
2. 点击 "连接" → "MySQL" 或 "MariaDB"
3. 填写连接信息：

```
连接名称: ChatRoom-MariaDB
主机: localhost (或你的MariaDB服务器地址)
端口: 3306
用户名: chatroom_user (或 root)
密码: your_secure_password
数据库: chatroom_db (可选，连接后选择)
```

### 2. 高级设置（可选）
- **字符集**: utf8mb4
- **排序规则**: utf8mb4_unicode_ci
- **连接超时**: 20秒
- **命令超时**: 30秒

### 3. 测试连接
点击 "测试连接" 按钮，确保连接成功。

## 📊 导入数据库结构

### ⚠️ 重要：选择合适的SQL文件

根据遇到的错误类型，选择对应的SQL文件：

#### 🎯 最佳选择：使用修复版SQL文件（推荐）
```
文件: chatroom_database_fixed.sql
特点: 修复了列名歧义问题(ERROR 1052)，不包含存储过程
位置: 项目根目录
状态: 最新修复版，推荐使用
```

#### 备选方案1：简化版SQL文件
```
文件: chatroom_database_simple.sql
特点: 不包含存储过程，避免ERROR 1064语法错误
位置: 项目根目录
使用场景: 如果修复版出现问题时的备选方案
```

#### 备选方案2：完整版SQL文件
```
文件: chatroom/chatroom_database.sql  
特点: 包含存储过程和完整功能
注意: 可能出现ERROR 1064(语法错误)或ERROR 1052(列名歧义)错误
使用场景: 仅在其他版本都失败时尝试，需要手动分段执行
```

### 方法1: 使用修复版SQL文件（强烈推荐）
1. 连接到数据库后，右键选择数据库 `chatroom_db`
2. 选择 "运行SQL文件..."
3. 选择 `chatroom_database_fixed.sql` 文件（修复了ERROR 1052列名歧义问题）
4. 点击 "开始" 执行

### 方法2: 使用简化版SQL文件（备选）
1. 连接到数据库后，右键选择数据库 `chatroom_db`
2. 选择 "运行SQL文件..."
3. 选择 `chatroom_database_simple.sql` 文件
4. 点击 "开始" 执行

### 方法3: 使用完整版SQL文件（最后选择）
1. 连接到数据库后，右键选择数据库
2. 选择 "运行SQL文件..."
3. 选择 `chatroom/chatroom_database.sql` 文件
4. 点击 "开始" 执行

### 方法3: 分段执行
如果一次性执行失败，可以分段执行：

#### 第一步：创建表结构
```sql
-- 只执行创建表的部分
-- 从 "DROP TABLE IF EXISTS `chatrooms`;" 开始
-- 到所有 CREATE TABLE 语句结束
```

#### 第二步：插入示例数据
```sql
-- 执行插入示例数据的部分
INSERT INTO `chatrooms` (`id`, `name`, `description`, `is_public`, `max_users`, `created_by`, `status`) VALUES
(UUID(), '公共聊天室', '欢迎大家在这里自由交流讨论！', 1, 100, 'system', 'active'),
-- ... 其他插入语句
```

#### 第三步：创建视图和存储过程
```sql
-- 执行创建视图的部分
CREATE OR REPLACE VIEW `v_chatroom_stats` AS
-- ...

-- 执行创建存储过程的部分
DELIMITER $$
CREATE PROCEDURE `CleanupExpiredOnlineUsers`(IN `minutes_threshold` INT DEFAULT 30)
-- ...
DELIMITER ;
```

## 📋 验证安装结果

### 1. 检查表结构
执行以下查询验证表是否创建成功：

```sql
-- 显示所有聊天室相关表
SHOW TABLES LIKE 'chatroom%';

-- 检查表数量
SELECT 
    COUNT(*) as table_count 
FROM information_schema.tables 
WHERE table_schema = 'chatroom_db' 
AND table_name LIKE 'chatroom%';
```

> **⚠️ 重要提示**: 如果在导入SQL文件时遇到存储过程语法错误（如ERROR 1064），请按以下方式分段执行：

#### 方法A: 跳过存储过程（推荐）
创建一个不包含存储过程的简化版本：

```sql
-- 1. 先执行表结构部分（从开头到所有CREATE TABLE语句结束）
-- 2. 执行插入示例数据部分
-- 3. 执行创建视图部分
-- 4. 暂时跳过存储过程部分
```

#### 方法B: 手动创建存储过程
如果需要存储过程功能，在Navicat的查询窗口中分别执行：

```sql
-- 存储过程1: 清理过期在线用户
DELIMITER $$
CREATE PROCEDURE CleanupExpiredOnlineUsers(IN minutes_threshold INT)
BEGIN
    DELETE FROM chatroom_online_users 
    WHERE last_seen < DATE_SUB(NOW(), INTERVAL minutes_threshold MINUTE);
    SELECT ROW_COUNT() as cleaned_records;
END$$
DELIMITER ;

-- 存储过程2: 获取聊天室消息历史
DELIMITER $$
CREATE PROCEDURE GetChatroomMessages(
    IN p_chatroom_id VARCHAR(36),
    IN p_limit INT,
    IN p_offset INT
)
BEGIN
    SELECT 
        id, user_id, username, message, message_type,
        created_at, status
    FROM chatroom_messages 
    WHERE chatroom_id = p_chatroom_id 
    AND status = 'normal'
    ORDER BY created_at DESC
    LIMIT p_limit OFFSET p_offset;
END$$
DELIMITER ;

-- 检查表数量
SELECT 
    COUNT(*) as table_count 
FROM information_schema.tables 
WHERE table_schema = 'chatroom_db' 
AND table_name LIKE 'chatroom%';
```

应该看到以下表：
- `chatrooms` - 聊天室表
- `chatroom_members` - 成员表  
- `chatroom_messages` - 消息表
- `chatroom_online_users` - 在线用户表
- `chatroom_settings` - 设置表
- `chatroom_message_reads` - 消息阅读状态表

### 2. 检查示例数据
```sql
-- 查看示例聊天室
SELECT id, name, description, is_public, max_users, created_by, status 
FROM chatrooms;

-- 查看聊天室设置
SELECT 
    c.name as chatroom_name,
    s.setting_key,
    s.setting_value
FROM chatroom_settings s
JOIN chatrooms c ON s.chatroom_id = c.id;
```

### 3. 检查视图
```sql
-- 查看聊天室统计视图
SELECT * FROM v_chatroom_stats;

-- 检查视图数量
SELECT COUNT(*) as view_count 
FROM information_schema.views 
WHERE table_schema = 'chatroom_db';
```

### 4. 检查存储过程
```sql
-- 查看存储过程
SELECT routine_name, routine_type 
FROM information_schema.routines 
WHERE routine_schema = 'chatroom_db';

-- 测试存储过程
CALL CleanupExpiredOnlineUsers(30);
```

## 🛠️ 常见问题解决

### ⚠️ 权限问题专项诊断

如果遇到 **ERROR 1044 (42000): Access denied** 错误，请按以下步骤逐一排查：

#### 🔍 第一步：诊断当前状态
```sql
-- 检查当前登录用户
SELECT USER(), CURRENT_USER();

-- 检查MySQL版本
SELECT VERSION();

-- 检查当前用户的权限
SHOW GRANTS;
```

#### 🔧 第二步：权限修复方案

**方案A: 重启MySQL服务并用管理员模式连接**
```bash
# Windows (以管理员身份运行命令提示符)
net stop mysql
net start mysql

# 或者重启XAMPP中的MySQL服务
```

**方案B: 使用跳过权限检查模式（慎用）**
```bash
# 1. 停止MySQL服务
# 2. 以跳过权限表模式启动MySQL
mysqld --skip-grant-tables

# 3. 在另一个终端连接MySQL
mysql -u root

# 4. 修复权限
USE mysql;
UPDATE user SET Grant_priv='Y' WHERE user='root';
FLUSH PRIVILEGES;

# 5. 正常重启MySQL服务
```

**方案C: 完整的权限重置**
```sql
-- 在确保有管理员权限的情况下执行
DROP USER IF EXISTS 'chatroom_user'@'%';
DROP USER IF EXISTS 'chatroom_user'@'localhost';

-- 重新创建用户
CREATE USER 'chatroom_user'@'%' IDENTIFIED BY 'your_secure_password';
CREATE USER 'chatroom_user'@'localhost' IDENTIFIED BY 'your_secure_password';

-- 创建数据库
CREATE DATABASE IF NOT EXISTS chatroom_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 分别给两个host授权
GRANT ALL PRIVILEGES ON chatroom_db.* TO 'chatroom_user'@'%';
GRANT ALL PRIVILEGES ON chatroom_db.* TO 'chatroom_user'@'localhost';
FLUSH PRIVILEGES;
```

#### 🧪 第三步：测试连接
```sql
-- 测试新用户连接
-- 断开当前连接，用chatroom_user重新连接
-- 然后执行：
USE chatroom_db;
CREATE TABLE test_table (id INT PRIMARY KEY);
DROP TABLE test_table;
```

#### 🛠️ 自动修复工具
如果手动操作复杂，可以使用提供的修复脚本：

```bash
# 在项目根目录运行
python fix_mysql_permissions.py
```

该脚本会：
1. 测试MySQL连接
2. 检查和修复root权限
3. 自动创建chatroom_user用户
4. 设置正确的数据库权限

### 1. 连接失败
**问题**: 无法连接到MariaDB服务器
**解决方案**:
- 检查MariaDB服务是否启动
- 确认端口3306未被占用
- 检查防火墙设置
- 验证用户名和密码

### 2. 字符集问题
**问题**: 中文显示乱码
**解决方案**:
```sql
-- 检查数据库字符集
SHOW CREATE DATABASE chatroom_db;

-- 如果字符集不是utf8mb4，需要修改
ALTER DATABASE chatroom_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. 权限不足 (ERROR 1044)
**问题**: Access denied for user 'root'@'%' (using password: YES)
**原因**: root用户没有GRANT权限或连接方式不正确

**解决方案**:

#### 步骤1: 检查连接方式
确保在Navicat中使用正确的连接参数：
```
主机: localhost (而不是127.0.0.1或其他IP)
用户名: root
密码: 你的root密码
```

#### 步骤2: 验证root权限
```sql
-- 检查当前用户
SELECT USER();

-- 检查当前用户权限
SHOW GRANTS FOR CURRENT_USER();

-- 应该看到类似这样的输出：
-- GRANT ALL PRIVILEGES ON *.* TO `root`@`localhost` WITH GRANT OPTION
```

#### 步骤3: 修复root权限（如果需要）
如果权限不足，在系统命令行中执行：

**Windows (XAMPP)**:
```cmd
cd C:\xampp\mysql\bin
mysql.exe -u root -p
```

**Linux/macOS**:
```bash
sudo mysql -u root -p
```

然后执行：
```sql
-- 恢复root的完整权限
GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;

-- 现在创建聊天室用户
CREATE USER IF NOT EXISTS 'chatroom_user'@'%' IDENTIFIED BY 'your_secure_password';
CREATE DATABASE IF NOT EXISTS chatroom_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON chatroom_db.* TO 'chatroom_user'@'%';
FLUSH PRIVILEGES;
```

#### 步骤4: 验证创建结果
```sql
-- 检查用户是否创建成功
SELECT user, host FROM mysql.user WHERE user='chatroom_user';

-- 检查数据库是否创建成功
SHOW DATABASES LIKE 'chatroom_db';

-- 检查权限是否正确
SHOW GRANTS FOR 'chatroom_user'@'%';
```

### 4. 外键约束错误
**问题**: 创建表时外键约束失败
**解决方案**:
```sql
-- 临时禁用外键检查
SET FOREIGN_KEY_CHECKS = 0;
-- 执行创建表语句
-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;
```

## 📊 数据库管理建议

### 1. 定期备份
```sql
-- 备份整个数据库
mysqldump -u chatroom_user -p chatroom_db > chatroom_backup.sql

-- 恢复数据库
mysql -u chatroom_user -p chatroom_db < chatroom_backup.sql
```

### 2. 性能监控
```sql
-- 检查表大小
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)'
FROM information_schema.tables 
WHERE table_schema = 'chatroom_db'
ORDER BY (data_length + index_length) DESC;

-- 检查慢查询
SHOW PROCESSLIST;
```

### 3. 索引优化
```sql
-- 检查索引使用情况
SHOW INDEX FROM chatroom_messages;

-- 分析表性能
ANALYZE TABLE chatroom_messages;
```

## 🚀 下一步

数据库创建完成后：

1. **配置环境变量**: 复制 `.env.example` 为 `.env` 并修改数据库连接信息
2. **测试连接**: 运行 `python chatroom/mariadb_config.py` 测试连接
3. **启动应用**: 运行 `python app.py` 启动聊天室系统
4. **测试功能**: 访问 `http://localhost:5000` 测试聊天室功能

## 📚 相关文档

- [聊天室集成指南](INTEGRATION_GUIDE.md)
- [WebSocket API文档](WEBSOCKET_API.md)
- [数据库配置说明](mariadb_config.py)

---

如有问题，请检查日志文件或联系开发团队。
