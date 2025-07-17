"""
简化的JWT测试脚本
"""
import os
import sys
import jwt
from datetime import datetime, timedelta, timezone

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置环境变量
os.environ['FLASK_ENV'] = 'development'

def simple_jwt_test():
    """简化的JWT测试"""
    print("🧪 简化JWT测试")
    print("=" * 40)
    
    # 使用简单的密钥
    secret_key = "test-secret-key-for-jwt-authentication"
    print(f"密钥长度: {len(secret_key)}")
    
    # 当前时间
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=300)  # 5分钟后过期
    
    print(f"当前时间: {now}")
    print(f"过期时间: {expires}")
    
    # 创建payload
    payload = {
        'user_id': 'test_user',
        'username': 'testuser',
        'type': 'access',
        'iat': int(now.timestamp()),
        'exp': int(expires.timestamp())
    }
    
    print(f"\nPayload: {payload}")
    
    # 生成令牌
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    print(f"\n生成令牌: {token[:50]}...")
    
    # 立即验证
    try:
        decoded = jwt.decode(token, secret_key, algorithms=['HS256'])
        print(f"\n✅ 验证成功: {decoded}")
        
        # 检查过期时间
        current_ts = datetime.now(timezone.utc).timestamp()
        exp_ts = decoded['exp']
        remaining = exp_ts - current_ts
        
        print(f"剩余时间: {remaining:.2f}秒")
        
        if remaining > 0:
            print("✅ 令牌有效")
        else:
            print("❌ 令牌过期")
            
    except jwt.ExpiredSignatureError:
        print("❌ 令牌已过期")
    except jwt.InvalidTokenError as e:
        print(f"❌ 令牌无效: {e}")
    
    # 测试过期令牌
    print(f"\n🕐 测试过期令牌")
    old_payload = {
        'user_id': 'test_user',
        'username': 'testuser',
        'type': 'access',
        'iat': int((now - timedelta(hours=2)).timestamp()),
        'exp': int((now - timedelta(hours=1)).timestamp())  # 1小时前过期
    }
    
    old_token = jwt.encode(old_payload, secret_key, algorithm='HS256')
    
    try:
        jwt.decode(old_token, secret_key, algorithms=['HS256'])
        print("❌ 过期令牌验证成功（异常）")
    except jwt.ExpiredSignatureError:
        print("✅ 过期令牌正确被拒绝")
    except jwt.InvalidTokenError as e:
        print(f"✅ 过期令牌被拒绝: {e}")

if __name__ == '__main__':
    simple_jwt_test()
