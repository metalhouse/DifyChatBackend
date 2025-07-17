"""
JWT认证系统演示脚本
"""
import os
import sys
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置环境变量
os.environ['FLASK_ENV'] = 'development'

from auth.auth_manager import AuthManager, TokenType
from auth.utils import validate_password_strength, create_session_token, generate_secure_token
from config import get_security_config

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def demo_jwt_auth():
    """JWT认证系统演示"""
    print("🚀 JWT认证系统演示")
    print("=" * 50)
    
    # 1. 初始化认证管理器
    print("\n1️⃣ 初始化认证管理器")
    auth_manager = AuthManager()
    print("✅ 认证管理器初始化完成")
    
    # 2. 生成令牌对
    print("\n2️⃣ 生成JWT令牌对")
    user_id = "demo_user_123"
    username = "demouser"
    device_id = "demo_device"
    ip_address = "192.168.1.100"
    
    token_pair = auth_manager.generate_token_pair(
        user_id=user_id,
        username=username,
        device_id=device_id,
        ip_address=ip_address
    )
    
    print(f"✅ 访问令牌: {token_pair['access_token'][:50]}...")
    print(f"✅ 刷新令牌: {token_pair['refresh_token'][:50]}...")
    print(f"✅ 令牌类型: {token_pair['token_type']}")
    print(f"✅ 过期时间: {token_pair['expires_in']}秒")
    print(f"✅ 设备ID: {token_pair['device_id']}")
    
    # 3. 验证令牌
    print("\n3️⃣ 验证JWT令牌")
    
    # 验证访问令牌
    access_token_info = auth_manager.verify_token(
        token_pair['access_token'], 
        TokenType.ACCESS
    )
    
    if access_token_info:
        print("✅ 访问令牌验证成功")
        print(f"   用户ID: {access_token_info.user_id}")
        print(f"   用户名: {access_token_info.username}")
        print(f"   令牌类型: {access_token_info.token_type}")
        print(f"   设备ID: {access_token_info.device_id}")
        print(f"   IP地址: {access_token_info.ip_address}")
    else:
        print("❌ 访问令牌验证失败")
    
    # 验证刷新令牌
    refresh_token_info = auth_manager.verify_token(
        token_pair['refresh_token'], 
        TokenType.REFRESH
    )
    
    if refresh_token_info:
        print("✅ 刷新令牌验证成功")
    else:
        print("❌ 刷新令牌验证失败")
    
    # 4. 刷新访问令牌
    print("\n4️⃣ 刷新访问令牌")
    
    import time
    time.sleep(1)  # 等待1秒确保时间戳不同
    
    new_tokens = auth_manager.refresh_access_token(token_pair['refresh_token'])
    
    if new_tokens:
        print("✅ 令牌刷新成功")
        print(f"   新访问令牌: {new_tokens['access_token'][:50]}...")
        print(f"   令牌不同: {new_tokens['access_token'] != token_pair['access_token']}")
        
        # 验证新令牌
        new_token_info = auth_manager.verify_token(new_tokens['access_token'])
        if new_token_info:
            print("✅ 新令牌验证成功")
        else:
            print("❌ 新令牌验证失败")
    else:
        print("❌ 令牌刷新失败")
    
    # 5. 用户会话管理
    print("\n5️⃣ 用户会话管理")
    
    # 生成多个会话
    session1 = auth_manager.generate_token_pair(user_id, username, "device1")
    session2 = auth_manager.generate_token_pair(user_id, username, "device2")
    
    active_sessions = auth_manager.get_user_active_sessions(user_id)
    print(f"✅ 用户活跃会话数: {active_sessions}")
    
    # 6. 令牌撤销
    print("\n6️⃣ 令牌撤销测试")
    
    # 撤销单个令牌
    revoked = auth_manager.revoke_token(session1['access_token'])
    print(f"✅ 单个令牌撤销: {'成功' if revoked else '失败'}")
    
    # 验证被撤销的令牌
    revoked_token_info = auth_manager.verify_token(session1['access_token'])
    print(f"✅ 被撤销令牌验证: {'失败(正确)' if not revoked_token_info else '成功(异常)'}")
    
    # 撤销用户所有会话
    revoked_count = auth_manager.revoke_user_sessions(user_id)
    print(f"✅ 撤销用户所有会话: {revoked_count}个")
    
    # 7. 密码强度验证
    print("\n7️⃣ 密码强度验证")
    
    passwords = [
        "123",
        "password",
        "Password123",
        "StrongPass123!"
    ]
    
    for pwd in passwords:
        result = validate_password_strength(pwd)
        strength = "强" if result['score'] >= 4 else "中" if result['score'] >= 2 else "弱"
        print(f"   密码 '{pwd}': {strength} (评分: {result['score']}/5, 有效: {result['is_valid']})")
    
    # 8. 安全令牌生成
    print("\n8️⃣ 安全令牌生成")
    
    secure_token = generate_secure_token()
    print(f"✅ 安全令牌: {secure_token[:30]}...")
    print(f"✅ 令牌长度: {len(secure_token)}")
    
    # 9. 安全配置检查
    print("\n9️⃣ 安全配置检查")
    
    security_config = get_security_config()
    print(f"✅ JWT密钥长度: {len(security_config.jwt_secret_key)}")
    print(f"✅ 访问令牌过期时间: {security_config.jwt_access_token_expires}秒")
    print(f"✅ 刷新令牌过期时间: {security_config.jwt_refresh_token_expires}秒")
    print(f"✅ 登录失败限制: {security_config.max_login_attempts}次")
    
    print("\n🎉 JWT认证系统演示完成！")
    print("=" * 50)


if __name__ == '__main__':
    try:
        demo_jwt_auth()
    except Exception as e:
        print(f"\n💥 演示运行异常: {str(e)}")
        import traceback
        traceback.print_exc()
