-- =============================================
-- 聊天室系统数据库结构文件（修复版）
-- 适用于 MariaDB 10.x / MySQL 8.x
-- 修复了列名歧义问题 (ERROR 1052)
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
  KEY `idx_messages_status` (`status`),
  KEY `idx_messages_reply_to` (`reply_to_id`),
  CONSTRAINT `fk_messages_chatroom` FOREIGN KEY (`chatroom_id`) REFERENCES `chatrooms` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_messages_reply` FOREIGN KEY (`reply_to_id`) REFERENCES `chatroom_messages` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天消息表';

-- =============================================
-- 4. 在线用户表 (chatroom_online_users)
-- =============================================
DROP TABLE IF EXISTS `chatroom_online_users`;
CREATE TABLE `chatroom_online_users` (
  `id` varchar(36) NOT NULL COMMENT '在线记录UUID主键',
  `chatroom_id` varchar(36) NOT NULL COMMENT '聊天室ID',
  `user_id` varchar(50) NOT NULL COMMENT '用户ID',
  `username` varchar(100) DEFAULT NULL COMMENT '用户名（冗余字段）',
  `session_id` varchar(100) DEFAULT NULL COMMENT '会话ID（WebSocket连接标识）',
  `joined_at` timestamp DEFAULT CURRENT_TIMESTAMP COMMENT '进入时间',
  `last_seen` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后活跃时间',
  `status` enum('online','away','busy') DEFAULT 'online' COMMENT '在线状态',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_online_chatroom_user` (`chatroom_id`,`user_id`) COMMENT '用户在同一聊天室中的在线状态唯一',
  KEY `idx_online_user_id` (`user_id`),
  KEY `idx_online_session` (`session_id`),
  KEY `idx_online_last_seen` (`last_seen`),
  CONSTRAINT `fk_online_chatroom` FOREIGN KEY (`chatroom_id`) REFERENCES `chatrooms` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='在线用户表';

-- =============================================
-- 5. 聊天室设置表 (chatroom_settings)
-- =============================================
DROP TABLE IF EXISTS `chatroom_settings`;
CREATE TABLE `chatroom_settings` (
  `id` varchar(36) NOT NULL COMMENT '设置记录UUID主键',
  `chatroom_id` varchar(36) NOT NULL COMMENT '聊天室ID',
  `setting_key` varchar(50) NOT NULL COMMENT '设置键名',
  `setting_value` text DEFAULT NULL COMMENT '设置值',
  `data_type` enum('string','integer','boolean','json') DEFAULT 'string' COMMENT '数据类型',
  `description` varchar(200) DEFAULT NULL COMMENT '设置描述',
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_setting_chatroom_key` (`chatroom_id`,`setting_key`) COMMENT '聊天室设置键唯一',
  KEY `idx_settings_key` (`setting_key`),
  CONSTRAINT `fk_settings_chatroom` FOREIGN KEY (`chatroom_id`) REFERENCES `chatrooms` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天室设置表';

-- =============================================
-- 6. 消息阅读状态表 (chatroom_message_reads)
-- =============================================
DROP TABLE IF EXISTS `chatroom_message_reads`;
CREATE TABLE `chatroom_message_reads` (
  `id` varchar(36) NOT NULL COMMENT '阅读记录UUID主键',
  `message_id` varchar(36) NOT NULL COMMENT '消息ID',
  `user_id` varchar(50) NOT NULL COMMENT '阅读用户ID',
  `read_at` timestamp DEFAULT CURRENT_TIMESTAMP COMMENT '阅读时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_read_message_user` (`message_id`,`user_id`) COMMENT '用户对消息的阅读状态唯一',
  KEY `idx_reads_user_id` (`user_id`),
  KEY `idx_reads_read_at` (`read_at`),
  CONSTRAINT `fk_reads_message` FOREIGN KEY (`message_id`) REFERENCES `chatroom_messages` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息阅读状态表';

-- =============================================
-- 插入示例数据
-- =============================================

-- 插入示例聊天室
INSERT INTO `chatrooms` (`id`, `name`, `description`, `is_public`, `max_users`, `created_by`, `status`) VALUES
(UUID(), '公共聊天室', '欢迎大家在这里自由交流讨论！', 1, 100, 'system', 'active'),
(UUID(), '技术交流群', '分享技术心得，讨论编程问题', 1, 50, 'admin', 'active'),
(UUID(), '项目协作室', '团队内部项目讨论专用', 0, 20, 'project_manager', 'active');

-- 获取刚插入的聊天室ID（用于后续插入）
SET @public_room_id = (SELECT id FROM chatrooms WHERE name = '公共聊天室' LIMIT 1);
SET @tech_room_id = (SELECT id FROM chatrooms WHERE name = '技术交流群' LIMIT 1);
SET @project_room_id = (SELECT id FROM chatrooms WHERE name = '项目协作室' LIMIT 1);

-- 插入示例聊天室设置
INSERT INTO `chatroom_settings` (`id`, `chatroom_id`, `setting_key`, `setting_value`, `data_type`, `description`) VALUES
(UUID(), @public_room_id, 'allow_file_upload', 'true', 'boolean', '是否允许文件上传'),
(UUID(), @public_room_id, 'max_message_length', '1000', 'integer', '最大消息长度'),
(UUID(), @public_room_id, 'welcome_message', '欢迎加入公共聊天室！请遵守聊天规则。', 'string', '欢迎消息'),
(UUID(), @tech_room_id, 'allow_file_upload', 'true', 'boolean', '是否允许文件上传'),
(UUID(), @tech_room_id, 'max_message_length', '2000', 'integer', '最大消息长度'),
(UUID(), @tech_room_id, 'code_highlighting', 'true', 'boolean', '是否启用代码高亮'),
(UUID(), @project_room_id, 'allow_file_upload', 'true', 'boolean', '是否允许文件上传'),
(UUID(), @project_room_id, 'max_message_length', '1500', 'integer', '最大消息长度'),
(UUID(), @project_room_id, 'private_mode', 'true', 'boolean', '私有模式');

-- 插入示例系统消息
INSERT INTO `chatroom_messages` (`id`, `chatroom_id`, `user_id`, `username`, `message`, `message_type`, `is_system`) VALUES
(UUID(), @public_room_id, NULL, 'System', '聊天室创建成功，欢迎大家使用！', 'system', 1),
(UUID(), @tech_room_id, NULL, 'System', '技术交流群已开放，期待大家的技术分享！', 'system', 1),
(UUID(), @project_room_id, NULL, 'System', '项目协作室已准备就绪，团队成员可以开始讨论。', 'system', 1);

-- =============================================
-- 创建视图（修复列名歧义问题）
-- =============================================

-- 聊天室统计视图（修复版）
CREATE OR REPLACE VIEW `v_chatroom_stats` AS
SELECT 
    c.id as chatroom_id,
    c.name as chatroom_name,
    c.description,
    c.is_public,
    c.max_users,
    c.created_by,
    c.created_at,
    c.status,
    COALESCE(member_stats.member_count, 0) as member_count,
    COALESCE(member_stats.online_count, 0) as online_count,
    COALESCE(message_stats.message_count, 0) as message_count,
    COALESCE(message_stats.latest_message_time, NULL) as latest_message_time
FROM chatrooms c
LEFT JOIN (
    SELECT 
        cm.chatroom_id,
        COUNT(*) as member_count,
        SUM(CASE WHEN ou.user_id IS NOT NULL THEN 1 ELSE 0 END) as online_count
    FROM chatroom_members cm
    LEFT JOIN chatroom_online_users ou ON cm.chatroom_id = ou.chatroom_id AND cm.user_id = ou.user_id
    WHERE cm.status = 'active'
    GROUP BY cm.chatroom_id
) member_stats ON c.id = member_stats.chatroom_id
LEFT JOIN (
    SELECT 
        msg.chatroom_id,
        COUNT(*) as message_count,
        MAX(msg.created_at) as latest_message_time
    FROM chatroom_messages msg
    WHERE msg.status = 'normal'
    GROUP BY msg.chatroom_id
) message_stats ON c.id = message_stats.chatroom_id
WHERE c.status = 'active';

-- 用户聊天室参与视图（修复版）
CREATE OR REPLACE VIEW `v_user_chatroom_participation` AS
SELECT 
    cm.user_id,
    cm.username,
    c.id as chatroom_id,
    c.name as chatroom_name,
    c.is_public,
    cm.role,
    cm.joined_at,
    cm.last_active_at,
    cm.status as member_status,
    CASE WHEN ou.user_id IS NOT NULL THEN 1 ELSE 0 END as is_online,
    ou.last_seen,
    COALESCE(msg_stats.message_count, 0) as message_count
FROM chatroom_members cm
JOIN chatrooms c ON cm.chatroom_id = c.id
LEFT JOIN chatroom_online_users ou ON cm.chatroom_id = ou.chatroom_id AND cm.user_id = ou.user_id
LEFT JOIN (
    SELECT 
        msg.chatroom_id,
        msg.user_id,
        COUNT(*) as message_count
    FROM chatroom_messages msg
    WHERE msg.status = 'normal' AND msg.user_id IS NOT NULL
    GROUP BY msg.chatroom_id, msg.user_id
) msg_stats ON cm.chatroom_id = msg_stats.chatroom_id AND cm.user_id = msg_stats.user_id
WHERE cm.status = 'active' AND c.status = 'active';

-- 消息统计视图（修复版）
CREATE OR REPLACE VIEW `v_message_statistics` AS
SELECT 
    DATE(msg.created_at) as message_date,
    msg.chatroom_id,
    msg.message_type,
    COUNT(*) as message_count,
    COUNT(DISTINCT msg.user_id) as active_users
FROM chatroom_messages msg
WHERE msg.status = 'normal' AND msg.created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY DATE(msg.created_at), msg.chatroom_id, msg.message_type
ORDER BY message_date DESC, msg.chatroom_id;

-- 恢复外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- =============================================
-- 完成消息
-- =============================================
SELECT 'Chatroom database structure created successfully (Fixed Version)!' as Result;
SELECT COUNT(*) as Tables_Created FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name LIKE 'chatroom%';
SELECT COUNT(*) as Views_Created FROM information_schema.views WHERE table_schema = DATABASE() AND table_name LIKE 'v_%';
