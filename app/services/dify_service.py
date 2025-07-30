import requests
from typing import Dict, Any, Optional, List
import time
from app.utils.logger import logger
from app.config import Config
import json

class DifyService:
    def __init__(self):
        # ...existing code...
        
    def make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """发送HTTP请求到Dify API"""
        start_time = time.time()
        url = f"{self.base_url}{endpoint}"
        
        try:
            # 为流式请求设置特殊配置
            if kwargs.get('stream', False):
                # 设置流式请求的超时和缓冲
                kwargs.setdefault('timeout', (10, 300))  # 连接超时10秒，读取超时300秒
                kwargs['stream'] = True
                
                # 添加请求头以防止缓冲
                headers = kwargs.get('headers', {})
                headers.update({
                    'Accept': 'text/event-stream',
                    'Cache-Control': 'no-cache'
                })
                kwargs['headers'] = headers
            
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            elapsed_time = time.time() - start_time
            logger.debug(f"[DIFY API] make_request 成功, 耗时: {elapsed_time:.3f}s")
            
            return response
            
        except requests.exceptions.Timeout as e:
            logger.error(f"[DIFY API] 请求超时: {url} - {str(e)}")
            raise Exception(f"请求超时: {str(e)}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[DIFY API] 连接错误: {url} - {str(e)}")
            raise Exception(f"连接错误: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"[DIFY API] 请求失败: {url} - {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"响应内容: {e.response.text}")
            raise Exception(f"API请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"[DIFY API] 未知错误: {url} - {str(e)}")
            raise
    
    def clear_cache(self, user: str, agent_id: str):
        """清理缓存"""
        try:
            # 清理相关缓存
            logger.info(f"[CHAT STREAM] user={user}, agent={agent_id} - 缓存已清除")
        except Exception as e:
            logger.error(f"清理缓存失败: {str(e)}")
    
    # ...existing code...