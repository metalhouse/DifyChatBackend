"""
Dify API服务模块 (重构版本)
提供与Dify平台的API交互功能，支持异步HTTP客户端、重试机制、监控等
"""
import asyncio
import aiohttp
import requests
import logging
import time
import json
from functools import wraps
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from config import get_dify_config, get_database_config
from utils.cache_manager import get_cache_manager, CacheKeyGenerator


@dataclass
class APICallMetrics:
    """API调用指标"""
    endpoint: str
    method: str
    status_code: int
    response_time: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    agent_id: Optional[str] = None
    username: Optional[str] = None


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_delay: float = 1.0  # 基础延迟时间（秒）
    max_delay: float = 60.0  # 最大延迟时间（秒）
    exponential_base: float = 2.0  # 指数退避基数
    retryable_status_codes: List[int] = None  # 可重试的状态码
    
    def __post_init__(self):
        if self.retryable_status_codes is None:
            self.retryable_status_codes = [429, 500, 502, 503, 504]


class DifyServiceV2:
    """Dify API服务类 (重构版本)"""
    
    def __init__(self, base_url: str = None, api_key: str = None):
        # 配置初始化
        dify_config = get_dify_config()
        db_config = get_database_config()
        
        self.base_url = base_url or dify_config.base_url
        self.default_api_key = api_key or dify_config.default_api_key
        self.timeout = dify_config.timeout
        self.agents_file = db_config.agents_file
        
        # 重试配置
        self.retry_config = RetryConfig(
            max_retries=getattr(dify_config, 'max_retries', 3),
            base_delay=getattr(dify_config, 'retry_base_delay', 1.0),
            max_delay=getattr(dify_config, 'retry_max_delay', 60.0)
        )
        
        # 缓存配置
        self.cache_manager = get_cache_manager()
        self.conversation_cache_ttl = 300  # 5分钟
        self.agent_cache_ttl = 3600  # 1小时
        self.permission_cache_ttl = 1800  # 30分钟
        
        # 监控和指标
        self.metrics: List[APICallMetrics] = []
        self.max_metrics_history = 1000  # 最多保留1000条指标记录
        
        # 异步HTTP会话
        self._async_session: Optional[aiohttp.ClientSession] = None
        
        # 同步HTTP会话
        self._sync_session = requests.Session()
        self._sync_session.timeout = self.timeout
        
        # 设置默认请求头
        self._default_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'DifyChatBackend/2.0'
        }
        
        # 初始化日志
        self.logger = logging.getLogger(__name__)
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._ensure_async_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self._close_async_session()
        
    def __del__(self):
        """析构函数，确保会话正确关闭"""
        if self._sync_session:
            self._sync_session.close()
            
    async def _ensure_async_session(self) -> aiohttp.ClientSession:
        """确保异步会话可用"""
        if self._async_session is None or self._async_session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,  # 总连接池大小
                limit_per_host=30,  # 每个主机的连接数
                ttl_dns_cache=300,  # DNS缓存TTL
                use_dns_cache=True,
            )
            
            timeout = aiohttp.ClientTimeout(
                total=self.timeout,
                connect=10,  # 连接超时
                sock_read=30  # 读取超时
            )
            
            self._async_session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self._default_headers
            )
            
        return self._async_session
        
    async def _close_async_session(self):
        """关闭异步会话"""
        if self._async_session and not self._async_session.closed:
            await self._async_session.close()
            self._async_session = None
            
    def _is_cache_enabled(self) -> bool:
        """检查缓存是否可用"""
        return self.cache_manager and self.cache_manager.enabled
        
    def _record_metrics(self, metrics: APICallMetrics):
        """记录API调用指标"""
        self.metrics.append(metrics)
        
        # 限制指标历史记录数量
        if len(self.metrics) > self.max_metrics_history:
            self.metrics = self.metrics[-self.max_metrics_history:]
            
        # 记录日志
        log_level = logging.INFO if metrics.success else logging.ERROR
        self.logger.log(
            log_level,
            f"[DIFY API] {metrics.method} {metrics.endpoint} - "
            f"Status: {metrics.status_code}, Time: {metrics.response_time:.3f}s, "
            f"Agent: {metrics.agent_id or 'default'}, User: {metrics.username or 'unknown'}"
        )
        
        if not metrics.success and metrics.error_message:
            self.logger.error(f"[DIFY API ERROR] {metrics.error_message}")
            
    def _calculate_retry_delay(self, attempt: int) -> float:
        """计算重试延迟时间（指数退避）"""
        delay = self.retry_config.base_delay * (
            self.retry_config.exponential_base ** attempt
        )
        return min(delay, self.retry_config.max_delay)
        
    def _should_retry(self, status_code: int, attempt: int) -> bool:
        """判断是否应该重试"""
        if attempt >= self.retry_config.max_retries:
            return False
            
        return status_code in self.retry_config.retryable_status_codes
        
    def get_agent_api_key(self, agent_id: str) -> Optional[str]:
        """获取智能体API密钥"""
        try:
            with open(self.agents_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            agents = data.get('agents', {})
            agent_info = agents.get(agent_id, {})
            return agent_info.get('api_key')
            
        except Exception as e:
            self.logger.error(f"[DIFY] Failed to get API key for agent {agent_id}: {e}")
            return None
            
    def _get_api_key(self, agent_id: str = None) -> Tuple[Optional[str], Optional[str]]:
        """获取API密钥，返回(api_key, actual_agent_id)"""
        if agent_id:
            api_key = self.get_agent_api_key(agent_id)
            if api_key:
                return api_key, agent_id
            else:
                self.logger.error(f"[DIFY] No API key available for agent_id: {agent_id}")
                return None, None
        
        # 使用默认API密钥
        if self.default_api_key:
            return self.default_api_key, None
            
        # 尝试获取第一个可用智能体的API密钥
        try:
            with open(self.agents_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            agents = data.get('agents', {})
            if agents:
                first_agent_id = list(agents.keys())[0]
                api_key = self.get_agent_api_key(first_agent_id)
                if api_key:
                    self.logger.info(f"[DIFY] Using first available agent key: {first_agent_id}")
                    return api_key, first_agent_id
        except Exception as e:
            self.logger.error(f"[DIFY] Failed to get fallback API key: {e}")
            
        self.logger.error("[DIFY] No API key available")
        return None, None
        
    async def _make_async_request(
        self, 
        method: str, 
        path: str, 
        params: Dict = None,
        json_data: Dict = None, 
        data: Any = None,
        files: Dict = None,
        stream: bool = False,
        agent_id: str = None,
        username: str = None
    ) -> Tuple[Dict, int]:
        """异步HTTP请求"""
        start_time = time.time()
        url = f"{self.base_url}{path}"
        endpoint = path
        
        # 获取API密钥
        api_key, actual_agent_id = self._get_api_key(agent_id)
        if not api_key:
            metrics = APICallMetrics(
                endpoint=endpoint,
                method=method,
                status_code=500,
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                success=False,
                error_message="API密钥未配置",
                agent_id=actual_agent_id,
                username=username
            )
            self._record_metrics(metrics)
            return {'success': False, 'message': 'API密钥未配置'}, 500
            
        headers = {
            'Authorization': f'Bearer {api_key}',
            **self._default_headers
        }
        
        session = await self._ensure_async_session()
        
        # 重试逻辑
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                # 构建请求参数
                kwargs = {}
                if params:
                    kwargs['params'] = params
                if json_data:
                    kwargs['json'] = json_data
                if data:
                    kwargs['data'] = data
                if files:
                    # 对于文件上传，移除Content-Type让aiohttp自动设置
                    file_headers = {k: v for k, v in headers.items() if k != 'Content-Type'}
                    kwargs['data'] = aiohttp.FormData()
                    for key, value in files.items():
                        kwargs['data'].add_field(key, value)
                    if data:
                        for key, value in data.items():
                            kwargs['data'].add_field(key, value)
                    headers = file_headers
                    
                async with session.request(
                    method.upper(), 
                    url, 
                    headers=headers,
                    **kwargs
                ) as response:
                    response_time = time.time() - start_time
                    
                    if stream:
                        # 流式响应处理
                        metrics = APICallMetrics(
                            endpoint=endpoint,
                            method=method,
                            status_code=response.status,
                            response_time=response_time,
                            timestamp=datetime.now(),
                            success=response.status == 200,
                            agent_id=actual_agent_id,
                            username=username
                        )
                        self._record_metrics(metrics)
                        return response, 200
                        
                    # 解析响应
                    try:
                        if response.content_type == 'application/json':
                            response_data = await response.json()
                        else:
                            response_text = await response.text()
                            response_data = {'success': False, 'message': response_text}
                    except Exception as e:
                        response_data = {'success': False, 'message': f'响应解析失败: {str(e)}'}
                        
                    # 记录指标
                    success = response.status == 200
                    error_message = None if success else response_data.get('message', f'HTTP {response.status}')
                    
                    metrics = APICallMetrics(
                        endpoint=endpoint,
                        method=method,
                        status_code=response.status,
                        response_time=response_time,
                        timestamp=datetime.now(),
                        success=success,
                        error_message=error_message,
                        agent_id=actual_agent_id,
                        username=username
                    )
                    self._record_metrics(metrics)
                    
                    # 检查是否需要重试
                    if not success and self._should_retry(response.status, attempt):
                        if attempt < self.retry_config.max_retries:
                            delay = self._calculate_retry_delay(attempt)
                            self.logger.warning(
                                f"[DIFY] Request failed with status {response.status}, "
                                f"retrying in {delay:.2f}s (attempt {attempt + 1}/{self.retry_config.max_retries})"
                            )
                            await asyncio.sleep(delay)
                            continue
                            
                    return response_data, response.status
                    
            except asyncio.TimeoutError:
                response_time = time.time() - start_time
                error_message = "请求超时"
                
                if attempt < self.retry_config.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    self.logger.warning(
                        f"[DIFY] Request timeout, retrying in {delay:.2f}s "
                        f"(attempt {attempt + 1}/{self.retry_config.max_retries})"
                    )
                    await asyncio.sleep(delay)
                    continue
                    
                metrics = APICallMetrics(
                    endpoint=endpoint,
                    method=method,
                    status_code=408,
                    response_time=response_time,
                    timestamp=datetime.now(),
                    success=False,
                    error_message=error_message,
                    agent_id=actual_agent_id,
                    username=username
                )
                self._record_metrics(metrics)
                return {'success': False, 'message': error_message}, 408
                
            except Exception as e:
                response_time = time.time() - start_time
                error_message = f"请求异常: {str(e)}"
                
                if attempt < self.retry_config.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    self.logger.warning(
                        f"[DIFY] Request exception: {e}, retrying in {delay:.2f}s "
                        f"(attempt {attempt + 1}/{self.retry_config.max_retries})"
                    )
                    await asyncio.sleep(delay)
                    continue
                    
                metrics = APICallMetrics(
                    endpoint=endpoint,
                    method=method,
                    status_code=500,
                    response_time=response_time,
                    timestamp=datetime.now(),
                    success=False,
                    error_message=error_message,
                    agent_id=actual_agent_id,
                    username=username
                )
                self._record_metrics(metrics)
                return {'success': False, 'message': error_message}, 500
                
        # 所有重试都失败了
        return {'success': False, 'message': '请求失败，已达到最大重试次数'}, 500
        
    def _make_sync_request(
        self, 
        method: str, 
        path: str, 
        params: Dict = None,
        json_data: Dict = None, 
        data: Any = None,
        files: Dict = None,
        stream: bool = False,
        agent_id: str = None,
        username: str = None
    ) -> Tuple[Dict, int]:
        """同步HTTP请求（带重试机制）"""
        start_time = time.time()
        url = f"{self.base_url}{path}"
        endpoint = path
        
        # 获取API密钥
        api_key, actual_agent_id = self._get_api_key(agent_id)
        if not api_key:
            metrics = APICallMetrics(
                endpoint=endpoint,
                method=method,
                status_code=500,
                response_time=time.time() - start_time,
                timestamp=datetime.now(),
                success=False,
                error_message="API密钥未配置",
                agent_id=actual_agent_id,
                username=username
            )
            self._record_metrics(metrics)
            return {'success': False, 'message': 'API密钥未配置'}, 500
            
        headers = {
            'Authorization': f'Bearer {api_key}',
            **self._default_headers
        }
        
        # 重试逻辑
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                # 构建请求参数
                kwargs = {}
                if params:
                    kwargs['params'] = params
                if json_data:
                    kwargs['json'] = json_data
                if data and not files:
                    kwargs['data'] = data
                if files:
                    kwargs['files'] = files
                    if data:
                        kwargs['data'] = data
                    # 对于文件上传，移除Content-Type让requests自动设置
                    file_headers = {k: v for k, v in headers.items() if k != 'Content-Type'}
                    headers = file_headers
                    
                response = self._sync_session.request(
                    method.upper(), 
                    url, 
                    headers=headers,
                    stream=stream,
                    **kwargs
                )
                
                response_time = time.time() - start_time
                
                if stream:
                    # 流式响应处理
                    metrics = APICallMetrics(
                        endpoint=endpoint,
                        method=method,
                        status_code=response.status_code,
                        response_time=response_time,
                        timestamp=datetime.now(),
                        success=response.status_code == 200,
                        agent_id=actual_agent_id,
                        username=username
                    )
                    self._record_metrics(metrics)
                    return response, 200
                    
                # 解析响应
                try:
                    if response.headers.get('Content-Type', '').startswith('application/json'):
                        response_data = response.json()
                    else:
                        response_data = {'success': False, 'message': response.text}
                except Exception as e:
                    response_data = {'success': False, 'message': f'响应解析失败: {str(e)}'}
                    
                # 记录指标
                success = response.status_code == 200
                error_message = None if success else response_data.get('message', f'HTTP {response.status_code}')
                
                metrics = APICallMetrics(
                    endpoint=endpoint,
                    method=method,
                    status_code=response.status_code,
                    response_time=response_time,
                    timestamp=datetime.now(),
                    success=success,
                    error_message=error_message,
                    agent_id=actual_agent_id,
                    username=username
                )
                self._record_metrics(metrics)
                
                # 检查是否需要重试
                if not success and self._should_retry(response.status_code, attempt):
                    if attempt < self.retry_config.max_retries:
                        delay = self._calculate_retry_delay(attempt)
                        self.logger.warning(
                            f"[DIFY] Request failed with status {response.status_code}, "
                            f"retrying in {delay:.2f}s (attempt {attempt + 1}/{self.retry_config.max_retries})"
                        )
                        time.sleep(delay)
                        continue
                        
                return response_data, response.status_code
                
            except requests.exceptions.Timeout:
                response_time = time.time() - start_time
                error_message = "请求超时"
                
                if attempt < self.retry_config.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    self.logger.warning(
                        f"[DIFY] Request timeout, retrying in {delay:.2f}s "
                        f"(attempt {attempt + 1}/{self.retry_config.max_retries})"
                    )
                    time.sleep(delay)
                    continue
                    
                metrics = APICallMetrics(
                    endpoint=endpoint,
                    method=method,
                    status_code=408,
                    response_time=response_time,
                    timestamp=datetime.now(),
                    success=False,
                    error_message=error_message,
                    agent_id=actual_agent_id,
                    username=username
                )
                self._record_metrics(metrics)
                return {'success': False, 'message': error_message}, 408
                
            except Exception as e:
                response_time = time.time() - start_time
                error_message = f"请求异常: {str(e)}"
                
                if attempt < self.retry_config.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    self.logger.warning(
                        f"[DIFY] Request exception: {e}, retrying in {delay:.2f}s "
                        f"(attempt {attempt + 1}/{self.retry_config.max_retries})"
                    )
                    time.sleep(delay)
                    continue
                    
                metrics = APICallMetrics(
                    endpoint=endpoint,
                    method=method,
                    status_code=500,
                    response_time=response_time,
                    timestamp=datetime.now(),
                    success=False,
                    error_message=error_message,
                    agent_id=actual_agent_id,
                    username=username
                )
                self._record_metrics(metrics)
                return {'success': False, 'message': error_message}, 500
                
        # 所有重试都失败了
        return {'success': False, 'message': '请求失败，已达到最大重试次数'}, 500
 
         #   = = = = = = = = = =   �v�c�T�~���e�l  = = = = = = = = = = 
         
         d e f   g e t _ a p i _ m e t r i c s ( 
                 s e l f ,   
                 s t a r t _ t i m e :   O p t i o n a l [ d a t e t i m e ]   =   N o n e ,   
                 e n d _ t i m e :   O p t i o n a l [ d a t e t i m e ]   =   N o n e , 
                 a g e n t _ i d :   O p t i o n a l [ s t r ]   =   N o n e , 
                 u s e r n a m e :   O p t i o n a l [ s t r ]   =   N o n e 
         )   - >   D i c t [ s t r ,   A n y ] : 
                 \  
 \ \ ���SA P I �(uch\ \ \ 
                 f i l t e r e d _ m e t r i c s   =   s e l f . m e t r i c s 
                 
                 #   �e��Ǐ�n
                 i f   s t a r t _ t i m e : 
                         f i l t e r e d _ m e t r i c s   =   [ m   f o r   m   i n   f i l t e r e d _ m e t r i c s   i f   m . t i m e s t a m p   > =   s t a r t _ t i m e ] 
                 i f   e n d _ t i m e : 
                         f i l t e r e d _ m e t r i c s   =   [ m   f o r   m   i n   f i l t e r e d _ m e t r i c s   i f   m . t i m e s t a m p   < =   e n d _ t i m e ] 
                         
                 #   zf��SOǏ�n
                 i f   a g e n t _ i d : 
                         f i l t e r e d _ m e t r i c s   =   [ m   f o r   m   i n   f i l t e r e d _ m e t r i c s   i f   m . a g e n t _ i d   = =   a g e n t _ i d ] 
                         
                 #   (u7bǏ�n
                 i f   u s e r n a m e : 
                         f i l t e r e d _ m e t r i c s   =   [ m   f o r   m   i n   f i l t e r e d _ m e t r i c s   i f   m . u s e r n a m e   = =   u s e r n a m e ] 
                         
                 i f   n o t   f i l t e r e d _ m e t r i c s : 
                         r e t u r n   { 
                                 ' t o t a l _ r e q u e s t s ' :   0 , 
                                 ' s u c c e s s _ r e q u e s t s ' :   0 , 
                                 ' f a i l e d _ r e q u e s t s ' :   0 , 
                                 ' s u c c e s s _ r a t e ' :   0 . 0 , 
                                 ' a v e r a g e _ r e s p o n s e _ t i m e ' :   0 . 0 , 
                                 ' e n d p o i n t s ' :   { } , 
                                 ' s t a t u s _ c o d e s ' :   { } , 
                                 ' e r r o r _ m e s s a g e s ' :   [ ] 
                         } 
                         
                 t o t a l _ r e q u e s t s   =   l e n ( f i l t e r e d _ m e t r i c s ) 
                 s u c c e s s _ r e q u e s t s   =   l e n ( [ m   f o r   m   i n   f i l t e r e d _ m e t r i c s   i f   m . s u c c e s s ] ) 
                 f a i l e d _ r e q u e s t s   =   t o t a l _ r e q u e s t s   -   s u c c e s s _ r e q u e s t s 
                 s u c c e s s _ r a t e   =   ( s u c c e s s _ r e q u e s t s   /   t o t a l _ r e q u e s t s )   *   1 0 0   i f   t o t a l _ r e q u e s t s   >   0   e l s e   0 
                 
                 r e s p o n s e _ t i m e s   =   [ m . r e s p o n s e _ t i m e   f o r   m   i n   f i l t e r e d _ m e t r i c s ] 
                 a v e r a g e _ r e s p o n s e _ t i m e   =   s u m ( r e s p o n s e _ t i m e s )   /   l e n ( r e s p o n s e _ t i m e s )   i f   r e s p o n s e _ t i m e s   e l s e   0 
                 
                 #   �z�p�~��
                 e n d p o i n t s   =   { } 
                 f o r   m e t r i c   i n   f i l t e r e d _ m e t r i c s : 
                         k e y   =   f \  
 m e t r i c . m e t h o d  
 m e t r i c . e n d p o i n t  
 \ 
                         i f   k e y   n o t   i n   e n d p o i n t s : 
                                 e n d p o i n t s [ k e y ]   =   { ' c o u n t ' :   0 ,   ' s u c c e s s ' :   0 ,   ' a v g _ t i m e ' :   0 . 0 } 
                         e n d p o i n t s [ k e y ] [ ' c o u n t ' ]   + =   1 
                         i f   m e t r i c . s u c c e s s : 
                                 e n d p o i n t s [ k e y ] [ ' s u c c e s s ' ]   + =   1 
                         e n d p o i n t s [ k e y ] [ ' a v g _ t i m e ' ]   =   ( 
                                 ( e n d p o i n t s [ k e y ] [ ' a v g _ t i m e ' ]   *   ( e n d p o i n t s [ k e y ] [ ' c o u n t ' ]   -   1 )   +   m e t r i c . r e s p o n s e _ t i m e )   
                                 /   e n d p o i n t s [ k e y ] [ ' c o u n t ' ] 
                         ) 
                         
                 #   �r`x�~��
                 s t a t u s _ c o d e s   =   { } 
                 f o r   m e t r i c   i n   f i l t e r e d _ m e t r i c s : 
                         s t a t u s _ c o d e s [ m e t r i c . s t a t u s _ c o d e ]   =   s t a t u s _ c o d e s . g e t ( m e t r i c . s t a t u s _ c o d e ,   0 )   +   1 
                         
                 #   �mo`�~��
                 e r r o r _ m e s s a g e s   =   [ 
                         { ' t i m e s t a m p ' :   m . t i m e s t a m p . i s o f o r m a t ( ) ,   ' m e s s a g e ' :   m . e r r o r _ m e s s a g e ,   ' e n d p o i n t ' :   m . e n d p o i n t } 
                         f o r   m   i n   f i l t e r e d _ m e t r i c s   
                         i f   n o t   m . s u c c e s s   a n d   m . e r r o r _ m e s s a g e 
                 ] 
                 
                 r e t u r n   { 
                         ' t o t a l _ r e q u e s t s ' :   t o t a l _ r e q u e s t s , 
                         ' s u c c e s s _ r e q u e s t s ' :   s u c c e s s _ r e q u e s t s , 
                         ' f a i l e d _ r e q u e s t s ' :   f a i l e d _ r e q u e s t s , 
                         ' s u c c e s s _ r a t e ' :   r o u n d ( s u c c e s s _ r a t e ,   2 ) , 
                         ' a v e r a g e _ r e s p o n s e _ t i m e ' :   r o u n d ( a v e r a g e _ r e s p o n s e _ t i m e ,   3 ) , 
                         ' e n d p o i n t s ' :   e n d p o i n t s , 
                         ' s t a t u s _ c o d e s ' :   s t a t u s _ c o d e s , 
                         ' e r r o r _ m e s s a g e s ' :   e r r o r _ m e s s a g e s [ - 1 0 : ]     #    gя1 0 *N��
                 } 
                 
         d e f   h e a l t h _ c h e c k ( s e l f )   - >   D i c t [ s t r ,   A n y ] : 
                 \ \ \ eP�^�h�g\ \ \ 
                 t r y : 
                         #   KmՋA P I ޏ�c
                         s t a r t _ t i m e   =   t i m e . t i m e ( ) 
                         r e s p o n s e _ d a t a ,   s t a t u s _ c o d e   =   s e l f . m a k e _ r e q u e s t ( ' G E T ' ,   ' / i n f o ' ) 
                         r e s p o n s e _ t i m e   =   t i m e . t i m e ( )   -   s t a r t _ t i m e 
                         
                         a p i _ h e a l t h y   =   s t a t u s _ c o d e   = =   2 0 0 
                         
                         #   �h�gX[
                         c a c h e _ h e a l t h y   =   T r u e 
                         c a c h e _ i n f o   =   { } 
                         i f   s e l f . _ i s _ c a c h e _ e n a b l e d ( ) : 
                                 t r y : 
                                         c a c h e _ i n f o   =   s e l f . c a c h e _ m a n a g e r . g e t _ i n f o ( ) 
                                 e x c e p t   E x c e p t i o n   a s   e : 
                                         c a c h e _ h e a l t h y   =   F a l s e 
                                         c a c h e _ i n f o   =   { ' e r r o r ' :   s t r ( e ) } 
                         e l s e : 
                                 c a c h e _ i n f o   =   { ' s t a t u s ' :   ' d i s a b l e d ' } 
                                 
                         r e t u r n   { 
                                 ' t i m e s t a m p ' :   d a t e t i m e . n o w ( ) . i s o f o r m a t ( ) , 
                                 ' a p i ' :   { 
                                         ' h e a l t h y ' :   a p i _ h e a l t h y , 
                                         ' r e s p o n s e _ t i m e ' :   r o u n d ( r e s p o n s e _ t i m e ,   3 ) , 
                                         ' b a s e _ u r l ' :   s e l f . b a s e _ u r l , 
                                         ' s t a t u s _ c o d e ' :   s t a t u s _ c o d e 
                                 } , 
                                 ' c a c h e ' :   { 
                                         ' h e a l t h y ' :   c a c h e _ h e a l t h y , 
                                         ' e n a b l e d ' :   s e l f . _ i s _ c a c h e _ e n a b l e d ( ) , 
                                         ' i n f o ' :   c a c h e _ i n f o 
                                 } , 
                                 ' m e t r i c s ' :   { 
                                         ' t o t a l _ r e c o r d e d ' :   l e n ( s e l f . m e t r i c s ) , 
                                         ' r e c e n t _ s u c c e s s _ r a t e ' :   s e l f . _ g e t _ r e c e n t _ s u c c e s s _ r a t e ( ) 
                                 } , 
                                 ' o v e r a l l _ h e a l t h y ' :   a p i _ h e a l t h y   a n d   c a c h e _ h e a l t h y 
                         } 
                 e x c e p t   E x c e p t i o n   a s   e : 
                         r e t u r n   { 
                                 ' t i m e s t a m p ' :   d a t e t i m e . n o w ( ) . i s o f o r m a t ( ) , 
                                 ' e r r o r ' :   s t r ( e ) , 
                                 ' o v e r a l l _ h e a l t h y ' :   F a l s e 
                         } 
                         
         d e f   _ g e t _ r e c e n t _ s u c c e s s _ r a t e ( s e l f ,   m i n u t e s :   i n t   =   1 0 )   - >   f l o a t : 
                 \ \ \ ���S gяN R���vb�R�s\ \ \ 
                 c u t o f f _ t i m e   =   d a t e t i m e . n o w ( )   -   t i m e d e l t a ( m i n u t e s = m i n u t e s ) 
                 r e c e n t _ m e t r i c s   =   [ m   f o r   m   i n   s e l f . m e t r i c s   i f   m . t i m e s t a m p   > =   c u t o f f _ t i m e ] 
                 
                 i f   n o t   r e c e n t _ m e t r i c s : 
                         r e t u r n   1 0 0 . 0 
                         
                 s u c c e s s _ c o u n t   =   l e n ( [ m   f o r   m   i n   r e c e n t _ m e t r i c s   i f   m . s u c c e s s ] ) 
                 r e t u r n   r o u n d ( ( s u c c e s s _ c o u n t   /   l e n ( r e c e n t _ m e t r i c s ) )   *   1 0 0 ,   2 ) 
 
 
 #   = = = = = = = = = =   _ek�]wQ�Qpe  = = = = = = = = = = 
 
 a s y n c   d e f   c r e a t e _ a s y n c _ d i f y _ s e r v i c e ( b a s e _ u r l :   O p t i o n a l [ s t r ]   =   N o n e ,   a p i _ k e y :   O p t i o n a l [ s t r ]   =   N o n e )   - >   D i f y S e r v i c e V 2 : 
         \ \ \ R�^_ekD i f y g�R�[�O\ \ \ 
         s e r v i c e   =   D i f y S e r v i c e V 2 ( b a s e _ u r l = b a s e _ u r l ,   a p i _ k e y = a p i _ k e y ) 
         a w a i t   s e r v i c e . _ e n s u r e _ a s y n c _ s e s s i o n ( ) 
         r e t u r n   s e r v i c e 
 
 
 #   = = = = = = = = = =   hQ@\g�R�[�O  = = = = = = = = = = 
 
 #   �OcN�s	g�Nx|Q�[�vhQ@\�[�O
 d i f y _ s e r v i c e _ v 2   =   D i f y S e r v i c e V 2 ( ) 
 
 #   :N�NTT|Q�[��S�N	��b'`0W�fbc�S	g�vd i f y _ s e r v i c e 
 #   d i f y _ s e r v i c e   =   d i f y _ s e r v i c e _ v 2  
 