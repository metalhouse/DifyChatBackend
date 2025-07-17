"""
JWT认证系统测试脚本（不依赖pytest）
"""
import sys
import os
import time
import traceback

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth.auth_manager import AuthManager, TokenType
from auth.utils import validate_password_strength, generate_secure_token
from config import get_security_config


class AuthTestRunner:
    """认证系统测试运行器"""
    
    def __init__(self):
        self.auth_manager = AuthManager()
        self.test_user_id = "test_user_123"
        self.test_username = "testuser"
        self.test_device_id = "device_123"
        self.test_ip = "192.168.1.100"
        
        self.passed = 0
        self.failed = 0
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始JWT认证系统测试...\n")
        
        # 基础功能测试
        self.test_generate_token_pair()
        self.test_verify_valid_token()
        self.test_verify_invalid_token()
        self.test_refresh_access_token()
        self.test_revoke_token()
        self.test_revoke_user_sessions()
        self.test_user_active_sessions()
        
        # 工具函数测试
        self.test_password_strength_validation()
        self.test_secure_token_generation()
        
        # 配置测试
        self.test_security_config()
        
        print(f"\n📊 测试结果:")
        print(f"✅ 通过: {self.passed}")
        print(f"❌ 失败: {self.failed}")
        print(f"📈 成功率: {self.passed/(self.passed+self.failed)*100:.1f}%")
        
        return self.failed == 0
    
    def assert_test(self, condition, test_name, message=""):
        """测试断言"""
        try:
            if condition:
                print(f"✅ {test_name}")
                self.passed += 1
            else:
                print(f"❌ {test_name}: {message}")
                self.failed += 1
        except Exception as e:
            print(f"❌ {test_name}: 异常 - {str(e)}")
            self.failed += 1
    
    def test_generate_token_pair(self):
        """测试生成令牌对"""
        try:
            token_pair = self.auth_manager.generate_token_pair(
                user_id=self.test_user_id,
                username=self.test_username,
                device_id=self.test_device_id,
                ip_address=self.test_ip
            )
            
            # 检查返回结构
            required_keys = ['access_token', 'refresh_token', 'token_type', 'expires_in', 'issued_at', 'device_id']
            has_all_keys = all(key in token_pair for key in required_keys)
            
            self.assert_test(
                has_all_keys,
                "生成令牌对 - 结构完整性",
                f"缺少必要字段: {[k for k in required_keys if k not in token_pair]}"
            )
            
            self.assert_test(
                token_pair['token_type'] == 'Bearer',
                "生成令牌对 - 令牌类型",
                f"期望Bearer，实际{token_pair.get('token_type')}"
            )
            
            self.assert_test(
                len(token_pair['access_token']) > 100,
                "生成令牌对 - 访问令牌长度",
                "访问令牌长度过短"
            )
            
            self.assert_test(
                len(token_pair['refresh_token']) > 100,
                "生成令牌对 - 刷新令牌长度",
                "刷新令牌长度过短"
            )
            
        except Exception as e:
            self.assert_test(False, "生成令牌对", f"异常: {str(e)}")
    
    def test_verify_valid_token(self):
        """测试验证有效令牌"""
        try:
            # 生成令牌
            token_pair = self.auth_manager.generate_token_pair(
                user_id=self.test_user_id,
                username=self.test_username,
                device_id=self.test_device_id,
                ip_address=self.test_ip
            )
            
            # 验证访问令牌
            access_token_info = self.auth_manager.verify_token(
                token_pair['access_token'], 
                TokenType.ACCESS
            )
            
            self.assert_test(
                access_token_info is not None,
                "验证有效令牌 - 访问令牌验证",
                "访问令牌验证失败"
            )
            
            if access_token_info:
                self.assert_test(
                    access_token_info.user_id == self.test_user_id,
                    "验证有效令牌 - 用户ID匹配",
                    f"期望{self.test_user_id}，实际{access_token_info.user_id}"
                )
                
                self.assert_test(
                    access_token_info.username == self.test_username,
                    "验证有效令牌 - 用户名匹配",
                    f"期望{self.test_username}，实际{access_token_info.username}"
                )
                
                self.assert_test(
                    access_token_info.token_type == TokenType.ACCESS,
                    "验证有效令牌 - 令牌类型匹配",
                    f"期望{TokenType.ACCESS}，实际{access_token_info.token_type}"
                )
            
            # 验证刷新令牌
            refresh_token_info = self.auth_manager.verify_token(
                token_pair['refresh_token'], 
                TokenType.REFRESH
            )
            
            self.assert_test(
                refresh_token_info is not None,
                "验证有效令牌 - 刷新令牌验证",
                "刷新令牌验证失败"
            )
            
        except Exception as e:
            self.assert_test(False, "验证有效令牌", f"异常: {str(e)}")
    
    def test_verify_invalid_token(self):
        """测试验证无效令牌"""
        try:
            # 完全无效的令牌
            invalid_result = self.auth_manager.verify_token("invalid.token.here")
            self.assert_test(
                invalid_result is None,
                "验证无效令牌 - 格式错误令牌",
                "应该返回None"
            )
            
            # 类型不匹配
            token_pair = self.auth_manager.generate_token_pair(
                user_id=self.test_user_id,
                username=self.test_username
            )
            
            wrong_type_result = self.auth_manager.verify_token(
                token_pair['access_token'], 
                TokenType.REFRESH
            )
            
            self.assert_test(
                wrong_type_result is None,
                "验证无效令牌 - 类型不匹配",
                "应该返回None"
            )
            
        except Exception as e:
            self.assert_test(False, "验证无效令牌", f"异常: {str(e)}")
    
    def test_refresh_access_token(self):
        """测试刷新访问令牌"""
        try:
            # 生成初始令牌对
            token_pair = self.auth_manager.generate_token_pair(
                user_id=self.test_user_id,
                username=self.test_username
            )
            
            # 使用刷新令牌生成新的访问令牌
            new_tokens = self.auth_manager.refresh_access_token(
                token_pair['refresh_token']
            )
            
            self.assert_test(
                new_tokens is not None,
                "刷新访问令牌 - 刷新成功",
                "刷新令牌失败"
            )
            
            if new_tokens:
                self.assert_test(
                    'access_token' in new_tokens and 'refresh_token' in new_tokens,
                    "刷新访问令牌 - 返回结构",
                    "缺少必要的令牌字段"
                )
                
                self.assert_test(
                    new_tokens['access_token'] != token_pair['access_token'],
                    "刷新访问令牌 - 令牌更新",
                    "新令牌应该与原令牌不同"
                )
                
                # 验证新令牌有效
                new_token_info = self.auth_manager.verify_token(
                    new_tokens['access_token']
                )
                
                self.assert_test(
                    new_token_info is not None and new_token_info.user_id == self.test_user_id,
                    "刷新访问令牌 - 新令牌有效性",
                    "新令牌验证失败"
                )
            
        except Exception as e:
            self.assert_test(False, "刷新访问令牌", f"异常: {str(e)}")
    
    def test_revoke_token(self):
        """测试撤销令牌"""
        try:
            token_pair = self.auth_manager.generate_token_pair(
                user_id=self.test_user_id,
                username=self.test_username
            )
            
            # 令牌应该有效
            before_revoke = self.auth_manager.verify_token(token_pair['access_token'])
            self.assert_test(
                before_revoke is not None,
                "撤销令牌 - 撤销前验证",
                "令牌在撤销前应该有效"
            )
            
            # 撤销令牌
            revoked = self.auth_manager.revoke_token(token_pair['access_token'])
            self.assert_test(
                revoked is True,
                "撤销令牌 - 撤销操作",
                "撤销操作应该成功"
            )
            
            # 令牌应该无效
            after_revoke = self.auth_manager.verify_token(token_pair['access_token'])
            self.assert_test(
                after_revoke is None,
                "撤销令牌 - 撤销后验证",
                "令牌在撤销后应该无效"
            )
            
        except Exception as e:
            self.assert_test(False, "撤销令牌", f"异常: {str(e)}")
    
    def test_revoke_user_sessions(self):
        """测试撤销用户所有会话"""
        try:
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
            before_revoke1 = self.auth_manager.verify_token(token_pair1['access_token'])
            before_revoke2 = self.auth_manager.verify_token(token_pair2['access_token'])
            
            self.assert_test(
                before_revoke1 is not None and before_revoke2 is not None,
                "撤销用户会话 - 撤销前验证",
                "所有令牌在撤销前应该有效"
            )
            
            # 撤销用户所有会话
            revoked_count = self.auth_manager.revoke_user_sessions(self.test_user_id)
            self.assert_test(
                revoked_count == 2,
                "撤销用户会话 - 撤销数量",
                f"期望撤销2个，实际撤销{revoked_count}个"
            )
            
            # 令牌应该都无效
            after_revoke1 = self.auth_manager.verify_token(token_pair1['access_token'])
            after_revoke2 = self.auth_manager.verify_token(token_pair2['access_token'])
            
            self.assert_test(
                after_revoke1 is None and after_revoke2 is None,
                "撤销用户会话 - 撤销后验证",
                "所有令牌在撤销后应该无效"
            )
            
        except Exception as e:
            self.assert_test(False, "撤销用户会话", f"异常: {str(e)}")
    
    def test_user_active_sessions(self):
        """测试用户活跃会话管理"""
        try:
            # 初始没有会话
            initial_count = self.auth_manager.get_user_active_sessions(self.test_user_id)
            self.assert_test(
                initial_count == 0,
                "用户活跃会话 - 初始状态",
                f"期望0个会话，实际{initial_count}个"
            )
            
            # 生成一个令牌
            self.auth_manager.generate_token_pair(
                user_id=self.test_user_id,
                username=self.test_username
            )
            
            after_one = self.auth_manager.get_user_active_sessions(self.test_user_id)
            self.assert_test(
                after_one == 1,
                "用户活跃会话 - 单个会话",
                f"期望1个会话，实际{after_one}个"
            )
            
            # 生成另一个令牌
            self.auth_manager.generate_token_pair(
                user_id=self.test_user_id,
                username=self.test_username
            )
            
            after_two = self.auth_manager.get_user_active_sessions(self.test_user_id)
            self.assert_test(
                after_two == 2,
                "用户活跃会话 - 多个会话",
                f"期望2个会话，实际{after_two}个"
            )
            
        except Exception as e:
            self.assert_test(False, "用户活跃会话", f"异常: {str(e)}")
    
    def test_password_strength_validation(self):
        """测试密码强度验证"""
        try:
            # 弱密码测试
            weak_result = validate_password_strength('123')
            self.assert_test(
                weak_result['is_valid'] is False,
                "密码强度验证 - 弱密码识别",
                "弱密码应该被识别为无效"
            )
            
            # 强密码测试
            strong_result = validate_password_strength('StrongPass123!')
            self.assert_test(
                strong_result['is_valid'] is True,
                "密码强度验证 - 强密码识别",
                "强密码应该被识别为有效"
            )
            
            self.assert_test(
                strong_result['score'] == 5,
                "密码强度验证 - 强密码评分",
                f"期望评分5，实际{strong_result['score']}"
            )
            
            # 常见弱密码测试
            common_result = validate_password_strength('password')
            self.assert_test(
                common_result['is_valid'] is False,
                "密码强度验证 - 常见弱密码",
                "常见弱密码应该被拒绝"
            )
            
        except Exception as e:
            self.assert_test(False, "密码强度验证", f"异常: {str(e)}")
    
    def test_secure_token_generation(self):
        """测试安全令牌生成"""
        try:
            token1 = generate_secure_token()
            token2 = generate_secure_token()
            
            self.assert_test(
                token1 != token2,
                "安全令牌生成 - 唯一性",
                "生成的令牌应该不同"
            )
            
            self.assert_test(
                len(token1) > 40,
                "安全令牌生成 - 长度检查",
                f"令牌长度过短: {len(token1)}"
            )
            
            # 指定长度测试
            short_token = generate_secure_token(16)
            self.assert_test(
                len(short_token) > 20,
                "安全令牌生成 - 自定义长度",
                f"短令牌长度: {len(short_token)}"
            )
            
        except Exception as e:
            self.assert_test(False, "安全令牌生成", f"异常: {str(e)}")
    
    def test_security_config(self):
        """测试安全配置"""
        try:
            security_config = get_security_config()
            
            self.assert_test(
                hasattr(security_config, 'jwt_secret_key'),
                "安全配置 - JWT密钥存在",
                "JWT密钥配置缺失"
            )
            
            self.assert_test(
                len(security_config.jwt_secret_key) >= 32,
                "安全配置 - JWT密钥长度",
                f"JWT密钥长度不足: {len(security_config.jwt_secret_key)}"
            )
            
            self.assert_test(
                security_config.jwt_access_token_expires > 0,
                "安全配置 - 访问令牌过期时间",
                f"访问令牌过期时间配置: {security_config.jwt_access_token_expires}"
            )
            
            self.assert_test(
                security_config.jwt_refresh_token_expires > security_config.jwt_access_token_expires,
                "安全配置 - 刷新令牌过期时间",
                "刷新令牌过期时间应该大于访问令牌"
            )
            
        except Exception as e:
            self.assert_test(False, "安全配置", f"异常: {str(e)}")


if __name__ == '__main__':
    print("🚀 JWT认证系统测试启动")
    print("=" * 50)
    
    try:
        test_runner = AuthTestRunner()
        success = test_runner.run_all_tests()
        
        if success:
            print("\n🎉 所有测试通过！JWT认证系统运行正常。")
            sys.exit(0)
        else:
            print(f"\n⚠️  有 {test_runner.failed} 个测试失败，请检查相关功能。")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 测试运行异常: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
