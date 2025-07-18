"""
权限分析脚本 - 检查用户权限配置
"""

# 各API端点需要的权限
api_permissions = {
    # 基础聊天功能
    "api_agents": ["access_agents"],
    "api_conversations": ["view_conversations"], 
    "api_chat": ["send_messages"],
    "api_create_conversation": ["create_conversations"],
    "api_chat_messages": ["send_messages", "create_conversations"],
    
    # 新增Dify API
    "api_message_feedback": ["send_messages"],  # 消息反馈
    "api_suggested_questions": ["view_conversations"],  # 建议问题  
    "api_delete_conversation": ["delete_conversations"],  # 删除对话
    "api_rename_conversation": ["edit_conversations"],  # 重命名对话
    "api_audio_to_text": ["send_messages"],  # 语音转文字
    "api_text_to_audio": ["send_messages"],  # 文字转语音
    "api_messages_history": ["view_conversations"],  # 历史消息
    "api_app_info": ["view_app_info"],  # 应用信息
    
    # 缓存管理
    "api_user_permissions": ["view_permissions"],
    "api_agent_config": ["view_agent_config"], 
    "api_preload_cache": ["manage_cache", "admin"],
    "api_refresh_agent_cache": ["manage_cache", "admin"],
    "api_invalidate_cache": ["manage_cache", "admin"],
    "api_cache_stats": ["view_stats"],
    "api_cache_health": ["manage_cache", "admin"]
}

# 当前用户权限
current_permissions = [
    "access_agents",
    "view_conversations",
    "send_messages",
    "create_conversations",
    "edit_conversations",
    "delete_conversations",
    "view_app_info",
    "audio_to_text",
    "text_to_audio",
    "message_feedback",
    "suggested_questions",
    "messages_history",
    "view_permissions",
    "view_agent_config",
    "view_stats",
    "manage_cache",
    "admin",
    "admin_access",
    "manage_users",
    "view_all_agents",
    "manage_agents",
    "view_system_logs",
    "use_chat"
]

print("🔍 权限分析报告")
print("=" * 60)

# 分析缺失权限
missing_permissions = set()
extra_permissions = set(current_permissions)

print("\n📋 API端点权限检查:")
for api_name, required_perms in api_permissions.items():
    print(f"\n🔸 {api_name}:")
    print(f"   需要权限: {required_perms}")
    
    has_all_perms = True
    missing_for_api = []
    
    for perm in required_perms:
        if perm not in current_permissions:
            has_all_perms = False
            missing_for_api.append(perm)
            missing_permissions.add(perm)
        else:
            extra_permissions.discard(perm)
    
    if has_all_perms:
        print(f"   ✅ 权限充足")
    else:
        print(f"   ❌ 缺失权限: {missing_for_api}")

print(f"\n📊 权限统计:")
print(f"✅ 已配置权限总数: {len(current_permissions)}")
print(f"❌ 缺失权限数: {len(missing_permissions)}")
print(f"⚠️  可能多余权限数: {len(extra_permissions)}")

if missing_permissions:
    print(f"\n❌ 缺失的权限:")
    for perm in sorted(missing_permissions):
        print(f"   - {perm}")

if extra_permissions:
    print(f"\n⚠️  可能多余的权限 (可能用于其他功能):")
    for perm in sorted(extra_permissions):
        print(f"   - {perm}")

# 基于Dify API文档的标准权限建议
dify_standard_permissions = [
    "access_agents", "view_conversations", "send_messages", "create_conversations",
    "edit_conversations", "delete_conversations", "view_app_info", 
    "audio_to_text", "text_to_audio", "message_feedback", "suggested_questions",
    "messages_history", "view_permissions", "view_agent_config", "view_stats"
]

print(f"\n💡 基于Dify API文档的建议权限:")
for perm in sorted(dify_standard_permissions):
    status = "✅" if perm in current_permissions else "❌"
    print(f"   {status} {perm}")
