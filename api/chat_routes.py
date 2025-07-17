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
    """获取会话列表"""
    # 从认证信息中获取用户名
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'success': False, 'message': '用户认证信息缺失'}), 401
    
    username = user['username']
    agent_id = request.args.get('agent_id')
    
    params = {
        'user': username,
        'last_id': request.args.get('last_id'),
        'limit': request.args.get('limit'),
        'sort_by': request.args.get('sort_by'),
    }
    params = {k: v for k, v in params.items() if v is not None}
    
    resp, status = dify_service.make_request('GET', '/conversations', params=params, agent_id=agent_id)
    return jsonify(resp), status

@require_auth()
@require_permissions(['send_messages'])
@check_agent_access('agent_id')
@auto_refresh_token()
@api_response
def api_chat():
    """发送对话消息"""
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
    
    if payload.get('response_mode') == 'streaming':
        def stream():
            resp, _ = dify_service.make_request(
                'POST', '/chat-messages', json_data=payload, 
                stream=True, agent_id=agent_id
            )
            for line in resp.iter_lines():
                if line:
                    yield line + b'\n'
        return Response(stream(), content_type='text/event-stream')
    else:
        resp, status = dify_service.make_request(
            'POST', '/chat-messages', json_data=payload, agent_id=agent_id
        )
        return jsonify(resp), status
