"""
Dify API服务模块
提供与Dify平台的API交互功能
"""
import requests
import logging
from functools import wraps
import json
from typing import Optional, List, Dict, Any
from config import get_dify_config, get_database_config

class DifyService:
    """Dify API服务类"""
    
    def __init__(self, base_url: str = None, api_key: str = None):
        dify_config = get_dify_config()
        db_config = get_database_config()
        
        self.base_url = base_url or dify_config.base_url
        self.default_api_key = api_key or dify_config.default_api_key
        self.timeout = dify_config.timeout
        self.max_retries = dify_config.max_retries
        self.agents_file = db_config.agents_file
        
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
        
        if not api_key:
            logging.error(f"[DIFY] No API key available for agent_id: {agent_id}")
            return False, "API密钥未配置"
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                stream=stream,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return True, response
            else:
                logging.error(f"[DIFY] API request failed: {response.status_code} - {response.text}")
                return False, f"API请求失败: {response.status_code}"
                
        except requests.RequestException as e:
            logging.error(f"[DIFY] Request exception: {e}")
            return False, f"请求异常: {str(e)}"
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
