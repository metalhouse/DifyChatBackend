#!/usr/bin/env python3
"""
配置管理系统测试脚本
验证配置加载、验证、环境变量处理等功能
"""
import os
import sys
import tempfile
import shutil
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_config_loading():
    """测试配置加载"""
    print("1. 测试配置加载...")
    
    try:
        from config import get_config, reset_config
        
        # 重置配置以确保干净状态
        reset_config()
        
        # 设置必要的环境变量
        os.environ['DIFY_BASE_URL'] = 'http://test-dify.example.com/v1'
        os.environ['SECRET_KEY'] = 'test-secret-key'
        
        config = get_config()
        
        # 验证配置加载
        assert config.dify.base_url == 'http://test-dify.example.com/v1'
        assert config.security.secret_key == 'test-secret-key'
        assert config.env == 'development'  # 默认环境
        
        print("   ✓ 配置加载成功")
        return True
        
    except Exception as e:
        print(f"   ✗ 配置加载失败: {e}")
        return False

def test_config_validation():
    """测试配置验证"""
    print("2. 测试配置验证...")
    
    try:
        from config import create_config, reset_config
        
        # 测试无效日志级别
        reset_config()
        os.environ['DIFY_BASE_URL'] = 'http://test.com'
        os.environ['LOG_LEVEL'] = 'INVALID_LEVEL'
        
        try:
            create_config()
            print("   ✗ 应该抛出验证错误")
            return False
        except ValueError as e:
            if "无效的日志级别" in str(e):
                print("   ✓ 日志级别验证正确")
            else:
                print(f"   ✗ 意外的验证错误: {e}")
                return False
        
        # 测试无效端口
        reset_config()
        os.environ['LOG_LEVEL'] = 'INFO'
        os.environ['FLASK_PORT'] = '99999'
        
        try:
            create_config()
            print("   ✗ 应该抛出端口验证错误")
            return False
        except ValueError as e:
            if "无效的端口号" in str(e):
                print("   ✓ 端口验证正确")
            else:
                print(f"   ✗ 意外的端口错误: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ✗ 配置验证测试失败: {e}")
        return False

def test_environment_handling():
    """测试环境处理"""
    print("3. 测试环境处理...")
    
    try:
        from config import create_config, reset_config
        
        # 测试开发环境
        reset_config()
        os.environ['FLASK_ENV'] = 'development'
        os.environ['DIFY_BASE_URL'] = 'http://test.com'
        os.environ['FLASK_PORT'] = '5000'
        
        config = create_config()
        assert config.is_development()
        assert not config.is_production()
        print("   ✓ 开发环境识别正确")
        
        # 测试生产环境
        reset_config()
        os.environ['FLASK_ENV'] = 'production'
        os.environ['SECRET_KEY'] = 'prod-secret-key'
        
        config = create_config()
        assert config.is_production()
        assert not config.is_development()
        print("   ✓ 生产环境识别正确")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 环境处理测试失败: {e}")
        return False

def test_directory_creation():
    """测试目录创建"""
    print("4. 测试目录创建...")
    
    try:
        from config import create_config, reset_config
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        
        try:
            reset_config()
            os.environ['FLASK_ENV'] = 'testing'
            os.environ['DIFY_BASE_URL'] = 'http://test.com'
            os.environ['DATA_DIR'] = os.path.join(temp_dir, 'test_data')
            os.environ['LOG_DIR'] = os.path.join(temp_dir, 'test_logs')
            
            config = create_config()
            
            # 验证目录创建
            assert os.path.exists(config.database.data_dir)
            print("   ✓ 数据目录创建成功")
            
            # 验证日志目录
            log_dir = Path(config.logging.file_path).parent
            assert log_dir.exists()
            print("   ✓ 日志目录创建成功")
            
            return True
            
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"   ✗ 目录创建测试失败: {e}")
        return False

def test_flask_config():
    """测试Flask配置生成"""
    print("5. 测试Flask配置生成...")
    
    try:
        from config import get_config, reset_config
        
        reset_config()
        os.environ['DIFY_BASE_URL'] = 'http://test.com'
        os.environ['SECRET_KEY'] = 'flask-test-key'
        os.environ['FLASK_DEBUG'] = 'true'
        
        config = get_config()
        flask_config = config.get_flask_config()
        
        # 验证Flask配置
        assert flask_config['SECRET_KEY'] == 'flask-test-key'
        assert flask_config['DEBUG'] is True
        assert flask_config['JSON_AS_ASCII'] is False
        
        print("   ✓ Flask配置生成正确")
        return True
        
    except Exception as e:
        print(f"   ✗ Flask配置测试失败: {e}")
        return False

def test_config_access_functions():
    """测试配置访问函数"""
    print("6. 测试配置访问函数...")
    
    try:
        from config import (
            get_database_config, get_dify_config, get_security_config,
            get_logging_config, get_server_config, get_redis_config,
            reset_config
        )
        
        reset_config()
        os.environ['DIFY_BASE_URL'] = 'http://test.com'
        os.environ['SECRET_KEY'] = 'test-key'
        
        # 测试各个配置访问函数
        db_config = get_database_config()
        assert hasattr(db_config, 'users_file')
        print("   ✓ 数据库配置访问正确")
        
        dify_config = get_dify_config()
        assert dify_config.base_url == 'http://test.com'
        print("   ✓ Dify配置访问正确")
        
        security_config = get_security_config()
        assert security_config.secret_key == 'test-key'
        print("   ✓ 安全配置访问正确")
        
        logging_config = get_logging_config()
        assert hasattr(logging_config, 'level')
        print("   ✓ 日志配置访问正确")
        
        server_config = get_server_config()
        assert hasattr(server_config, 'host')
        print("   ✓ 服务器配置访问正确")
        
        redis_config = get_redis_config()
        assert hasattr(redis_config, 'enabled')
        print("   ✓ Redis配置访问正确")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 配置访问函数测试失败: {e}")
        return False

def cleanup_environment():
    """清理测试环境变量"""
    test_vars = [
        'DIFY_BASE_URL', 'SECRET_KEY', 'LOG_LEVEL', 'FLASK_PORT',
        'FLASK_ENV', 'DATA_DIR', 'LOG_DIR', 'FLASK_DEBUG'
    ]
    
    for var in test_vars:
        if var in os.environ:
            del os.environ[var]

def main():
    """主测试函数"""
    print("开始配置管理系统测试...\n")
    
    # 保存原始环境变量
    original_env = dict(os.environ)
    
    try:
        tests = [
            test_config_loading,
            test_config_validation,
            test_environment_handling,
            test_directory_creation,
            test_flask_config,
            test_config_access_functions
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
            print()
        
        print(f"测试结果: {passed}/{total} 通过")
        
        if passed == total:
            print("✓ 所有配置管理测试通过！")
            return True
        else:
            print("✗ 部分测试失败")
            return False
            
    finally:
        # 恢复原始环境变量
        os.environ.clear()
        os.environ.update(original_env)
        
        # 重置配置实例
        try:
            from config import reset_config
            reset_config()
        except:
            pass

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
