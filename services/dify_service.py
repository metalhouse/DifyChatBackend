"""
Dify API服务模块 - Task 5.1 现代化增强版
提供与Dify平台的API交互功能，支持缓存
新增功能：异步HTTP客户端、错误处理和重试机制、API调用监控和日志
"""
import requests
import logging
from functools import wraps
import json
import time
from typing import Optional, List, Dict, Any, Tuple
from config import get_dify_config, get_database_config
from utils.cache_manager import get_cache_manager, CacheKeyGenerator

# Task 5.1 新增依赖
import aiohttp
import asyncio
import backoff
from dataclasses import dataclass


# Task 5.1 新增：API响应数据类
@dataclass
class APIResponse:
    """标准化API响应数据类"""
    data: Any
    status_code: int
    headers: Dict[str, str]
    success: bool
    error_message: Optional[str] = None
    request_id: Optional[str] = None
    duration: float = 0.0


# Task 5.1 新增：API监控装饰器
def api_monitor(func):
    """API调用监控装饰器"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        method_name = func.__name__
        
        try:
            result = func(self, *args, **kwargs)
            duration = time.time() - start_time
            
            # 记录成功调用
            if hasattr(self, '_record_api_call'):
                self._record_api_call(method_name, True, duration)
            logging.debug(f"[DIFY API] {method_name} 成功, 耗时: {duration:.3f}s")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            # 记录失败调用  
            if hasattr(self, '_record_api_call'):
                self._record_api_call(method_name, False, duration, str(e))
            logging.error(f"[DIFY API] {method_name} 失败, 耗时: {duration:.3f}s, 错误: {e}")
            
            raise
    
    return wrapper


# Task 5.1 新增：自定义异常类
class DifyAPIException(Exception):
    """Dify API异常基类"""
    def __init__(self, message: str, status_code: int = 500, response_data: Dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)


class RetryableError(DifyAPIException):
    """可重试的错误"""
    pass


class NonRetryableError(DifyAPIException):
    """不可重试的错误"""
    pass


class DifyService:
    """
    Dify API服务类 - Task 5.1 现代化增强版
    
    原有功能：缓存管理、智能体管理、API调用
    新增功能：异步HTTP客户端、智能重试机制、API监控统计
    """
    
    def __init__(self, base_url: str = None, api_key: str = None):
        dify_config = get_dify_config()
        db_config = get_database_config()
        
        self.base_url = base_url or dify_config.base_url
        self.default_api_key = api_key or dify_config.default_api_key
        self.timeout = dify_config.timeout
        self.max_retries = dify_config.max_retries
        self.agents_file = db_config.agents_file
        
        # 缓存配置
        self.cache_manager = get_cache_manager()
        self.conversation_cache_ttl = 300  # 5分钟
        self.agent_cache_ttl = 3600  # 1小时
        self.permission_cache_ttl = 1800  # 30分钟
        
        # Task 5.1 新增：异步HTTP客户端
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Task 5.1 新增：API监控统计
        self.api_stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'average_response_time': 0.0,
            'error_distribution': {},
            'call_history': []  # 最近100次调用
        }
        
        logging.info("[DIFY SERVICE] Task 5.1 现代化初始化完成 - 支持异步HTTP、智能重试、API监控")
    
    # Task 5.1 新增：API统计记录
    def _record_api_call(self, method: str, success: bool, duration: float, error: str = None):
        """记录API调用统计"""
        self.api_stats['total_calls'] += 1
        
        if success:
            self.api_stats['successful_calls'] += 1
        else:
            self.api_stats['failed_calls'] += 1
            
            # 记录错误分布
            error_type = type(error).__name__ if error else 'Unknown'
            self.api_stats['error_distribution'][error_type] = \
                self.api_stats['error_distribution'].get(error_type, 0) + 1
        
        # 更新平均响应时间
        total_calls = self.api_stats['total_calls']
        avg_time = self.api_stats['average_response_time']
        self.api_stats['average_response_time'] = \
            (avg_time * (total_calls - 1) + duration) / total_calls
        
        # 记录调用历史（保留最近100次）
        call_record = {
            'method': method,
            'success': success,
            'duration': duration,
            'timestamp': time.time(),
            'error': error
        }
        
        self.api_stats['call_history'].append(call_record)
        if len(self.api_stats['call_history']) > 100:
            self.api_stats['call_history'].pop(0)
    
    # Task 5.1 新增：异步HTTP会话管理
    async def _ensure_session(self):
        """确保异步会话存在"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,  # 最大连接数
                ttl_dns_cache=300,  # DNS缓存时间
                use_dns_cache=True,
            )
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={'User-Agent': 'DifyChatBackend/2.0'}
            )
            
            logging.debug("[DIFY SERVICE] 异步HTTP会话已创建")
    
    async def _close_session(self):
        """关闭异步会话"""
        if self._session and not self._session.closed:
            await self._session.close()
            logging.debug("[DIFY SERVICE] 异步HTTP会话已关闭")
    
    # Task 5.1 新增：智能重试判断
    def _should_retry(self, status_code: int, error: Exception = None) -> bool:
        """判断是否应该重试"""
        # 5xx错误可以重试
        if 500 <= status_code < 600:
            return True
        
        # 429 限流错误可以重试
        if status_code == 429:
            return True
        
        # 连接错误可以重试
        if isinstance(error, (requests.ConnectionError, requests.Timeout)):
            return True
        
        return False
    
    # Task 5.1 新增：支持重试的同步HTTP请求
    @backoff.on_exception(
        backoff.expo,
        (requests.ConnectionError, requests.Timeout, RetryableError),
        max_tries=3,
        max_time=30
    )
    def _make_request_with_retry(self, method: str, url: str, **kwargs):
        """支持重试的HTTP请求"""
        stream = kwargs.get('stream', False)
        
        try:
            response = requests.request(method, url, timeout=self.timeout, **kwargs)
            
            # 对于流式请求，不进行重试机制，直接返回
            if stream:
                if response.status_code != 200:
                    # 流式请求失败，记录错误并抛出异常
                    error_text = response.text if hasattr(response, 'text') else str(response)
                    logging.error(f"[DIFY STREAM ERROR] {method} {url}: {response.status_code} - {error_text}")
                    raise NonRetryableError(f"流式请求失败: HTTP {response.status_code}", response.status_code)
                return response
            
            # 非流式请求检查是否需要重试
            if self._should_retry(response.status_code):
                raise RetryableError(f"HTTP {response.status_code}", response.status_code)
            
            return response
            
        except (requests.ConnectionError, requests.Timeout) as e:
            # 对于流式请求，网络错误不重试
            if stream:
                logging.error(f"[DIFY STREAM NETWORK ERROR] {method} {url}: {e}")
                raise NonRetryableError(f"流式请求网络错误: {e}", 500)
            # 非流式请求，网络错误触发重试
            raise RetryableError(f"网络错误: {e}", 500)
    
    # Task 5.1 新增：异步HTTP请求方法
    @api_monitor
    async def make_async_request(self, method: str, path: str, params: Dict = None,
                                json_data: Dict = None, agent_id: str = None) -> APIResponse:
        """
        异步HTTP请求接口
        """
        await self._ensure_session()
        
        url = f"{self.base_url}{path}"
        api_key = self._get_api_key(agent_id)
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        start_time = time.time()
        
        try:
            async with self._session.request(
                method, url,
                params=params,
                json=json_data,
                headers=headers
            ) as response:
                
                duration = time.time() - start_time
                
                # 获取响应数据
                try:
                    response_data = await response.json()
                except Exception:
                    response_data = await response.text()
                
                # 返回标准化API响应
                return APIResponse(
                    data=response_data,
                    status_code=response.status,
                    headers=dict(response.headers),
                    success=response.status == 200,
                    error_message=None if response.status == 200 else str(response_data),
                    request_id=response.headers.get('X-Request-ID'),
                    duration=duration
                )
                
        except aiohttp.ClientError as e:
            duration = time.time() - start_time
            logging.error(f"[DIFY] 异步API请求失败: {e}")
            return APIResponse(
                data={'success': False, 'message': str(e)},
                status_code=500,
                headers={},
                success=False,
                error_message=str(e),
                duration=duration
            )
    
    # Task 5.1 新增：异步上下文管理器支持
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self._close_session()
    
    def _get_api_key(self, agent_id: str = None) -> str:
        """获取API密钥（增强错误处理）"""
        if agent_id:
            api_key = self.get_agent_api_key(agent_id)
            if not api_key:
                raise NonRetryableError(f"智能体 {agent_id} 的API密钥未配置", 401)
            return api_key
        
        # 使用默认密钥或第一个可用密钥
        api_key = self.default_api_key
        if not api_key:
            api_key = self._get_fallback_api_key()
        
        if not api_key:
            raise NonRetryableError("API密钥未配置", 401)
        
        return api_key
    
    def _get_fallback_api_key(self) -> Optional[str]:
        """获取备用API密钥"""
        try:
            with open(self.agents_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            agents = data.get('agents', {})
            if agents:
                first_agent_id = list(agents.keys())[0]
                api_key = self.get_agent_api_key(first_agent_id)
                if api_key:
                    logging.info(f"[DIFY] 使用备用API密钥: {first_agent_id}")
                return api_key
        except Exception as e:
            logging.error(f"[DIFY] 获取备用API密钥失败: {e}")
        
        return None
    
    def _is_cache_enabled(self) -> bool:
        """检查缓存是否可用"""
        return self.cache_manager and self.cache_manager.enabled
    
    def _get_cached_conversations(self, username: str, agent_id: str, params: Dict) -> Optional[Dict]:
        """获取缓存的对话列表"""
        if not self._is_cache_enabled():
            return None
        
        # 生成缓存key，包含参数信息确保准确性
        cache_key = CacheKeyGenerator.custom(
            "conversations", 
            username, 
            agent_id or "default",
            str(hash(str(sorted(params.items()))))
        )
        
        return self.cache_manager.get(cache_key)
    
    def _cache_conversations(self, username: str, agent_id: str, params: Dict, data: Dict) -> None:
        """缓存对话列表"""
        if not self._is_cache_enabled():
            return
        
        # 生成缓存key
        cache_key = CacheKeyGenerator.custom(
            "conversations", 
            username, 
            agent_id or "default",
            str(hash(str(sorted(params.items()))))
        )
        
        # 添加缓存时间戳
        cache_data = {
            "data": data,
            "cached_at": time.time(),
            "params": params
        }
        
        self.cache_manager.set(cache_key, cache_data, ttl=self.conversation_cache_ttl)
        logging.debug(f"[CACHE] 对话列表已缓存: {cache_key}")
    
    def _invalidate_conversations_cache(self, username: str, agent_id: str = None) -> None:
        """清除对话列表缓存"""
        if not self._is_cache_enabled():
            return
        
        # 清除用户的所有对话缓存
        if agent_id:
            pattern = f"conversations:{username}:{agent_id}:*"
        else:
            pattern = f"conversations:{username}:*"
        
        deleted = self.cache_manager.delete_pattern(pattern)
        if deleted > 0:
            logging.info(f"[CACHE] 清除对话缓存: {deleted} 条记录")
    
    def _get_cached_agents(self, username: str) -> Optional[List]:
        """获取缓存的智能体列表"""
        if not self._is_cache_enabled():
            return None
        
        cache_key = CacheKeyGenerator.agent_list(username)
        cached_data = self.cache_manager.get(cache_key)
        
        if cached_data:
            logging.debug(f"[CACHE] 智能体列表命中缓存: {username}")
            return cached_data.get("agents")
        
        return None
    
    def _cache_agents(self, username: str, agents: List) -> None:
        """缓存智能体列表"""
        if not self._is_cache_enabled():
            return
        
        cache_key = CacheKeyGenerator.agent_list(username)
        cache_data = {
            "agents": agents,
            "cached_at": time.time()
        }
        
        self.cache_manager.set(cache_key, cache_data, ttl=self.agent_cache_ttl)
        logging.debug(f"[CACHE] 智能体列表已缓存: {username}")
    
    @api_monitor
    def get_user_agents(self, username: str, use_cache: bool = True) -> List[Dict[str, str]]:
        """获取用户可用的智能体列表"""
        # 尝试从缓存获取
        if use_cache:
            cached_agents = self._get_cached_agents(username)
            if cached_agents is not None:
                return cached_agents
        
        try:
            with open(self.agents_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            agent_ids = data.get('user_agents', {}).get(username, [])
            agents = data.get('agents', {})
            
            result = [
                {
                    "id": aid, 
                    "name": agents[aid]["name"],
                    "welcome_message": agents[aid].get("welcome_message", "")
                }
                for aid in agent_ids if aid in agents
            ]
            
            # 缓存结果
            if use_cache:
                self._cache_agents(username, result)
            
            return result
            
        except Exception as e:
            logging.error(f"[AGENT] get_user_agents error: {e}")
            return []
    
    @api_monitor
    def get_conversations(self, username: str, agent_id: str = None, 
                         params: Dict = None, use_cache: bool = True) -> Tuple[Dict, int]:
        """获取对话列表，支持缓存"""
        params = params or {}
        
        # 确保params包含必需的user参数
        params['user'] = username
        
        # 尝试从缓存获取
        if use_cache:
            cached_data = self._get_cached_conversations(username, agent_id, params)
            if cached_data:
                logging.debug(f"[CACHE] 对话列表命中缓存: {username}")
                return cached_data["data"], 200
        
        # 从API获取
        resp, status = self.make_request('GET', '/conversations', params=params, agent_id=agent_id)
        
        # 如果成功，缓存结果
        if status == 200 and use_cache:
            self._cache_conversations(username, agent_id, params, resp)
        
        return resp, status
    
    def invalidate_user_cache(self, username: str, agent_id: str = None) -> None:
        """清除用户相关缓存（在发送新消息后调用）"""
        if not self._is_cache_enabled():
            return
        
        # 清除对话列表缓存
        self._invalidate_conversations_cache(username, agent_id)
        
        # 可以选择性清除智能体缓存（如果智能体信息可能变化）
        # self._invalidate_agents_cache(username)
        
        logging.info(f"[CACHE] 用户缓存已清除: {username}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        if not self._is_cache_enabled():
            return {"enabled": False, "message": "缓存未启用"}
        
        stats = self.cache_manager.stats
        return {
            "enabled": True,
            "conversations_cache_ttl": self.conversation_cache_ttl,
            "agents_cache_ttl": self.agent_cache_ttl,
            "stats": {
                "hits": stats.hits,
                "misses": stats.misses,
                "hit_rate": round(stats.hit_rate * 100, 2),
                "total_operations": stats.total_operations
            }
        }

    # ========== 新增方法：单个资源详情 ==========
    
    @api_monitor
    def get_agent_detail(self, agent_id: str, username: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """获取单个智能体详情"""
        try:
            # 首先检查用户是否有访问该智能体的权限
            user_agents = self.get_user_agents(username, use_cache)
            agent_found = None
            
            for agent in user_agents:
                if agent.get('id') == agent_id:
                    agent_found = agent
                    break
            
            if not agent_found:
                return None
            
            # 获取智能体的详细配置（如果需要）
            cache_key = CacheKeyGenerator.agent_detail(agent_id)
            
            if use_cache and self._is_cache_enabled():
                cached_detail = self.cache_manager.get(cache_key)
                if cached_detail:
                    logging.debug(f"[CACHE HIT] 智能体详情: {agent_id}")
                    return cached_detail
            
            # 扩展基础智能体信息
            agent_detail = {
                **agent_found,
                'detailed_info': True,
                'last_accessed': time.time(),
                'permissions': {
                    'can_chat': True,
                    'can_view_history': True,
                    'can_configure': False  # 根据用户权限设置
                }
            }
            
            # 缓存结果
            if use_cache and self._is_cache_enabled():
                self.cache_manager.setex(cache_key, self.agent_cache_ttl, agent_detail)
                logging.debug(f"[CACHE SET] 智能体详情: {agent_id}")
            
            return agent_detail
            
        except Exception as e:
            logging.error(f"[DIFY SERVICE] 获取智能体详情失败: {agent_id}, 错误: {e}")
            return None
    
    @api_monitor
    def get_conversation_detail(self, conversation_id: str, username: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """获取单个对话详情"""
        try:
            cache_key = CacheKeyGenerator.conversation_detail(conversation_id)
            
            if use_cache and self._is_cache_enabled():
                cached_detail = self.cache_manager.get(cache_key)
                if cached_detail:
                    logging.debug(f"[CACHE HIT] 对话详情: {conversation_id}")
                    return cached_detail
            
            # 从API获取对话详情
            resp, status = self.make_request('GET', f'/conversations/{conversation_id}')
            
            if status != 200 or not resp:
                return None
            
            # 检查对话是否属于当前用户（安全检查）
            if resp.get('created_by') != username:
                logging.warning(f"[SECURITY] 用户 {username} 尝试访问不属于自己的对话: {conversation_id}")
                return None
            
            # 扩展对话信息
            conversation_detail = {
                **resp,
                'detailed_info': True,
                'last_accessed': time.time(),
                'permissions': {
                    'can_delete': True,
                    'can_rename': True,
                    'can_export': True
                }
            }
            
            # 缓存结果
            if use_cache and self._is_cache_enabled():
                self.cache_manager.setex(cache_key, self.conversation_cache_ttl, conversation_detail)
                logging.debug(f"[CACHE SET] 对话详情: {conversation_id}")
            
            return conversation_detail
            
        except Exception as e:
            logging.error(f"[DIFY SERVICE] 获取对话详情失败: {conversation_id}, 错误: {e}")
            return None
    
    def get_user_conversation_count(self, username: str) -> int:
        """获取用户对话总数"""
        try:
            # 获取用户的所有对话（不分页）
            params = {'limit': 1}  # 只获取第一条来获取总数
            resp, status = self.make_request('GET', '/conversations', params=params)
            
            if status == 200 and resp:
                return resp.get('total', 0)
            
            return 0
            
        except Exception as e:
            logging.error(f"[DIFY SERVICE] 获取对话总数失败: {username}, 错误: {e}")
            return 0
    
    def get_user_message_count(self, username: str) -> int:
        """获取用户消息总数（简化实现）"""
        try:
            # 这里可以实现更复杂的统计逻辑
            # 简化版本：基于对话数量估算
            conversation_count = self.get_user_conversation_count(username)
            # 假设每个对话平均10条消息
            return conversation_count * 10
            
        except Exception as e:
            logging.error(f"[DIFY SERVICE] 获取消息总数失败: {username}, 错误: {e}")
            return 0

    def get_agent_api_key(self, agent_id: str) -> Optional[str]:
        """获取智能体的API密钥"""
        try:
            with open(self.agents_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            encoded_key = data.get('agents', {}).get(agent_id, {}).get('dify_api_key')
            if encoded_key:
                # 解码Base64编码的API Key
                import base64
                try:
                    return base64.urlsafe_b64decode(encoded_key.encode('utf-8')).decode('utf-8')
                except Exception:
                    # 如果解码失败，返回原始值
                    return encoded_key
            return None
        except Exception as e:
            logging.error(f"[AGENT] get_agent_api_key error: {e}")
            return None

    # Task 5.1 增强：智能重试机制的同步请求方法
    @api_monitor
    def make_request(self, method: str, path: str, params: Dict = None, 
                    json_data: Dict = None, stream: bool = False, 
                    agent_id: str = None, files: Dict = None, data: Dict = None) -> Tuple[Dict, int]:
        """
        向Dify API发送请求 - Task 5.1 增强版
        新增功能：智能重试、详细错误处理、API监控
        """
        url = f"{self.base_url}{path}"
        
        try:
            # 获取API密钥（使用新的增强方法）
            api_key = self._get_api_key(agent_id)
            
            headers = {
                'Authorization': f'Bearer {api_key}',
            }
            
            # 文件上传时不设置Content-Type
            if not files:
                headers['Content-Type'] = 'application/json'
            
            # 使用带重试的请求方法
            resp = self._make_request_with_retry(
                method.upper(), url, 
                headers=headers, 
                params=params, 
                json=json_data, 
                stream=stream,
                files=files,
                data=data
            )
            
            if stream:
                # 检查流式响应的状态码
                if resp.status_code != 200:
                    # 流式请求失败，抛出异常让上层处理
                    error_text = resp.text if hasattr(resp, 'text') else str(resp)
                    raise Exception(f"流式请求失败: HTTP {resp.status_code} - {error_text}")
                return resp, 200
                
            # 解析响应数据
            try:
                response_data = resp.json()
            except Exception:
                response_data = {'success': False, 'message': resp.text}
                
            if resp.status_code == 200:
                return response_data, 200
            else:
                logging.error(f"[DIFY] API请求失败: {resp.status_code} - {resp.text}")
                return {
                    'success': False, 
                    'message': response_data.get('message', '请求失败'), 
                    'data': response_data
                }, resp.status_code
                
        except NonRetryableError as e:
            # 不可重试的错误，直接返回
            logging.error(f"[DIFY] 不可重试错误: {e.message}")
            return {
                'success': False, 
                'message': e.message,
                'data': e.response_data
            }, e.status_code
            
        except RetryableError as e:
            # 重试耗尽后的错误
            logging.error(f"[DIFY] 重试耗尽: {e.message}")
            return {
                'success': False, 
                'message': f'请求失败（已重试）: {e.message}',
                'data': e.response_data
            }, e.status_code
                
        except Exception as e:
            logging.error(f"[DIFY] {method} {url} 未预期错误: {e}")
            return {'success': False, 'message': str(e)}, 500
                
        except Exception as e:
            logging.error(f"[DIFY] {method} {url} error: {e}")
            return {'success': False, 'message': str(e)}, 500

    # ========== 智能体缓存增强功能 ==========
    
    def _get_cached_permissions(self, username: str) -> Optional[Dict]:
        """获取缓存的用户权限"""
        if not self._is_cache_enabled():
            return None
        
        cache_key = CacheKeyGenerator.permission(username)
        cached_data = self.cache_manager.get(cache_key)
        
        if cached_data:
            logging.debug(f"[CACHE] 用户权限命中缓存: {username}")
            return cached_data.get("permissions")
        
        return None
    
    def _cache_permissions(self, username: str, permissions: Dict) -> None:
        """缓存用户权限"""
        if not self._is_cache_enabled():
            return
        
        cache_key = CacheKeyGenerator.permission(username)
        cache_data = {
            "permissions": permissions,
            "cached_at": time.time()
        }
        
        self.cache_manager.set(cache_key, cache_data, ttl=self.permission_cache_ttl)
        logging.debug(f"[CACHE] 用户权限已缓存: {username}")
    
    def _get_cached_agent_config(self, agent_id: str) -> Optional[Dict]:
        """获取缓存的智能体配置"""
        if not self._is_cache_enabled():
            return None
        
        cache_key = CacheKeyGenerator.agent_config(agent_id)
        cached_data = self.cache_manager.get(cache_key)
        
        if cached_data:
            logging.debug(f"[CACHE] 智能体配置命中缓存: {agent_id}")
            return cached_data.get("config")
        
        return None
    
    def _cache_agent_config(self, agent_id: str, config: Dict) -> None:
        """缓存智能体配置"""
        if not self._is_cache_enabled():
            return
        
        cache_key = CacheKeyGenerator.agent_config(agent_id)
        cache_data = {
            "config": config,
            "cached_at": time.time()
        }
        
        self.cache_manager.set(cache_key, cache_data, ttl=self.agent_cache_ttl)
        logging.debug(f"[CACHE] 智能体配置已缓存: {agent_id}")
    
    def get_user_permissions(self, username: str, use_cache: bool = True) -> Dict:
        """获取用户权限，支持缓存"""
        # 尝试从缓存获取
        if use_cache:
            cached_permissions = self._get_cached_permissions(username)
            if cached_permissions is not None:
                return cached_permissions
        
        try:
            with open(self.agents_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 获取用户权限信息
            user_agents = data.get('user_agents', {}).get(username, [])
            agents = data.get('agents', {})
            
            permissions = {
                'user_agents': user_agents,
                'accessible_agents': [
                    {
                        'agent_id': aid,
                        'name': agents[aid].get('name', ''),
                        'permissions': agents[aid].get('permissions', ['read'])
                    }
                    for aid in user_agents if aid in agents
                ],
                'roles': data.get('user_roles', {}).get(username, ['user']),
                'last_updated': time.time()
            }
            
            # 缓存权限
            if use_cache:
                self._cache_permissions(username, permissions)
            
            return permissions
            
        except Exception as e:
            logging.error(f"[AGENT] get_user_permissions error: {e}")
            return {'user_agents': [], 'accessible_agents': [], 'roles': ['user']}
    
    def get_agent_config(self, agent_id: str, use_cache: bool = True) -> Dict:
        """获取智能体配置，支持缓存"""
        # 尝试从缓存获取
        if use_cache:
            cached_config = self._get_cached_agent_config(agent_id)
            if cached_config is not None:
                return cached_config
        
        try:
            with open(self.agents_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            agents = data.get('agents', {})
            if agent_id in agents:
                config = agents[agent_id].copy()
                config['last_updated'] = time.time()
                
                # 缓存配置
                if use_cache:
                    self._cache_agent_config(agent_id, config)
                
                return config
            else:
                return {}
                
        except Exception as e:
            logging.error(f"[AGENT] get_agent_config error: {e}")
            return {}
    
    def invalidate_agent_cache(self, username: str = None, agent_id: str = None) -> None:
        """失效智能体相关缓存"""
        if not self._is_cache_enabled():
            return
        
        patterns = []
        
        if username:
            # 清除用户的智能体列表和权限缓存
            patterns.extend([
                f"agent_list:{username}",
                f"permission:{username}"
            ])
        
        if agent_id:
            # 清除特定智能体的配置缓存
            patterns.append(f"agent_config:{agent_id}")
        
        if not username and not agent_id:
            # 清除所有智能体相关缓存
            patterns.extend([
                "agent_list:*",
                "permission:*",
                "agent_config:*"
            ])
        
        for pattern in patterns:
            deleted = self.cache_manager.delete_pattern(pattern)
            if deleted > 0:
                logging.info(f"[CACHE] 清除智能体缓存: {pattern} ({deleted} 条记录)")
    
    def preload_agent_cache(self, usernames: List[str] = None) -> Dict[str, int]:
        """预热智能体缓存"""
        if not self._is_cache_enabled():
            return {"status": "disabled", "preloaded": 0}
        
        preloaded = 0
        errors = 0
        
        try:
            with open(self.agents_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            user_agents = data.get('user_agents', {})
            agents = data.get('agents', {})
            
            # 如果没有指定用户，预热所有用户
            if usernames is None:
                usernames = list(user_agents.keys())
            
            # 预热用户智能体列表
            for username in usernames:
                try:
                    # 预热智能体列表
                    self.get_user_agents(username, use_cache=True)
                    preloaded += 1
                    
                    # 预热用户权限
                    self.get_user_permissions(username, use_cache=True)
                    preloaded += 1
                    
                except Exception as e:
                    logging.error(f"[CACHE] 预热用户缓存失败 {username}: {e}")
                    errors += 1
            
            # 预热智能体配置
            for agent_id in agents.keys():
                try:
                    self.get_agent_config(agent_id, use_cache=True)
                    preloaded += 1
                except Exception as e:
                    logging.error(f"[CACHE] 预热智能体配置失败 {agent_id}: {e}")
                    errors += 1
            
            logging.info(f"[CACHE] 预热完成: {preloaded} 个缓存项, {errors} 个错误")
            return {
                "status": "completed",
                "preloaded": preloaded,
                "errors": errors,
                "users": len(usernames),
                "agents": len(agents)
            }
            
        except Exception as e:
            logging.error(f"[CACHE] 预热失败: {e}")
            return {"status": "error", "message": str(e)}
    
    def refresh_agent_config_cache(self) -> Dict[str, Any]:
        """刷新智能体配置缓存（配置更新时调用）"""
        if not self._is_cache_enabled():
            return {"status": "disabled"}
        
        try:
            # 清除所有智能体相关缓存
            self.invalidate_agent_cache()
            
            # 重新预热缓存
            result = self.preload_agent_cache()
            
            logging.info("[CACHE] 智能体配置缓存已刷新")
            return {"status": "refreshed", "preload_result": result}
            
        except Exception as e:
            logging.error(f"[CACHE] 刷新智能体配置缓存失败: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_agent_cache_stats(self) -> Dict[str, Any]:
        """获取智能体缓存统计信息"""
        if not self._is_cache_enabled():
            return {"enabled": False, "message": "缓存未启用"}
        
        # 获取基础缓存统计
        base_stats = self.get_cache_stats()
        
        # 添加智能体特定统计
        agent_stats = {
            "agent_cache_ttl": self.agent_cache_ttl,
            "permission_cache_ttl": self.permission_cache_ttl,
            "cache_keys": {
                "agent_lists": self.cache_manager.count_keys("agent_list:*"),
                "permissions": self.cache_manager.count_keys("permission:*"),
                "agent_configs": self.cache_manager.count_keys("agent_config:*")
            }
        }
        
        # 合并统计信息
        if base_stats.get("enabled"):
            base_stats["agent_cache"] = agent_stats
        
        return base_stats

    # ========== 新增功能方法 ==========
    
    def send_message_feedback(self, message_id: str, rating: str, content: str = None, username: str = None, agent_id: str = None) -> tuple:
        """发送消息反馈（点赞/点踩）"""
        payload = {
            'rating': rating,
            'user': username,
        }
        if content:
            payload['content'] = content
        
        return self.make_request('POST', f'/messages/{message_id}/feedbacks', json_data=payload, agent_id=agent_id)
    
    def get_suggested_questions(self, message_id: str, username: str, agent_id: str = None) -> tuple:
        """获取下一轮建议问题列表"""
        params = {'user': username}
        return self.make_request('GET', f'/messages/{message_id}/suggested', params=params, agent_id=agent_id)
    
    def delete_conversation(self, conversation_id: str, username: str, agent_id: str = None) -> tuple:
        """删除对话"""
        payload = {'user': username}
        return self.make_request('DELETE', f'/conversations/{conversation_id}', json_data=payload, agent_id=agent_id)
    
    def rename_conversation(self, conversation_id: str, name: str = None, auto_generate: bool = False, username: str = None, agent_id: str = None) -> tuple:
        """重命名对话"""
        payload = {
            'user': username,
            'auto_generate': auto_generate
        }
        if name:
            payload['name'] = name
        
        return self.make_request('POST', f'/conversations/{conversation_id}/name', json_data=payload, agent_id=agent_id)
    
    def audio_to_text(self, file_data, username: str, agent_id: str = None) -> tuple:
        """语音转文字"""
        # 注意：这个需要特殊处理，因为是文件上传
        import requests
        
        # 获取API密钥
        if agent_id:
            api_key = self.get_agent_api_key(agent_id)
            if not api_key:
                logging.error(f"[DIFY] No API key available for agent_id: {agent_id}")
                return {'success': False, 'message': f'智能体 {agent_id} 的API密钥未配置'}, 500
        else:
            api_key = self.default_api_key
            if not api_key:
                return {'success': False, 'message': 'API密钥未配置'}, 500
        
        url = f"{self.base_url}/audio-to-text"
        headers = {
            'Authorization': f'Bearer {api_key}'
        }
        
        files = {'file': file_data}
        data = {'user': username}
        
        try:
            resp = requests.post(url, headers=headers, files=files, data=data, timeout=self.timeout)
            
            if resp.status_code == 200:
                return resp.json(), 200
            else:
                return {'success': False, 'message': '语音转文字失败'}, resp.status_code
                
        except Exception as e:
            logging.error(f"[DIFY] audio_to_text error: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    def text_to_audio(self, message_id: str = None, text: str = None, username: str = None, agent_id: str = None) -> tuple:
        """文字转语音"""
        payload = {'user': username}
        
        if message_id:
            payload['message_id'] = message_id
        elif text:
            payload['text'] = text
        
        return self.make_request('POST', '/text-to-audio', json_data=payload, agent_id=agent_id)
    
    def get_app_info(self, agent_id: str = None) -> tuple:
        """获取应用基本信息"""
        return self.make_request('GET', '/info', agent_id=agent_id)
    
    def get_app_parameters(self, agent_id: str = None) -> tuple:
        """获取应用参数"""
        return self.make_request('GET', '/parameters', agent_id=agent_id)
    
    def get_messages_history(self, conversation_id: str, username: str, first_id: str = None, limit: int = 20, agent_id: str = None) -> tuple:
        """获取会话历史消息"""
        params = {
            'conversation_id': conversation_id,
            'user': username,
            'limit': limit
        }
        if first_id:
            params['first_id'] = first_id
        
        return self.make_request('GET', '/messages', params=params, agent_id=agent_id)
    
    # ========== Task 5.1 新增：API监控和统计功能 ==========
    
    def get_api_stats(self) -> Dict[str, Any]:
        """获取API调用统计信息"""
        success_rate = 0.0
        if self.api_stats['total_calls'] > 0:
            success_rate = (self.api_stats['successful_calls'] / self.api_stats['total_calls']) * 100
        
        return {
            'total_calls': self.api_stats['total_calls'],
            'successful_calls': self.api_stats['successful_calls'],
            'failed_calls': self.api_stats['failed_calls'],
            'success_rate': round(success_rate, 2),
            'average_response_time': round(self.api_stats['average_response_time'], 3),
            'error_distribution': self.api_stats['error_distribution'],
            'recent_calls': self.api_stats['call_history'][-10:],  # 最近10次调用
            'cache_enabled': self._is_cache_enabled(),
            'cache_stats': self.get_cache_stats() if self._is_cache_enabled() else None
        }
    
    def reset_api_stats(self) -> None:
        """重置API统计信息"""
        self.api_stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'average_response_time': 0.0,
            'error_distribution': {},
            'call_history': []
        }
        logging.info("[DIFY SERVICE] API统计信息已重置")
    
    # ========== Task 5.1 新增：健康检查和监控 ==========
    
    @api_monitor
    def health_check(self) -> Dict[str, Any]:
        """服务健康检查"""
        try:
            # 测试API连通性
            resp, status = self.make_request('GET', '/info')
            
            api_available = status == 200
            cache_available = self._is_cache_enabled()
            
            return {
                'status': 'healthy' if api_available else 'degraded',
                'api_available': api_available,
                'cache_available': cache_available,
                'base_url': self.base_url,
                'stats': self.get_api_stats(),
                'timestamp': time.time()
            }
            
        except Exception as e:
            logging.error(f"[DIFY SERVICE] 健康检查失败: {e}")
            return {
                'status': 'unhealthy',
                'api_available': False,
                'cache_available': self._is_cache_enabled(),
                'error': str(e),
                'timestamp': time.time()
            }
    
    # ========== Task 5.1 新增：资源清理 ==========
    
    def cleanup(self):
        """清理服务资源"""
        try:
            # 清理异步会话
            if self._session and not self._session.closed:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self._close_session())
                    else:
                        loop.run_until_complete(self._close_session())
                except Exception as e:
                    logging.warning(f"[DIFY SERVICE] 清理异步会话时出错: {e}")
            
            logging.info("[DIFY SERVICE] 资源清理完成")
            
        except Exception as e:
            logging.error(f"[DIFY SERVICE] 资源清理失败: {e}")


# Task 5.1 增强：全局Dify服务实例（延迟初始化以避免导入问题）
_dify_service_instance = None

def get_dify_service() -> DifyService:
    """获取Dify服务实例（单例模式）"""
    global _dify_service_instance
    if _dify_service_instance is None:
        _dify_service_instance = DifyService()
        # 注册清理函数
        import atexit
        atexit.register(_dify_service_instance.cleanup)
    return _dify_service_instance

# 为了向后兼容，保留全局实例
dify_service = get_dify_service()
