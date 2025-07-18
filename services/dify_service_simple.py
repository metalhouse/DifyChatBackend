"""
Dify API服务模块 - 测试版
"""
import requests
import logging
import json
import time
from typing import Optional, List, Dict, Any, Tuple
from config import get_dify_config, get_database_config

logger = logging.getLogger(__name__)

class DifyService:
    """Dify API服务类"""
    
    def __init__(self, base_url: str = None, api_key: str = None):
        # 基础配置
        try:
            dify_config = get_dify_config()
            db_config = get_database_config()
            
            self.base_url = base_url or dify_config.base_url
            self.default_api_key = api_key or dify_config.default_api_key
            self.timeout = dify_config.timeout
            self.max_retries = dify_config.max_retries
            self.agents_file = db_config.agents_file
            
            logging.info(f"[DIFY SERVICE] 初始化完成 - URL: {self.base_url}")
            
        except Exception as e:
            logging.error(f"[DIFY SERVICE] 初始化失败: {e}")
            raise
    
    def make_request(self, method: str, path: str, params: Dict = None, 
                    json_data: Dict = None, stream: bool = False, 
                    agent_id: str = None, files: Dict = None, data: Dict = None) -> Tuple[Dict, int]:
        """HTTP请求"""
        url = f"{self.base_url}{path}"
        api_key = self._get_api_key(agent_id)
        
        headers = {
            'Authorization': f'Bearer {api_key}',
        }
        
        if not files:
            headers['Content-Type'] = 'application/json'
        
        try:
            response = requests.request(
                method, url,
                headers=headers,
                params=params,
                json=json_data,
                stream=stream,
                timeout=self.timeout,
                files=files,
                data=data
            )
            
            if stream:
                return response, 200
            
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            return response_data, response.status_code
            
        except Exception as e:
            logging.error(f"[DIFY] API请求失败: {e}")
            return {'error': str(e)}, 500
    
    def _get_api_key(self, agent_id: str = None) -> str:
        """获取API密钥"""
        if agent_id:
            api_key = self.get_agent_api_key(agent_id)
            if api_key:
                return api_key
        
        return self.default_api_key or "dummy-key"
    
    def get_agent_api_key(self, agent_id: str) -> Optional[str]:
        """获取智能体的API密钥"""
        try:
            with open(self.agents_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            encoded_key = data.get('agents', {}).get(agent_id, {}).get('dify_api_key')
            if encoded_key:
                import base64
                try:
                    return base64.urlsafe_b64decode(encoded_key.encode('utf-8')).decode('utf-8')
                except:
                    return encoded_key
            return None
            
        except Exception as e:
            logging.error(f"[AGENT] get_agent_api_key error: {e}")
            return None

# 全局服务实例
dify_service = None

def get_dify_service():
    """获取服务实例"""
    global dify_service
    if dify_service is None:
        dify_service = DifyService()
    return dify_service
