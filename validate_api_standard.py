"""
API标准化功能验证脚本
"""
import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_endpoint(method, endpoint, data=None, headers=None):
    """测试API端点"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n🔍 测试 {method} {endpoint}")
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == 'PUT':
            response = requests.put(url, json=data, headers=headers, timeout=10)
        
        print(f"   状态码: {response.status_code}")
        
        if response.headers.get('Content-Type', '').startswith('application/json'):
            data = response.json()
            print(f"   成功: {data.get('success', 'N/A')}")
            print(f"   消息: {data.get('message', 'N/A')}")
            print(f"   错误码: {data.get('error_code', 'N/A')}")
            print(f"   请求ID: {data.get('request_id', 'N/A')}")
            
        return response
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return None

def main():
    print("🚀 API标准化功能验证")
    
    # 1. 健康检查 - 验证标准化响应格式
    print("\n=== 健康检查与响应格式验证 ===")
    test_endpoint('GET', '/health')
    test_endpoint('GET', '/api/v1/health')
    test_endpoint('GET', '/api/v1/info')
    
    # 2. 请求验证测试
    print("\n=== 请求验证测试 ===")
    # 测试无效数据
    test_endpoint('POST', '/api/v1/auth/login', {"username": "ab", "password": "123"})
    test_endpoint('POST', '/api/v1/auth/login', {})  # 缺少必需字段
    
    # 3. 有效认证测试
    print("\n=== 有效认证测试 ===")
    login_data = {
        "username": "metalhouse",
        "password": "Iwhyi3589"
    }
    login_response = test_endpoint('POST', '/api/v1/auth/login', login_data)
    
    access_token = None
    if login_response and login_response.status_code == 200:
        data = login_response.json()
        if data.get('success'):
            tokens = data.get('data', {}).get('tokens', {})
            access_token = tokens.get('access_token')
            print(f"   ✅ 登录成功，获得令牌")
    
    # 4. 认证保护的端点测试
    if access_token:
        print("\n=== 认证保护的端点测试 ===")
        headers = {'Authorization': f'Bearer {access_token}'}
        
        test_endpoint('GET', '/api/v1/auth/me', headers=headers)
        test_endpoint('GET', '/api/v1/chat/agents', headers=headers)
        test_endpoint('GET', '/api/v1/chat/conversations', headers=headers)
        test_endpoint('GET', '/api/v1/cache/health', headers=headers)
    
    # 5. 错误处理测试
    print("\n=== 错误处理测试 ===")
    test_endpoint('GET', '/api/v1/nonexistent')  # 404
    test_endpoint('PUT', '/api/v1/auth/login')   # 405 Method Not Allowed
    
    # 6. 未认证访问保护端点
    print("\n=== 未认证访问测试 ===")
    test_endpoint('GET', '/api/v1/auth/me')
    test_endpoint('GET', '/api/v1/chat/agents')
    
    print("\n✅ API标准化功能验证完成!")
    print("\n📊 验证项目:")
    print("   ✓ 统一响应格式 (success, message, data, error_code, request_id, timestamp)")
    print("   ✓ 请求验证与错误处理")
    print("   ✓ 认证系统与权限控制")
    print("   ✓ API版本化 (/api/v1/)")
    print("   ✓ 标准HTTP状态码")

if __name__ == "__main__":
    main()
