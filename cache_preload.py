#!/usr/bin/env python3
"""
智能体缓存预热脚本
用于在系统启动时预热缓存，提高性能
"""
import sys
import os
import time
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import create_config
from utils.cache_manager import init_cache_manager
from services.dify_service import DifyService


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def preload_agent_cache(config_name='development'):
    """预热智能体缓存"""
    print("=" * 60)
    print("智能体缓存预热脚本")
    print("=" * 60)
    
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # 加载配置
        config = create_config(config_name)
        logger.info(f"加载配置: {config_name}")
        
        # 初始化缓存管理器
        cache_manager = init_cache_manager(config)
        logger.info(f"缓存管理器状态: {'启用' if cache_manager.enabled else '禁用'}")
        
        if not cache_manager.enabled:
            logger.warning("缓存未启用，跳过预热")
            return
        
        # 创建服务实例
        dify_service = DifyService()
        
        # 检查缓存健康状态
        health_status = cache_manager.health_check()
        logger.info(f"缓存健康状态: {health_status['status']}")
        
        if health_status['status'] != 'healthy':
            logger.error("缓存不健康，无法预热")
            return
        
        # 执行预热
        logger.info("开始预热智能体缓存...")
        start_time = time.time()
        
        result = dify_service.preload_agent_cache()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 输出结果
        if result['status'] == 'completed':
            logger.info(f"预热完成！耗时: {duration:.2f}秒")
            logger.info(f"预热项目: {result['preloaded']} 个")
            logger.info(f"处理用户: {result['users']} 个")
            logger.info(f"处理智能体: {result['agents']} 个")
            
            if result['errors'] > 0:
                logger.warning(f"预热时发生错误: {result['errors']} 个")
        else:
            logger.error(f"预热失败: {result.get('message', '未知错误')}")
        
        # 显示缓存统计
        stats = dify_service.get_agent_cache_stats()
        if stats.get('enabled'):
            logger.info("缓存统计信息:")
            cache_stats = stats.get('agent_cache', {})
            cache_keys = cache_stats.get('cache_keys', {})
            
            for key_type, count in cache_keys.items():
                logger.info(f"  {key_type}: {count} 个缓存项")
        
        print("\n" + "=" * 60)
        print("✅ 智能体缓存预热完成")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"预热失败: {e}")
        print(f"\n❌ 预热失败: {e}")
        sys.exit(1)


def clear_agent_cache(config_name='development'):
    """清除智能体缓存"""
    print("=" * 60)
    print("清除智能体缓存")
    print("=" * 60)
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        config = create_config(config_name)
        cache_manager = init_cache_manager(config)
        dify_service = DifyService()
        
        if not cache_manager.enabled:
            logger.warning("缓存未启用")
            return
        
        # 清除所有智能体缓存
        dify_service.invalidate_agent_cache()
        logger.info("智能体缓存已清除")
        
        print("✅ 智能体缓存已清除")
        
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        print(f"❌ 清除缓存失败: {e}")


def show_cache_stats(config_name='development'):
    """显示缓存统计"""
    print("=" * 60)
    print("智能体缓存统计信息")
    print("=" * 60)
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        config = create_config(config_name)
        cache_manager = init_cache_manager(config)
        dify_service = DifyService()
        
        if not cache_manager.enabled:
            print("缓存未启用")
            return
        
        stats = dify_service.get_agent_cache_stats()
        
        if stats.get('enabled'):
            print("缓存状态: 启用")
            print(f"缓存类型: {stats.get('redis_mode', 'Unknown')}")
            
            # 基础统计
            if 'stats' in stats:
                base_stats = stats['stats']
                total_ops = base_stats.get('total_operations', 0)
                hit_rate = base_stats.get('hit_rate', 0.0)
                
                print(f"总操作数: {total_ops}")
                print(f"命中率: {hit_rate:.2%}")
                print(f"命中: {base_stats.get('hits', 0)}")
                print(f"未命中: {base_stats.get('misses', 0)}")
                print(f"设置: {base_stats.get('sets', 0)}")
                print(f"删除: {base_stats.get('deletes', 0)}")
                print(f"错误: {base_stats.get('errors', 0)}")
            
            # 智能体缓存统计
            if 'agent_cache' in stats:
                agent_stats = stats['agent_cache']
                print(f"\n智能体缓存TTL:")
                print(f"  智能体列表: {agent_stats.get('agent_cache_ttl', 0)} 秒")
                print(f"  用户权限: {agent_stats.get('permission_cache_ttl', 0)} 秒")
                
                cache_keys = agent_stats.get('cache_keys', {})
                print(f"\n缓存项统计:")
                for key_type, count in cache_keys.items():
                    print(f"  {key_type}: {count} 个")
        else:
            print("缓存未启用")
        
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        print(f"❌ 获取统计失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='智能体缓存管理工具')
    parser.add_argument('action', choices=['preload', 'clear', 'stats'], 
                       help='操作类型：preload=预热, clear=清除, stats=统计')
    parser.add_argument('--config', '-c', default='development',
                       choices=['development', 'testing', 'production'],
                       help='配置环境 (默认: development)')
    
    args = parser.parse_args()
    
    if args.action == 'preload':
        preload_agent_cache(args.config)
    elif args.action == 'clear':
        clear_agent_cache(args.config)
    elif args.action == 'stats':
        show_cache_stats(args.config)


if __name__ == '__main__':
    main()
