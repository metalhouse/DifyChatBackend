-- 验证聊天室数据库导入完整性
-- 请在 Navicat 中执行以下查询来确认导入结果

-- =============================================
-- 1. 检查表结构
-- =============================================
SELECT '=== 表结构检查 ===' as Check_Type;

-- 显示所有聊天室相关表
SHOW TABLES LIKE 'chatroom%';

-- 检查表数量（应该是6个表）
SELECT 
    COUNT(*) as table_count,
    '应该是 6 个表' as expected_count
FROM information_schema.tables 
WHERE table_schema = 'chatroom_db' 
AND table_name LIKE 'chatroom%';

-- 列出所有表的详细信息
SELECT 
    table_name,
    table_comment,
    engine,
    table_collation
FROM information_schema.tables 
WHERE table_schema = 'chatroom_db' 
AND table_name LIKE 'chatroom%'
ORDER BY table_name;

-- =============================================
-- 2. 检查视图
-- =============================================
SELECT '=== 视图检查 ===' as Check_Type;

-- 检查视图数量（应该是3个视图）
SELECT 
    COUNT(*) as view_count,
    '应该是 3 个视图' as expected_count
FROM information_schema.views 
WHERE table_schema = 'chatroom_db';

-- 列出所有视图
SELECT 
    table_name as view_name,
    view_definition
FROM information_schema.views 
WHERE table_schema = 'chatroom_db'
ORDER BY table_name;

-- =============================================
-- 3. 检查存储过程（修复版没有存储过程）
-- =============================================
SELECT '=== 存储过程检查 ===' as Check_Type;

-- 检查存储过程数量
SELECT 
    COUNT(*) as procedure_count,
    '修复版应该是 0 个存储过程' as note
FROM information_schema.routines 
WHERE routine_schema = 'chatroom_db'
AND routine_type = 'PROCEDURE';

-- =============================================
-- 4. 检查示例数据
-- =============================================
SELECT '=== 示例数据检查 ===' as Check_Type;

-- 查看示例聊天室
SELECT 
    name as chatroom_name,
    description,
    is_public,
    max_users,
    created_by,
    status
FROM chatrooms
ORDER BY created_at;

-- 查看聊天室设置数量
SELECT 
    COUNT(*) as settings_count,
    '应该有一些聊天室设置记录' as note
FROM chatroom_settings;

-- 查看系统消息数量
SELECT 
    COUNT(*) as system_messages_count,
    '应该有一些系统消息' as note
FROM chatroom_messages 
WHERE is_system = 1;

-- =============================================
-- 5. 测试视图查询
-- =============================================
SELECT '=== 视图功能测试 ===' as Check_Type;

-- 测试聊天室统计视图
SELECT * FROM v_chatroom_stats;

-- 测试用户参与视图（可能为空，因为没有真实用户数据）
SELECT COUNT(*) as participation_records FROM v_user_chatroom_participation;

-- 测试消息统计视图（可能为空或很少记录）
SELECT COUNT(*) as message_stats_records FROM v_message_statistics;

-- =============================================
-- 6. 检查外键约束
-- =============================================
SELECT '=== 外键约束检查 ===' as Check_Type;

SELECT 
    table_name,
    constraint_name,
    referenced_table_name,
    referenced_column_name
FROM information_schema.key_column_usage 
WHERE table_schema = 'chatroom_db' 
AND referenced_table_name IS NOT NULL
ORDER BY table_name, constraint_name;

SELECT '=== 导入验证完成 ===' as Result;
