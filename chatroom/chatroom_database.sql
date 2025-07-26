-- =============================================
-- 聊天室系统数据库结构文件
-- 适用于 MariaDB 10.x / MySQL 8.x
-- 创建时间: 2025-07-25
-- =============================================

-- 设置字符集和排序规则
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =============================================
-- 1. 聊天室表 (chatrooms)
-- =============================================
DROP TABLE IF EXISTS `chatrooms`;
CREATE TABLE `chatrooms` (
  `id` varchar(36) NOT NULL COMMENT '聊天室UUID主键',
  `name` varchar(100) NOT NULL COMMENT '聊天室名称',
  `description` text DEFAULT NULL COMMENT '聊天室描述',
  `is_public` tinyint(1) DEFAULT 1 COMMENT '是否公开聊天室 (1:公开, 0:私有)',
  `max_users` int(11) DEFAULT 100 COMMENT '最大用户数量',
  `created_by` varchar(50) NOT NULL COMMENT '创建者用户ID',
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `status` enum('active','archived','disabled') DEFAULT 'active' COMMENT '聊天室状态',
  PRIMARY KEY (`id`),
  KEY `idx_chatrooms_created_by` (`created_by`),
  KEY `idx_chatrooms_status` (`status`),
  KEY `idx_chatrooms_public` (`is_public`),
  KEY `idx_chatrooms_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天室表';

-- =============================================
-- 2. 聊天室成员表 (chatroom_members)
-- =============================================
DROP TABLE IF EXISTS `chatroom_members`;
CREATE TABLE `chatroom_members` (
  `id` varchar(36) NOT NULL COMMENT '成员记录UUID主键',
  `chatroom_id` varchar(36) NOT NULL COMMENT '聊天室ID',
  `user_id` varchar(50) NOT NULL COMMENT '用户ID',
  `username` varchar(100) DEFAULT NULL COMMENT '用户名（冗余字段，便于查询）',
  `role` enum('owner','admin','moderator','member') DEFAULT 'member' COMMENT '成员角色',
  `joined_at` timestamp DEFAULT CURRENT_TIMESTAMP COMMENT '加入时间',
  `last_active_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后活跃时间',
  `status` enum('active','muted','banned') DEFAULT 'active' COMMENT '成员状态',
  `mute_until` timestamp NULL DEFAULT NULL COMMENT '禁言截止时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_member_chatroom_user` (`chatroom_id`,`user_id`) COMMENT '用户在同一聊天室中唯一',
  KEY `idx_members_user_id` (`user_id`),
  KEY `idx_members_role` (`role`),
  KEY `idx_members_status` (`status`),
  KEY `idx_members_joined_at` (`joined_at`),
  CONSTRAINT `fk_members_chatroom` FOREIGN KEY (`chatroom_id`) REFERENCES `chatrooms` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天室成员表';

-- =============================================
-- 3. 聊天消息表 (chatroom_messages)
-- =============================================
DROP TABLE IF EXISTS `chatroom_messages`;
CREATE TABLE `chatroom_messages` (
  `id` varchar(36) NOT NULL COMMENT '消息UUID主键',
  `chatroom_id` varchar(36) NOT NULL COMMENT '聊天室ID',
  `user_id` varchar(50) DEFAULT NULL COMMENT '发送者用户ID（系统消息时可为空）',
  `username` varchar(100) DEFAULT NULL COMMENT '发送者用户名（冗余字段）',
  `message` text NOT NULL COMMENT '消息内容',
  `message_type` enum('text','image','file','audio','video','system','announcement') DEFAULT 'text' COMMENT '消息类型',
  `encrypted` tinyint(1) DEFAULT 0 COMMENT '是否加密 (1:加密, 0:未加密)',
  `encryption_data` json DEFAULT NULL COMMENT '加密数据（IV、密文、标签等）',
  `message_hash` varchar(64) DEFAULT NULL COMMENT '消息SHA256哈希（用于完整性验证）',
  `is_system` tinyint(1) DEFAULT 0 COMMENT '是否系统消息 (1:系统消息, 0:用户消息)',
  `reply_to_id` varchar(36) DEFAULT NULL COMMENT '回复的消息ID',
  `file_url` varchar(500) DEFAULT NULL COMMENT '文件URL（文件类型消息使用）',
  `file_size` bigint(20) DEFAULT NULL COMMENT '文件大小（字节）',
  `file_name` varchar(255) DEFAULT NULL COMMENT '文件名',
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `status` enum('normal','edited','deleted') DEFAULT 'normal' COMMENT '消息状态',
  PRIMARY KEY (`id`),
  KEY `idx_messages_chatroom_id` (`chatroom_id`),
  KEY `idx_messages_user_id` (`user_id`),
  KEY `idx_messages_created_at` (`created_at`),
  KEY `idx_messages_type` (`message_type`),
  KEY `idx_messages_system` (`is_system`),
  KEY `idx_messages_status` (`status`),
  KEY `idx_messages_reply_to` (`reply_to_id`),
  CONSTRAINT `fk_messages_chatroom` FOREIGN KEY (`chatroom_id`) REFERENCES `chatrooms` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_messages_reply_to` FOREIGN KEY (`reply_to_id`) REFERENCES `chatroom_messages` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天消息表';

-- =============================================
-- 4. 在线用户表 (chatroom_online_users)
-- =============================================
DROP TABLE IF EXISTS `chatroom_online_users`;
CREATE TABLE `chatroom_online_users` (
  `id` varchar(36) NOT NULL COMMENT '在线记录UUID主键',
  `chatroom_id` varchar(36) NOT NULL COMMENT '聊天室ID',
  `user_id` varchar(50) NOT NULL COMMENT '用户ID',
  `username` varchar(100) DEFAULT NULL COMMENT '用户名',
  `session_id` varchar(100) DEFAULT NULL COMMENT 'WebSocket会话ID',
  `socket_id` varchar(100) DEFAULT NULL COMMENT 'Socket连接ID',
  `joined_at` timestamp DEFAULT CURRENT_TIMESTAMP COMMENT '进入时间',
  `last_seen` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后活跃时间',
  `status` enum('online','away','busy','offline') DEFAULT 'online' COMMENT '用户状态',
  `ip_address` varchar(45) DEFAULT NULL COMMENT 'IP地址',
  `user_agent` text DEFAULT NULL COMMENT '用户代理信息',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_online_chatroom_user` (`chatroom_id`,`user_id`) COMMENT '用户在同一聊天室中的在线状态唯一',
  KEY `idx_online_user_id` (`user_id`),
  KEY `idx_online_session_id` (`session_id`),
  KEY `idx_online_socket_id` (`socket_id`),
  KEY `idx_online_last_seen` (`last_seen`),
  KEY `idx_online_status` (`status`),
  CONSTRAINT `fk_online_users_chatroom` FOREIGN KEY (`chatroom_id`) REFERENCES `chatrooms` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天室在线用户表';

-- =============================================
-- 5. 聊天室设置表 (chatroom_settings)
-- =============================================
DROP TABLE IF EXISTS `chatroom_settings`;
CREATE TABLE `chatroom_settings` (
  `id` varchar(36) NOT NULL COMMENT '设置记录UUID主键',
  `chatroom_id` varchar(36) NOT NULL COMMENT '聊天室ID',
  `setting_key` varchar(100) NOT NULL COMMENT '设置键',
  `setting_value` json DEFAULT NULL COMMENT '设置值',
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_settings_chatroom_key` (`chatroom_id`,`setting_key`) COMMENT '聊天室设置键唯一',
  CONSTRAINT `fk_settings_chatroom` FOREIGN KEY (`chatroom_id`) REFERENCES `chatrooms` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天室设置表';

-- =============================================
-- 6. 消息阅读状态表 (chatroom_message_reads)
-- =============================================
DROP TABLE IF EXISTS `chatroom_message_reads`;
CREATE TABLE `chatroom_message_reads` (
  `id` varchar(36) NOT NULL COMMENT '阅读记录UUID主键',
  `message_id` varchar(36) NOT NULL COMMENT '消息ID',
  `user_id` varchar(50) NOT NULL COMMENT '用户ID',
  `read_at` timestamp DEFAULT CURRENT_TIMESTAMP COMMENT '阅读时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_reads_message_user` (`message_id`,`user_id`) COMMENT '用户对消息的阅读状态唯一',
  KEY `idx_reads_user_id` (`user_id`),
  KEY `idx_reads_read_at` (`read_at`),
  CONSTRAINT `fk_reads_message` FOREIGN KEY (`message_id`) REFERENCES `chatroom_messages` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息阅读状态表';

-- =============================================
-- 7. 创建示例数据
-- =============================================

-- 插入示例聊天室
INSERT INTO `chatrooms` (`id`, `name`, `description`, `is_public`, `max_users`, `created_by`, `status`) VALUES
(UUID(), '公共聊天室', '欢迎大家在这里自由交流讨论！', 1, 100, 'system', 'active'),
(UUID(), '技术交流', '技术问题讨论和经验分享专区', 1, 50, 'system', 'active'),
(UUID(), '项目协作', '项目开发和协作讨论区', 0, 30, 'system', 'active');

-- 插入示例聊天室设置
INSERT INTO `chatroom_settings` (`id`, `chatroom_id`, `setting_key`, `setting_value`) 
SELECT 
    UUID(),
    c.id,
    'welcome_message',
    JSON_OBJECT('enabled', true, 'message', CONCAT('欢迎来到', c.name, '！请遵守聊天室规则，友好交流。'))
FROM `chatrooms` c;

INSERT INTO `chatroom_settings` (`id`, `chatroom_id`, `setting_key`, `setting_value`) 
SELECT 
    UUID(),
    c.id,
    'message_history_limit',
    JSON_OBJECT('limit', 1000, 'auto_cleanup', true)
FROM `chatrooms` c;

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- =============================================
-- 8. 创建视图（便于查询）
-- =============================================

-- 聊天室统计信息视图
CREATE OR REPLACE VIEW `v_chatroom_stats` AS
SELECT 
    c.id,
    c.name,
    c.description,
    c.is_public,
    c.max_users,
    c.created_by,
    c.created_at,
    c.status,
    COALESCE(m.member_count, 0) as member_count,
    COALESCE(o.online_count, 0) as online_count,
    COALESCE(msg.message_count, 0) as message_count,
    COALESCE(msg.latest_message_at, NULL) as latest_message_at
FROM `chatrooms` c
LEFT JOIN (
    SELECT chatroom_id, COUNT(*) as member_count 
    FROM `chatroom_members` 
    WHERE status = 'active' 
    GROUP BY chatroom_id
) m ON c.id = m.chatroom_id
LEFT JOIN (
    SELECT chatroom_id, COUNT(*) as online_count 
    FROM `chatroom_online_users` 
    WHERE status = 'online' 
    GROUP BY chatroom_id
) o ON c.id = o.chatroom_id
LEFT JOIN (
    SELECT 
        chatroom_id, 
        COUNT(*) as message_count,
        MAX(created_at) as latest_message_at
    FROM `chatroom_messages` 
    WHERE status = 'normal'
    GROUP BY chatroom_id
) msg ON c.id = msg.chatroom_id;

-- 用户聊天室参与情况视图
CREATE OR REPLACE VIEW `v_user_chatroom_participation` AS
SELECT 
    m.user_id,
    m.username,
    c.id as chatroom_id,
    c.name as chatroom_name,
    m.role,
    m.joined_at,
    m.last_active_at,
    m.status as member_status,
    CASE WHEN o.user_id IS NOT NULL THEN 1 ELSE 0 END as is_online,
    COALESCE(msg.message_count, 0) as message_count
FROM `chatroom_members` m
JOIN `chatrooms` c ON m.chatroom_id = c.id
LEFT JOIN `chatroom_online_users` o ON m.chatroom_id = o.chatroom_id AND m.user_id = o.user_id
LEFT JOIN (
    SELECT 
        chatroom_id, 
        user_id, 
        COUNT(*) as message_count
    FROM `chatroom_messages` 
    WHERE status = 'normal' AND is_system = 0
    GROUP BY chatroom_id, user_id
) msg ON m.chatroom_id = msg.chatroom_id AND m.user_id = msg.user_id
WHERE m.status = 'active' AND c.status = 'active';

-- =============================================
-- 9. 创建存储过程
-- =============================================

-- 清理过期在线用户记录
DELIMITER $$
CREATE PROCEDURE `CleanupExpiredOnlineUsers`(IN `minutes_threshold` INT DEFAULT 30)
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_chatroom_id VARCHAR(36);
    DECLARE v_user_id VARCHAR(50);
    
    -- 声明游标
    DECLARE cur CURSOR FOR 
        SELECT chatroom_id, user_id 
        FROM chatroom_online_users 
        WHERE last_seen < DATE_SUB(NOW(), INTERVAL minutes_threshold MINUTE);
    
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    -- 开始事务
    START TRANSACTION;
    
    -- 删除过期的在线用户记录
    DELETE FROM chatroom_online_users 
    WHERE last_seen < DATE_SUB(NOW(), INTERVAL minutes_threshold MINUTE);
    
    -- 获取影响行数
    SELECT ROW_COUNT() as cleaned_records;
    
    -- 提交事务
    COMMIT;
END$$

-- 获取聊天室消息历史（分页）
CREATE PROCEDURE `GetChatroomMessageHistory`(
    IN `p_chatroom_id` VARCHAR(36),
    IN `p_limit` INT DEFAULT 50,
    IN `p_offset` INT DEFAULT 0,
    IN `p_before_message_id` VARCHAR(36) DEFAULT NULL
)
BEGIN
    DECLARE v_before_created_at TIMESTAMP DEFAULT NULL;
    
    -- 如果指定了before_message_id，获取其创建时间
    IF p_before_message_id IS NOT NULL THEN
        SELECT created_at INTO v_before_created_at 
        FROM chatroom_messages 
        WHERE id = p_before_message_id;
    END IF;
    
    -- 查询消息历史
    SELECT 
        id,
        chatroom_id,
        user_id,
        username,
        message,
        message_type,
        encrypted,
        encryption_data,
        message_hash,
        is_system,
        reply_to_id,
        file_url,
        file_size,
        file_name,
        created_at,
        status
    FROM chatroom_messages
    WHERE 
        chatroom_id = p_chatroom_id
        AND status = 'normal'
        AND (v_before_created_at IS NULL OR created_at < v_before_created_at)
    ORDER BY created_at DESC
    LIMIT p_limit OFFSET p_offset;
END$$

DELIMITER ;

-- =============================================
-- 10. 创建触发器
-- =============================================

-- 聊天室成员变更时更新统计
DELIMITER $$
CREATE TRIGGER `tr_chatroom_members_after_insert` 
AFTER INSERT ON `chatroom_members`
FOR EACH ROW
BEGIN
    -- 这里可以添加统计更新逻辑
    -- 例如：更新聊天室成员计数缓存
    NULL;
END$$

CREATE TRIGGER `tr_chatroom_members_after_delete`
AFTER DELETE ON `chatroom_members`
FOR EACH ROW
BEGIN
    -- 清理该用户在此聊天室的在线状态
    DELETE FROM chatroom_online_users 
    WHERE chatroom_id = OLD.chatroom_id AND user_id = OLD.user_id;
END$$

DELIMITER ;

-- =============================================
-- 完成信息
-- =============================================
SELECT 
    '聊天室数据库结构创建完成!' as message,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name LIKE 'chatroom%') as tables_created,
    (SELECT COUNT(*) FROM information_schema.views WHERE table_schema = DATABASE() AND table_name LIKE 'v_%') as views_created,
    (SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = DATABASE() AND routine_type = 'PROCEDURE') as procedures_created;

-- 显示所有创建的表
SHOW TABLES LIKE 'chatroom%';

-- 显示表结构（可选，用于验证）
-- DESCRIBE chatrooms;
-- DESCRIBE chatroom_members;
-- DESCRIBE chatroom_messages;
-- DESCRIBE chatroom_online_users;
