
-- 为 metalhouse 用户添加聊天室管理员权限
-- 请在 Navicat 中执行以下SQL语句

-- 1. 查看当前聊天室
SELECT id, name, description FROM chatrooms;

-- 2. 查看 metalhouse 当前的成员资格
SELECT 
    c.name as chatroom_name,
    cm.role,
    cm.status,
    cm.joined_at
FROM chatroom_members cm
JOIN chatrooms c ON cm.chatroom_id = c.id
WHERE cm.user_id = 'metalhouse';

-- 3. 为 metalhouse 添加到所有聊天室（如果不存在）
INSERT IGNORE INTO chatroom_members (id, chatroom_id, user_id, username, role, status)
SELECT 
    UUID() as id,
    c.id as chatroom_id,
    'metalhouse' as user_id,
    'metalhouse' as username,
    'admin' as role,
    'active' as status
FROM chatrooms c
WHERE c.id NOT IN (
    SELECT chatroom_id FROM chatroom_members WHERE user_id = 'metalhouse'
);

-- 4. 更新现有成员为管理员角色
UPDATE chatroom_members 
SET role = 'admin', status = 'active'
WHERE user_id = 'metalhouse';

-- 5. 验证结果
SELECT 
    c.name as chatroom_name,
    cm.role,
    cm.status
FROM chatroom_members cm
JOIN chatrooms c ON cm.chatroom_id = c.id
WHERE cm.user_id = 'metalhouse'
ORDER BY c.name;
