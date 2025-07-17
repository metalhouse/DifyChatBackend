"""
JWT认证系统测试
"""
import pytest
import time
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from auth.auth_manager import AuthManager, TokenType, TokenInfo
from auth.utils import (
    generate_device_id, get_client_info, create_session_token,
    validate_password_strength, generate_secure_token
)
from auth.decorators import require_auth, require_refresh_token, optional_auth
from config import get_security_config

class TestAuthManager:
    """认证管理器测试"""
    
    def setup_method(self):
        """测试前的设置"""
        self.auth_manager = AuthManager()
        self.test_user_id = "test_user_123"
        self.test_username = "testuser"
        self.test_device_id = "device_123"
        self.test_ip = "192.168.1.100"
    
    def test_generate_token_pair(self):
        """测试生成令牌对"""
        token_pair = self.auth_manager.generate_token_pair(
            user_id=self.test_user_id,
            username=self.test_username,
            device_id=self.test_device_id,
            ip_address=self.test_ip
        )
        
        # 验证返回结构
        assert 'access_token' in token_pair
        assert 'refresh_token' in token_pair
        assert 'token_type' in token_pair
        assert 'expires_in' in token_pair
        assert 'issued_at' in token_pair
        assert 'device_id' in token_pair
        
        assert token_pair['token_type'] == 'Bearer'
        assert token_pair['device_id'] == self.test_device_id
        
        # 验证令牌可以解码
        access_payload = jwt.decode(
            token_pair['access_token'],
            self.auth_manager.security_config.jwt_secret_key,
            algorithms=['HS256']
        )
        
        assert access_payload['user_id'] == self.test_user_id
        assert access_payload['username'] == self.test_username
        assert access_payload['type'] == TokenType.ACCESS.value
        assert access_payload['device_id'] == self.test_device_id
        assert access_payload['ip_address'] == self.test_ip
    
    def test_verify_valid_token(self):
        """测试验证有效令牌"""
        token_pair = self.auth_manager.generate_token_pair(
            user_id=self.test_user_id,
            username=self.test_username,
            device_id=self.test_device_id,
            ip_address=self.test_ip
        )
        
        # 验证访问令牌
        token_info = self.auth_manager.verify_token(
            token_pair['access_token'], 
            TokenType.ACCESS
        )
        
        assert token_info is not None
        assert token_info.user_id == self.test_user_id
        assert token_info.username == self.test_username
        assert token_info.token_type == TokenType.ACCESS
        assert token_info.device_id == self.test_device_id
        assert token_info.ip_address == self.test_ip
        
        # 验证刷新令牌
        refresh_token_info = self.auth_manager.verify_token(
            token_pair['refresh_token'], 
            TokenType.REFRESH
        )
        
        assert refresh_token_info is not None
        assert refresh_token_info.token_type == TokenType.REFRESH
    
    def test_verify_invalid_token(self):
        """测试验证无效令牌"""
        # 无效令牌
        invalid_token = "invalid.token.here"
        token_info = self.auth_manager.verify_token(invalid_token)
        assert token_info is None
        
        # 错误的令牌类型
        token_pair = self.auth_manager.generate_token_pair(
            user_id=self.test_user_id,
            username=self.test_username
        )
        
        # 用访问令牌验证刷新令牌类型
        token_info = self.auth_manager.verify_token(
            token_pair['access_token'], 
            TokenType.REFRESH
        )
        assert token_info is None
    
    def test_verify_expired_token(self):
        """测试验证过期令牌"""
        # 创建已过期的令牌
        now = datetime.utcnow()
        past_time = now - timedelta(hours=1)
        
        payload = {
            'user_id': self.test_user_id,
            'username': self.test_username,
            'type': TokenType.ACCESS.value,
            'iat': int(past_time.timestamp()),
            'exp': int((past_time + timedelta(minutes=30)).timestamp()),
            'device_id': self.test_device_id,
            'ip_address': self.test_ip
        }
        
        expired_token = jwt.encode(
            payload,
            self.auth_manager.security_config.jwt_secret_key,
            algorithm='HS256'
        )
        
        token_info = self.auth_manager.verify_token(expired_token)
        assert token_info is None
    
    def test_refresh_access_token(self):
        """测试刷新访问令牌"""
        # 生成初始令牌对
        token_pair = self.auth_manager.generate_token_pair(
            user_id=self.test_user_id,
            username=self.test_username,
            device_id=self.test_device_id,
            ip_address=self.test_ip
        )
        
        # 使用刷新令牌生成新的访问令牌
        new_tokens = self.auth_manager.refresh_access_token(
            token_pair['refresh_token']
        )
        
        assert new_tokens is not None
        assert 'access_token' in new_tokens
        assert 'refresh_token' in new_tokens
        
        # 新令牌应该不同于原令牌
        assert new_tokens['access_token'] != token_pair['access_token']
        
        # 验证新令牌有效
        new_token_info = self.auth_manager.verify_token(
            new_tokens['access_token']
        )
        assert new_token_info is not None
        assert new_token_info.user_id == self.test_user_id
    
    def test_revoke_token(self):
        """测试撤销令牌"""
        token_pair = self.auth_manager.generate_token_pair(
            user_id=self.test_user_id,
            username=self.test_username
        )
        
        # 令牌应该有效
        token_info = self.auth_manager.verify_token(token_pair['access_token'])
        assert token_info is not None
        
        # 撤销令牌
        revoked = self.auth_manager.revoke_token(token_pair['access_token'])
        assert revoked is True
        
        # 令牌应该无效
        token_info = self.auth_manager.verify_token(token_pair['access_token'])
        assert token_info is None
    
    def test_revoke_user_sessions(self):
        """测试撤销用户所有会话"""
        # 生成多个令牌
        token_pair1 = self.auth_manager.generate_token_pair(
            user_id=self.test_user_id,
            username=self.test_username,
            device_id="device1"
        )
        
        token_pair2 = self.auth_manager.generate_token_pair(
            user_id=self.test_user_id,
            username=self.test_username,
            device_id="device2"
        )
        
        # 验证令牌有效
        assert self.auth_manager.verify_token(token_pair1['access_token']) is not None
        assert self.auth_manager.verify_token(token_pair2['access_token']) is not None
        
        # 撤销用户所有会话
        revoked_count = self.auth_manager.revoke_user_sessions(self.test_user_id)
        assert revoked_count == 2
        
        # 令牌应该都无效
        assert self.auth_manager.verify_token(token_pair1['access_token']) is None
        assert self.auth_manager.verify_token(token_pair2['access_token']) is None
    
    def test_get_user_active_sessions(self):
        """测试获取用户活跃会话数量"""
        # 初始没有会话
        session_count = self.auth_manager.get_user_active_sessions(self.test_user_id)
        assert session_count == 0
        
        # 生成一个令牌
        self.auth_manager.generate_token_pair(
            user_id=self.test_user_id,
            username=self.test_username
        )
        
        session_count = self.auth_manager.get_user_active_sessions(self.test_user_id)
        assert session_count == 1
        
        # 生成另一个令牌
        self.auth_manager.generate_token_pair(
            user_id=self.test_user_id,
            username=self.test_username
        )
        
        session_count = self.auth_manager.get_user_active_sessions(self.test_user_id)
        assert session_count == 2


class TestAuthUtils:
    """认证工具函数测试"""
    
    @patch('auth.utils.request')
    def test_generate_device_id(self, mock_request):
        """测试生成设备ID"""
        mock_request.headers.get.return_value = 'Mozilla/5.0 Test Browser'
        mock_request.remote_addr = '192.168.1.100'
        
        device_id = generate_device_id()
        
        assert isinstance(device_id, str)
        assert len(device_id) == 16
        
        # 相同输入应该生成不同的设备ID（因为包含时间戳）
        device_id2 = generate_device_id()
        assert device_id != device_id2
    
    @patch('auth.utils.request')
    def test_get_client_info(self, mock_request):
        """测试获取客户端信息"""
        mock_request.headers.get.return_value = 'Test User Agent'
        mock_request.remote_addr = '192.168.1.100'
        
        client_info = get_client_info()
        
        assert 'ip_address' in client_info
        assert 'user_agent' in client_info
        assert 'device_id' in client_info
        
        assert client_info['ip_address'] == '192.168.1.100'
        assert client_info['user_agent'] == 'Test User Agent'
        assert len(client_info['device_id']) == 16
    
    def test_validate_password_strength(self):
        """测试密码强度验证"""
        # 弱密码
        weak_result = validate_password_strength('123')
        assert weak_result['is_valid'] is False
        assert weak_result['score'] < 3
        assert len(weak_result['feedback']) > 0
        
        # 中等强度密码
        medium_result = validate_password_strength('Password123')
        assert medium_result['score'] >= 3
        
        # 强密码
        strong_result = validate_password_strength('StrongPass123!')
        assert strong_result['is_valid'] is True
        assert strong_result['score'] == 5
        assert len(strong_result['feedback']) == 0
        
        # 常见弱密码
        common_result = validate_password_strength('password')
        assert common_result['is_valid'] is False
        assert 'password过于简单' in ' '.join(common_result['feedback'])
    
    def test_generate_secure_token(self):
        """测试生成安全令牌"""
        token1 = generate_secure_token()
        token2 = generate_secure_token()
        
        # 应该生成不同的令牌
        assert token1 != token2
        
        # 默认长度
        assert len(token1) > 40  # URL安全base64编码会比原始长度长
        
        # 指定长度
        short_token = generate_secure_token(16)
        assert len(short_token) > 20


class TestAuthDecorators:
    """认证装饰器测试"""
    
    def setup_method(self):
        """测试前的设置"""
        self.auth_manager = AuthManager()
        self.test_user_id = "test_user_123"
        self.test_username = "testuser"
    
    @patch('auth.decorators.request')
    @patch('auth.decorators.g')
    def test_require_auth_with_valid_token(self, mock_g, mock_request):
        """测试有效令牌的认证装饰器"""
        # 生成有效令牌
        token_pair = self.auth_manager.generate_token_pair(
            user_id=self.test_user_id,
            username=self.test_username
        )
        
        # 模拟请求头
        mock_request.headers.get.return_value = f"Bearer {token_pair['access_token']}"
        
        # 创建测试函数
        @require_auth()
        def test_endpoint():
            return {'message': 'success'}
        
        # 执行测试
        result = test_endpoint()
        
        # 验证结果
        assert result == {'message': 'success'}
        
        # 验证用户信息被设置到g对象
        assert hasattr(mock_g, 'current_user')
    
    @patch('auth.decorators.request')
    def test_require_auth_without_token(self, mock_request):
        """测试缺少令牌的认证装饰器"""
        # 没有Authorization头
        mock_request.headers.get.return_value = None
        
        @require_auth()
        def test_endpoint():
            return {'message': 'success'}
        
        # 执行测试，应该返回401错误
        result, status_code = test_endpoint()
        
        assert status_code == 401
        assert result['success'] is False
        assert result['error_code'] == 'MISSING_TOKEN'
    
    @patch('auth.decorators.request')
    def test_require_auth_with_invalid_token(self, mock_request):
        """测试无效令牌的认证装饰器"""
        # 无效令牌
        mock_request.headers.get.return_value = "Bearer invalid.token.here"
        
        @require_auth()
        def test_endpoint():
            return {'message': 'success'}
        
        # 执行测试，应该返回401错误
        result, status_code = test_endpoint()
        
        assert status_code == 401
        assert result['success'] is False
        assert result['error_code'] == 'INVALID_TOKEN'
    
    @patch('auth.decorators.request')
    @patch('auth.decorators.g')
    def test_optional_auth_without_token(self, mock_g, mock_request):
        """测试可选认证装饰器（无令牌）"""
        # 没有Authorization头
        mock_request.headers.get.return_value = None
        
        @optional_auth()
        def test_endpoint():
            return {'message': 'success'}
        
        # 执行测试，应该成功
        result = test_endpoint()
        
        assert result == {'message': 'success'}
        # 用户信息应该为None
        assert mock_g.current_user is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
