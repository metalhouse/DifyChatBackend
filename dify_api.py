import requests
from flask import request, jsonify, Response
import os
import logging
from functools import wraps
import json

DIFY_BASE_URL = os.environ.get('DIFY_BASE_URL', 'http://192.168.1.68/v1')
DIFY_API_KEY = os.environ.get('DIFY_API_KEY')

AGENTS_FILE = os.path.join(os.path.dirname(__file__), 'agents.json')


def get_user_agents(username):
    try:
        with open(AGENTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        agent_ids = data.get('user_agents', {}).get(username, [])
        agents = data.get('agents', {})
        return [
            {"agent_id": aid, "name": agents[aid]["name"]}
            for aid in agent_ids if aid in agents
        ]
    except Exception as e:
        logging.error(f"[AGENT] get_user_agents error: {e}")
        return []


def get_agent_api_key(agent_id):
    try:
        with open(AGENTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('agents', {}).get(agent_id, {}).get('dify_api_key')
    except Exception as e:
        logging.error(f"[AGENT] get_agent_api_key error: {e}")
        return None


def dify_request(method, path, params=None, json_data=None, stream=False, agent_id=None):
    url = f"{DIFY_BASE_URL}{path}"
    api_key = get_agent_api_key(agent_id) if agent_id else DIFY_API_KEY
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    try:
        resp = requests.request(method, url, headers=headers, params=params, json=json_data, stream=stream, timeout=60)
        if stream:
            return resp
        try:
            data = resp.json()
        except Exception:
            data = {'success': False, 'message': resp.text}
        if resp.status_code == 200:
            return {'success': True, 'data': data}, 200
        else:
            return {'success': False, 'message': data.get('message', '请求失败'), 'data': data}, resp.status_code
    except Exception as e:
        logging.error(f"[DIFY] {method} {url} error: {e}")
        return {'success': False, 'message': str(e)}, 500


def api_response(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"[API] {func.__name__} error: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    return wrapper


@api_response
# 获取用户可用智能体列表
# GET /api/agents?user=xxx
def api_agents():
    username = request.args.get('user')
    if not username:
        return jsonify({'success': False, 'message': '缺少 user 参数'}), 400
    return jsonify({'success': True, 'data': get_user_agents(username)})


@api_response
# 获取会话列表
# GET /api/conversations?user=xxx&agent_id=xxx
# agent_id 必须在用户有权的列表中
def api_conversations():
    username = request.args.get('user')
    agent_id = request.args.get('agent_id')
    if not username:
        return jsonify({'success': False, 'message': '缺少 user 参数'}), 400
    if agent_id and agent_id not in [a['agent_id'] for a in get_user_agents(username)]:
        return jsonify({'success': False, 'message': '无权访问该智能体'}), 403
    params = {
        'user': username,
        'last_id': request.args.get('last_id'),
        'limit': request.args.get('limit'),
        'sort_by': request.args.get('sort_by'),
    }
    params = {k: v for k, v in params.items() if v is not None}
    resp, status = dify_request('GET', '/conversations', params=params, agent_id=agent_id)
    return jsonify(resp), status


@api_response
# 发送对话消息
# POST /api/chat，body: {user, query, agent_id, ...}
def api_chat():
    data = request.get_json(force=True)
    username = data.get('user')
    agent_id = data.get('agent_id')
    if not username:
        return jsonify({'success': False, 'message': '缺少 user 参数'}), 400
    if not data.get('query'):
        return jsonify({'success': False, 'message': '缺少 query 参数'}), 400
    if agent_id and agent_id not in [a['agent_id'] for a in get_user_agents(username)]:
        return jsonify({'success': False, 'message': '无权访问该智能体'}), 403
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
            resp = dify_request('POST', '/chat-messages', json_data=payload, stream=True, agent_id=agent_id)
            for line in resp.iter_lines():
                if line:
                    yield line + b'\n'
        return Response(stream(), content_type='text/event-stream')
    else:
        resp, status = dify_request('POST', '/chat-messages', json_data=payload, agent_id=agent_id)
        return jsonify(resp), status
