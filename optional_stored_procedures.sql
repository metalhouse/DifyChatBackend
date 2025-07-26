-- 可选：手动添加存储过程
-- 只有在应用程序确实需要时才执行

-- =============================================
-- 存储过程1: 清理过期在线用户
-- =============================================
DELIMITER $$
CREATE PROCEDURE CleanupExpiredOnlineUsers(IN minutes_threshold INT DEFAULT 30)
BEGIN
    DELETE FROM chatroom_online_users 
    WHERE last_seen < DATE_SUB(NOW(), INTERVAL minutes_threshold MINUTE);
    SELECT ROW_COUNT() as cleaned_records;
END$$
DELIMITER ;

-- =============================================
-- 存储过程2: 获取聊天室消息历史
-- =============================================
DELIMITER $$
CREATE PROCEDURE GetChatroomMessages(
    IN p_chatroom_id VARCHAR(36),
    IN p_limit INT DEFAULT 50,
    IN p_offset INT DEFAULT 0
)
BEGIN
    SELECT 
        id, user_id, username, message, message_type,
        created_at, updated_at, status
    FROM chatroom_messages 
    WHERE chatroom_id = p_chatroom_id 
    AND status = 'normal'
    ORDER BY created_at DESC
    LIMIT p_limit OFFSET p_offset;
END$$
DELIMITER ;

-- =============================================
-- 存储过程3: 获取用户未读消息数量
-- =============================================
DELIMITER $$
CREATE PROCEDURE GetUnreadMessageCount(
    IN p_user_id VARCHAR(50),
    IN p_chatroom_id VARCHAR(36)
)
BEGIN
    SELECT 
        COUNT(*) as unread_count
    FROM chatroom_messages cm
    LEFT JOIN chatroom_message_reads cmr ON cm.id = cmr.message_id AND cmr.user_id = p_user_id
    WHERE cm.chatroom_id = p_chatroom_id
    AND cm.status = 'normal'
    AND cmr.id IS NULL  -- 未读的消息
    AND cm.user_id != p_user_id;  -- 排除自己发送的消息
END$$
DELIMITER ;

-- 验证存储过程创建结果
SELECT 
    routine_name,
    routine_type,
    created,
    routine_comment
FROM information_schema.routines 
WHERE routine_schema = 'chatroom_db'
ORDER BY routine_name;
