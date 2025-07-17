#!/usr/bin/env python3
"""
Redis连接详细诊断
"""
import os
import sys
from pathlib import Path
import redis
import traceback

# 设置环境变量
os.environ['REDIS_ENABLED'] = 'true'
os.environ['REDIS_HOST'] = '192.168.1.195'
os.environ['REDIS_PORT'] = '6379'
os.environ['REDIS_DB'] = '0'

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def test_direct_redis_connection():
    """直接测试Redis连接"""
    print("🔍 直接Redis连接测试")
    print("=" * 40)
    
    host = '192.168.1.195'
    port = 6379
    db = 0
    
    try:
        # 创建Redis客户端
        r = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        
        print(f"连接参数: {host}:{port}/{db}")
        
        # 测试ping
        result = r.ping()
        print(f"Ping测试: {result}")
        
        # 测试基本操作
        test_key = "test:direct:connection"
        r.set(test_key, "Hello Redis!")
        value = r.get(test_key)
        print(f"设置/获取测试: {value}")
        
        # 清理测试键
        r.delete(test_key)
        
        # 获取Redis信息
        info = r.info()
        print(f"Redis版本: {info.get('redis_version', 'Unknown')}")
        print(f"已连接客户端: {info.get('connected_clients', 'Unknown')}")
        
        print("✅ 直接Redis连接成功！")
        return True
        
    except Exception as e:
        print(f"❌ 直接Redis连接失败: {e}")
        traceback.print_exc()
        return False

def test_config_loading():
    """测试配置加载"""
    print("\n🔧 配置加载测试")
    print("=" * 40)
    
    try:
        from config import create_config
        
        config = create_config('development')
        redis_config = config.redis
        
        print(f"Redis启用: {redis_config.enabled}")
        print(f"Redis主机: {redis_config.host}")
        print(f"Redis端口: {redis_config.port}")
        print(f"Redis数据库: {redis_config.db}")
        print(f"Redis密码: {'设置' if redis_config.password else '未设置'}")
        print(f"超时设置: {redis_config.socket_timeout}s")
        print(f"最大连接数: {redis_config.connection_pool_max_connections}")
        
        print("✅ 配置加载成功！")
        return config
        
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        traceback.print_exc()
        return None

def test_cache_manager_step_by_step(config):
    """逐步测试CacheManager"""
    print("\n🏗️ CacheManager逐步测试")
    print("=" * 40)
    
    try:
        from utils.cache_manager import CacheManager, REDIS_AVAILABLE
        
        print(f"Redis可用性: {REDIS_AVAILABLE}")
        
        if not REDIS_AVAILABLE:
            print("❌ Redis模块不可用")
            return False
        
        # 创建CacheManager
        cache = CacheManager(config)
        
        print(f"缓存启用状态: {cache._enabled}")
        print(f"Redis客户端: {cache._client}")
        print(f"连接池: {cache._pool}")
        
        if cache.enabled:
            print("✅ CacheManager初始化成功！")
            
            # 测试基本操作
            test_key = "test:cache:manager"
            test_value = {"message": "CacheManager测试", "number": 123}
            
            cache.set(test_key, test_value, ttl=60)
            retrieved = cache.get(test_key)
            
            print(f"缓存测试: {retrieved}")
            
            if retrieved == test_value:
                print("✅ CacheManager功能测试通过！")
                cache.delete(test_key)
                return True
            else:
                print("❌ CacheManager功能测试失败")
                return False
        else:
            print("❌ CacheManager未启用")
            return False
            
    except Exception as e:
        print(f"❌ CacheManager测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🚀 Redis连接详细诊断")
    print("=" * 60)
    
    # 1. 直接Redis连接测试
    direct_success = test_direct_redis_connection()
    
    # 2. 配置加载测试
    config = test_config_loading()
    
    # 3. CacheManager测试
    if config:
        cache_success = test_cache_manager_step_by_step(config)
    else:
        cache_success = False
    
    # 总结
    print("\n📋 诊断总结")
    print("=" * 40)
    print(f"直接Redis连接: {'✅ 成功' if direct_success else '❌ 失败'}")
    print(f"配置加载: {'✅ 成功' if config else '❌ 失败'}")
    print(f"CacheManager: {'✅ 成功' if cache_success else '❌ 失败'}")
    
    if direct_success and config and cache_success:
        print("\n🎉 所有测试通过！Redis连接完全正常！")
    else:
        print("\n⚠️ 存在问题，需要进一步调试")

if __name__ == "__main__":
    main()
