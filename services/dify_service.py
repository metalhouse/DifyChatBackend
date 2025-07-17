"""
Dify API服务模块
提供与Dify平台的API交互功能
"""
import requests
import os
import logging
from functools import wraps
import json
from typing import Optional, List, Dict, Any

class DifyService:
    """Dify API服务类"""
    
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or os.environ.get('DIFY_BASE_URL', 'http://192.168.1.68/v1')
        self.default_api_key = api_key or os.environ.get('DIFY_API_KEY')
        self.agents_file = os.path.join(os.path.dirname(__file__), '..', 'agents.json')
        
    def get_user_agents(self, username: str) -> List[Dict[str, str]]:
        """获取用户可用的智能体列表"""
        try:
            with open(self.agents_file, 'r', encoding='utf-8') as f:
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

    def get_agent_api_key(self, agent_id: str) -> Optional[str]:
        """获取智能体的API密钥"""
        try:
            with open(self.agents_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('agents', {}).get(agent_id, {}).get('dify_api_key')
        except Exception as e:
            logging.error(f"[AGENT] get_agent_api_key error: {e}")
            return None

    def make_request(self, method: str, path: str, params: Dict = None, 
                    json_data: Dict = None, stream: bool = False, 
                    agent_id: str = None) -> tuple:
        """向Dify API发送请求"""
        url = f"{self.base_url}{path}"
        api_key = self.get_agent_api_key(agent_id) if agent_id else self.default_api_key
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            resp = requests.request(
                method, url, headers=headers, params=params, 
                json=json_data, stream=stream, timeout=60
            )
            
            if stream:
                return resp, 200
                
            try:
                data = resp.json()
            except Exception:
                data = {'success': False, 'message': resp.text}
                
            if resp.status_code == 200:
                return {'success': True, 'data': data}, 200
            else:
                return {
                    'success': False, 
                    'message': data.get('message', '请求失败'), 
                    'data': data
                }, resp.status_code
                
        except Exception as e:
            logging.error(f"[DIFY] {method} {url} error: {e}")
            return {'success': False, 'message': str(e)}, 500

# 全局Dify服务实例
dify_service = DifyService()
