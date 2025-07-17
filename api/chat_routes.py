"""
API路由模块 - 智能体相关接口
"""
from flask import request, jsonify, g
from functools import wraps
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入认证装饰器
from auth.decorators import require_auth, require_permissions, check_agent_access, auto_refresh_token

from services.dify_service import dify_service

def api_response(func):
    """API响应装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"[API] {func.__name__} error: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    return wrapper

@require_auth()
@require_permissions(['access_agents'])
@auto_refresh_token()
@api_response
def api_agents():
    """获取用户可用智能体列表"""
    # 从认证信息中获取用户名
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'success': False, 'message': '用户认证信息缺失'}), 401
    
    username = user['username']
    agents = dify_service.get_user_agents(username)
    return jsonify({'success': True, 'data': agents})

@require_auth()
@require_permissions(['view_conversations'])
@check_agent_access('agent_id')
@auto_refresh_token()
@api_response
def api_conversations():
    """获取会话列表（支持缓存）"""
    # 从认证信息中获取用户名
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'success': False, 'message': '用户认证信息缺失'}), 401
    
    username = user['username']
    agent_id = request.args.get('agent_id')
    
    # 检查是否禁用缓存
    use_cache = request.args.get('no_cache', '').lower() not in ('true', '1', 'yes')
    
    params = {
        'user': username,
        'last_id': request.args.get('last_id'),
        'limit': request.args.get('limit'),
        'sort_by': request.args.get('sort_by'),
    }
    params = {k: v for k, v in params.items() if v is not None}
    
    # 使用带缓存的方法
    resp, status = dify_service.get_conversations(
        username=username, 
        agent_id=agent_id, 
        params=params, 
        use_cache=use_cache
    )
    
    return jsonify(resp), status

@require_auth()
@require_permissions(['send_messages'])
@check_agent_access('agent_id')
@auto_refresh_token()
@api_response
def api_chat():
    """发送对话消息（发送后清除缓存）"""
    from flask import Response
    
    # 从认证信息中获取用户名
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'success': False, 'message': '用户认证信息缺失'}), 401
    
    username = user['username']
    data = request.get_json(force=True)
    agent_id = data.get('agent_id')
    
    if not data.get('query'):
        return jsonify({'success': False, 'message': '缺少 query 参数'}), 400
    
    payload = {
        'query': data.get('query'),
        'inputs': data.get('inputs', {}),
        'response_mode': data.get('response_mode', 'blocking'),
        'user': username,
        'conversation_id': data.get('conversation_id'),
        'files': data.get('files'),
        'auto_generate_name': data.get('auto_generate_name', True)
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    
    # 发送消息
    if payload.get('response_mode') == 'streaming':
        def stream():
            resp, _ = dify_service.make_request(
                'POST', '/chat-messages', json_data=payload, 
                stream=True, agent_id=agent_id
            )
            
            # 在流式响应结束后清除缓存
            try:
                for line in resp.iter_lines():
                    if line:
                        yield line + b'\n'
            finally:
                # 清除用户对话缓存
                dify_service.invalidate_user_cache(username, agent_id)
                
        return Response(stream(), content_type='text/event-stream')
    else:
        resp, status = dify_service.make_request(
            'POST', '/chat-messages', json_data=payload, agent_id=agent_id
        )
        
        # 如果消息发送成功，清除相关缓存
        if status == 200:
            dify_service.invalidate_user_cache(username, agent_id)
        
        return jsonify(resp), status


# ========== 智能体缓存管理API ==========

@require_auth()
@require_permissions(['view_permissions'])
@auto_refresh_token()
@api_response
def api_user_permissions():
    """获取用户权限信息（支持缓存）"""
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'success': False, 'message': '用户认证信息缺失'}), 401
    
    username = user['username']
    use_cache = request.args.get('use_cache', 'true').lower() == 'true'
    
    permissions = dify_service.get_user_permissions(username, use_cache=use_cache)
    return jsonify({'success': True, 'data': permissions})


@require_auth()
@require_permissions(['view_agent_config'])
@check_agent_access('agent_id')
@auto_refresh_token()
@api_response
def api_agent_config():
    """获取智能体配置（支持缓存）"""
    agent_id = request.args.get('agent_id')
    if not agent_id:
        return jsonify({'success': False, 'message': '智能体ID是必需的'}), 400
    
    use_cache = request.args.get('use_cache', 'true').lower() == 'true'
    
    config = dify_service.get_agent_config(agent_id, use_cache=use_cache)
    return jsonify({'success': True, 'data': config})


@require_auth()
@require_permissions(['manage_cache', 'admin'])
@auto_refresh_token()
@api_response
def api_preload_cache():
    """预热智能体缓存"""
    usernames = request.json.get('usernames') if request.is_json else None
    
    result = dify_service.preload_agent_cache(usernames)
    return jsonify({'success': True, 'data': result})


@require_auth()
@require_permissions(['manage_cache', 'admin'])
@auto_refresh_token()
@api_response
def api_refresh_agent_cache():
    """刷新智能体配置缓存"""
    result = dify_service.refresh_agent_config_cache()
    return jsonify({'success': True, 'data': result})


@require_auth()
@require_permissions(['manage_cache', 'admin'])
@auto_refresh_token()
@api_response
def api_invalidate_agent_cache():
    """清除智能体缓存"""
    data = request.get_json() or {}
    username = data.get('username')
    agent_id = data.get('agent_id')
    
    dify_service.invalidate_agent_cache(username=username, agent_id=agent_id)
    
    return jsonify({
        'success': True, 
        'message': f'已清除缓存 - 用户: {username or "所有"}, 智能体: {agent_id or "所有"}'
    })


@require_auth()
@require_permissions(['view_stats'])
@auto_refresh_token()
@api_response
def api_agent_cache_stats():
    """获取智能体缓存统计"""
    stats = dify_service.get_agent_cache_stats()
    return jsonify({'success': True, 'data': stats})
