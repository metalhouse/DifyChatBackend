"""
修复API路由函数的URL参数问题
"""

import re

def fix_api_functions():
    """修复API函数的URL参数"""
    
    file_path = "d:/ChatDify_Codes/DifyChatBackend/api/chat_routes_v2.py"
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 定义需要修复的函数
    fixes = [
        # 修复 api_message_feedback
        {
            'old': 'def api_message_feedback():',
            'new': 'def api_message_feedback(message_id):'
        },
        # 修复 api_suggested_questions
        {
            'old': 'def api_suggested_questions():',
            'new': 'def api_suggested_questions(message_id):'
        },
        # 修复 api_delete_conversation
        {
            'old': 'def api_delete_conversation():',
            'new': 'def api_delete_conversation(conversation_id):'
        },
        # 修复 api_rename_conversation
        {
            'old': 'def api_rename_conversation():',
            'new': 'def api_rename_conversation(conversation_id):'
        },
        # 修复 api_messages_history
        {
            'old': 'def api_messages_history():',
            'new': 'def api_messages_history(conversation_id):'
        }
    ]
    
    # 应用修复
    for fix in fixes:
        content = content.replace(fix['old'], fix['new'])
    
    # 移除获取URL参数的代码，因为现在是直接参数
    url_param_patterns = [
        r"message_id = request\.view_args\.get\('message_id'\)",
        r"conversation_id = request\.view_args\.get\('conversation_id'\)"
    ]
    
    for pattern in url_param_patterns:
        content = re.sub(pattern, '', content)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ API函数参数修复完成")

def fix_user_permissions():
    """修复用户权限配置"""
    
    # 读取用户数据
    users_file = "d:/ChatDify_Codes/DifyChatBackend/data/users.json"
    
    import json
    with open(users_file, 'r', encoding='utf-8') as f:
        users = json.load(f)
    
    # 为 metalhouse 用户添加所有权限
    if 'metalhouse' in users:
        users['metalhouse']['permissions'] = [
            'access_agents',
            'access_conversations', 
            'send_messages',
            'edit_conversations',
            'delete_conversations',
            'view_app_info',
            'access_cache'
        ]
        users['metalhouse']['admin'] = True
    
    # 保存更新的用户数据
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    
    print("✅ 用户权限修复完成")

if __name__ == "__main__":
    print("🔧 开始修复API问题...")
    fix_api_functions()
    fix_user_permissions()
    print("🎉 修复完成！")
