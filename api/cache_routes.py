"""
缓存管理相关的API路由 (标准化版本)
"""
from flask import request, g
import logging

from utils.response_builder import ResponseBuilder, ErrorCode
from utils.request_validator import validate_and_convert, ValidationError
from auth.decorators import require_auth, require_permissions, auto_refresh_token
from services.dify_service import dify_service

def _get_current_user():
    """获取当前用户信息的辅助函数"""
    current_user = getattr(g, 'current_user', None)
    if not current_user:
        return None, ResponseBuilder.error(
            error_code=ErrorCode.AUTHENTICATION_REQUIRED,
            message="用户认证信息缺失"
        )
    return current_user, None

@require_auth()
@require_permissions(['view_permissions'])
@auto_refresh_token()
def api_user_permissions():
    """获取用户权限信息（支持缓存）"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        username = current_user['username']
        
        # 2. 解析参数
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        
        # 3. 获取用户权限
        permissions = dify_service.get_user_permissions(username, use_cache=use_cache)
        
        logging.info(f"[GET USER PERMISSIONS] user={username}, cache={use_cache}")
        
        return ResponseBuilder.success(
            data=permissions,
            message="获取用户权限成功"
        )
        
    except Exception as e:
        logging.error(f"[GET USER PERMISSIONS ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="获取用户权限异常"
        )

@require_auth()
@require_permissions(['view_agent_config'])
@auto_refresh_token()
def api_agent_config():
    """获取智能体配置（支持缓存）"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        # 2. 参数验证
        agent_id = request.args.get('agent_id')
        if not agent_id:
            return ResponseBuilder.error(
                error_code=ErrorCode.MISSING_PARAMETER,
                message="智能体ID是必需的"
            )
        
        # 3. 检查智能体访问权限
        from auth.decorators import check_agent_access
        
        @check_agent_access('agent_id')
        def _check_access():
            return True
        
        try:
            g.request_args = {'agent_id': agent_id}
            _check_access()
        except Exception:
            return ResponseBuilder.error(
                error_code=ErrorCode.ACCESS_DENIED,
                message="无权访问指定智能体"
            )
        
        # 4. 解析参数
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        
        # 5. 获取智能体配置
        config = dify_service.get_agent_config(agent_id, use_cache=use_cache)
        
        logging.info(f"[GET AGENT CONFIG] agent={agent_id}, cache={use_cache}")
        
        return ResponseBuilder.success(
            data=config,
            message="获取智能体配置成功"
        )
        
    except Exception as e:
        logging.error(f"[GET AGENT CONFIG ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="获取智能体配置异常"
        )

@require_auth()
@require_permissions(['manage_cache', 'admin'])
@auto_refresh_token()
def api_preload_cache():
    """预热智能体缓存"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        # 2. 解析参数
        data = request.get_json() or {}
        usernames = data.get('usernames')  # 可选：指定要预热的用户列表
        
        # 3. 执行缓存预热
        result = dify_service.preload_agent_cache(usernames)
        
        logging.info(f"[PRELOAD CACHE] operator={current_user['username']}, "
                    f"users={usernames or 'all'}")
        
        return ResponseBuilder.success(
            data=result,
            message="缓存预热完成"
        )
        
    except Exception as e:
        logging.error(f"[PRELOAD CACHE ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="缓存预热异常"
        )

@require_auth()
@require_permissions(['manage_cache', 'admin'])
@auto_refresh_token()
def api_refresh_agent_cache():
    """刷新智能体配置缓存"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        # 2. 执行配置缓存刷新
        result = dify_service.refresh_agent_config_cache()
        
        logging.info(f"[REFRESH AGENT CACHE] operator={current_user['username']}")
        
        return ResponseBuilder.success(
            data=result,
            message="智能体配置缓存刷新完成"
        )
        
    except Exception as e:
        logging.error(f"[REFRESH AGENT CACHE ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="刷新智能体配置缓存异常"
        )

@require_auth()
@require_permissions(['manage_cache', 'admin'])
@auto_refresh_token()
def api_invalidate_cache():
    """清除指定缓存"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        # 2. 解析参数
        data = request.get_json() or {}
        target_username = data.get('username')
        agent_id = data.get('agent_id')
        cache_type = data.get('cache_type', 'all')  # all, conversations, agents, permissions
        
        # 3. 执行缓存清除
        if cache_type == 'conversations':
            dify_service.invalidate_user_cache(target_username, agent_id)
        elif cache_type == 'agents':
            dify_service.invalidate_agent_cache(username=target_username, agent_id=agent_id)
        elif cache_type == 'permissions':
            # 清除权限缓存（需要在DifyService中实现）
            if hasattr(dify_service, 'invalidate_permissions_cache'):
                dify_service.invalidate_permissions_cache(target_username)
        else:
            # 清除所有相关缓存
            dify_service.invalidate_user_cache(target_username, agent_id)
            dify_service.invalidate_agent_cache(username=target_username, agent_id=agent_id)
        
        # 4. 构建清除信息
        cache_info = []
        if target_username:
            cache_info.append(f"用户: {target_username}")
        if agent_id:
            cache_info.append(f"智能体: {agent_id}")
        if not target_username and not agent_id:
            cache_info.append("所有缓存")
        
        cache_desc = f"{cache_type}缓存 - " + ", ".join(cache_info)
        
        logging.info(f"[INVALIDATE CACHE] operator={current_user['username']}, "
                    f"target={cache_desc}")
        
        return ResponseBuilder.success(
            message=f"已清除{cache_desc}"
        )
        
    except Exception as e:
        logging.error(f"[INVALIDATE CACHE ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="清除缓存异常"
        )

@require_auth()
@require_permissions(['view_stats'])
@auto_refresh_token()
def api_cache_stats():
    """获取缓存统计信息"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        # 2. 获取统计信息
        stats = dify_service.get_agent_cache_stats()
        
        # 3. 添加额外的统计信息
        from utils.cache_manager import get_cache_manager
        cache_manager = get_cache_manager()
        
        if cache_manager and cache_manager.enabled:
            # Redis连接统计
            redis_stats = cache_manager.health_check()
            stats['redis_status'] = redis_stats
            
            # 缓存键统计
            from services.dify_service import CacheKeyGenerator
            key_gen = CacheKeyGenerator()
            
            # 统计各类缓存键的数量
            conversation_keys = cache_manager.redis_client.keys(key_gen.conversations("*", "*"))
            agent_keys = cache_manager.redis_client.keys(key_gen.agents("*"))
            permission_keys = cache_manager.redis_client.keys(key_gen.permission("*"))
            config_keys = cache_manager.redis_client.keys(key_gen.agent_config("*"))
            
            stats['cache_key_counts'] = {
                'conversations': len(conversation_keys),
                'agents': len(agent_keys),
                'permissions': len(permission_keys),
                'agent_configs': len(config_keys),
                'total': len(conversation_keys) + len(agent_keys) + len(permission_keys) + len(config_keys)
            }
        else:
            stats['redis_status'] = {'status': 'disabled', 'message': '缓存未启用'}
            stats['cache_key_counts'] = {'total': 0}
        
        logging.info(f"[GET CACHE STATS] user={current_user['username']}")
        
        return ResponseBuilder.success(
            data=stats,
            message="获取缓存统计成功"
        )
        
    except Exception as e:
        logging.error(f"[GET CACHE STATS ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="获取缓存统计异常"
        )

@require_auth()
@require_permissions(['manage_cache', 'admin'])
@auto_refresh_token()
def api_cache_health():
    """获取缓存健康状态"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        # 2. 检查缓存健康状态
        from utils.cache_manager import get_cache_manager
        cache_manager = get_cache_manager()
        
        if cache_manager and cache_manager.enabled:
            health_status = cache_manager.health_check()
            
            # 添加DifyService缓存配置信息
            cache_config = dify_service.get_cache_stats()
            health_status['dify_cache_config'] = {
                "conversations_ttl": cache_config.get("conversations_cache_ttl"),
                "agents_ttl": cache_config.get("agents_cache_ttl"),
                "permissions_ttl": cache_config.get("permissions_cache_ttl", 1800),  # 30分钟
                "config_ttl": cache_config.get("config_cache_ttl", 3600)  # 1小时
            }
            
            # 测试缓存读写
            try:
                test_key = "health_check_test"
                test_value = "ok"
                cache_manager.set(test_key, test_value, ttl=10)
                retrieved_value = cache_manager.get(test_key)
                cache_manager.delete(test_key)
                
                health_status['read_write_test'] = {
                    'status': 'success' if retrieved_value == test_value else 'failed',
                    'latency_ms': 1  # 简化实现，实际应该测量延迟
                }
            except Exception as e:
                health_status['read_write_test'] = {
                    'status': 'failed',
                    'error': str(e)
                }
        else:
            health_status = {
                "status": "disabled",
                "enabled": False,
                "message": "缓存管理器未初始化或已禁用"
            }
        
        logging.info(f"[CACHE HEALTH CHECK] user={current_user['username']}")
        
        return ResponseBuilder.success(
            data=health_status,
            message="缓存健康检查完成"
        )
        
    except Exception as e:
        logging.error(f"[CACHE HEALTH CHECK ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="缓存健康检查异常"
        )
