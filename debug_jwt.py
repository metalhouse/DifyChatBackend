"""
JWT令牌调试脚本
"""
import jwt
import os
import sys
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置环境变量
os.environ['FLASK_ENV'] = 'development'

from config import get_security_config

def debug_jwt_token():
    """调试JWT令牌生成和验证"""
    print("🔍 JWT令牌调试")
    print("=" * 50)
    
    security_config = get_security_config()
    print(f"JWT密钥: {security_config.jwt_secret_key[:20]}...")
    print(f"访问令牌过期时间: {security_config.jwt_access_token_expires}秒")
    
    # 1. 手动生成令牌
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=security_config.jwt_access_token_expires)
    
    print(f"\n当前时间: {now}")
    print(f"过期时间: {expires_at}")
    print(f"时间差: {(expires_at - now).total_seconds()}秒")
    
    payload = {
        'user_id': 'test_user',
        'username': 'testuser',
        'type': 'access',
        'iat': int(now.timestamp()),
        'exp': int(expires_at.timestamp()),
        'device_id': 'test_device',
        'ip_address': '192.168.1.100'
    }
    
    print(f"\nPayload:")
    for key, value in payload.items():
        if key in ['iat', 'exp']:
            dt = datetime.fromtimestamp(value)
            print(f"  {key}: {value} ({dt})")
        else:
            print(f"  {key}: {value}")
    
    # 2. 编码令牌
    token = jwt.encode(
        payload,
        security_config.jwt_secret_key,
        algorithm='HS256'
    )
    
    print(f"\n生成的令牌: {token[:50]}...")
    
    # 3. 立即验证令牌
    try:
        decoded = jwt.decode(
            token,
            security_config.jwt_secret_key,
            algorithms=['HS256']
        )
        print(f"\n✅ 令牌验证成功:")
        for key, value in decoded.items():
            if key in ['iat', 'exp']:
                dt = datetime.fromtimestamp(value)
                print(f"  {key}: {value} ({dt})")
            else:
                print(f"  {key}: {value}")
        
        # 检查过期时间
        current_timestamp = datetime.utcnow().timestamp()
        exp_timestamp = decoded['exp']
        time_to_expire = exp_timestamp - current_timestamp
        
        print(f"\n⏰ 时间检查:")
        print(f"  当前时间戳: {current_timestamp}")
        print(f"  过期时间戳: {exp_timestamp}")
        print(f"  剩余时间: {time_to_expire}秒")
        
        if time_to_expire > 0:
            print("✅ 令牌未过期")
        else:
            print("❌ 令牌已过期")
            
    except jwt.ExpiredSignatureError:
        print("❌ 令牌已过期（JWT异常）")
    except jwt.InvalidTokenError as e:
        print(f"❌ 令牌无效: {e}")
    
    # 4. 等待几秒后再次验证
    print(f"\n⏳ 等待2秒后再次验证...")
    import time
    time.sleep(2)
    
    try:
        decoded2 = jwt.decode(
            token,
            security_config.jwt_secret_key,
            algorithms=['HS256']
        )
        print("✅ 2秒后令牌验证成功")
        
        current_timestamp2 = datetime.utcnow().timestamp()
        time_to_expire2 = decoded2['exp'] - current_timestamp2
        print(f"  剩余时间: {time_to_expire2}秒")
        
    except jwt.ExpiredSignatureError:
        print("❌ 2秒后令牌已过期")
    except jwt.InvalidTokenError as e:
        print(f"❌ 2秒后令牌无效: {e}")


if __name__ == '__main__':
    debug_jwt_token()
