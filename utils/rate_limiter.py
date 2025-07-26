"""
速率限制中间件
防止API端点被恶意频繁调用
"""
import time
import os
from functools import wraps
from flask import request, g
from collections import defaultdict, deque
from utils.response_builder import ResponseBuilder, ErrorCode
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """简单的速率限制器"""
    
    def __init__(self):
        # 存储每个IP的请求时间戳
        self.requests = defaultdict(deque)
        # 清理任务的最后执行时间
        self.last_cleanup = time.time()
    
    def is_allowed(self, identifier: str, max_requests: int, window_seconds: int) -> bool:
        """
        检查是否允许请求
        
        Args:
            identifier: 标识符（通常是IP地址）
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口大小（秒）
        
        Returns:
            bool: 是否允许请求
        """
        current_time = time.time()
        
        # 定期清理过期数据
        if current_time - self.last_cleanup > 300:  # 每5分钟清理一次
            self._cleanup_expired_requests(current_time, window_seconds)
            self.last_cleanup = current_time
        
        # 获取该标识符的请求队列
        request_times = self.requests[identifier]
        
        # 移除过期的请求记录
        cutoff_time = current_time - window_seconds
        while request_times and request_times[0] < cutoff_time:
            request_times.popleft()
        
        # 检查是否超过限制
        if len(request_times) >= max_requests:
            logger.warning(f"Rate limit exceeded for {identifier}: {len(request_times)} requests in {window_seconds}s")
            return False
        
        # 记录当前请求
        request_times.append(current_time)
        return True
    
    def _cleanup_expired_requests(self, current_time: float, window_seconds: int):
        """清理过期的请求记录"""
        cutoff_time = current_time - window_seconds * 2  # 保留2倍窗口时间的数据
        
        for identifier in list(self.requests.keys()):
            request_times = self.requests[identifier]
            
            # 移除过期记录
            while request_times and request_times[0] < cutoff_time:
                request_times.popleft()
            
            # 如果队列为空，删除该标识符
            if not request_times:
                del self.requests[identifier]

# 全局速率限制器实例
rate_limiter = RateLimiter()

def rate_limit(max_requests: int = 60, window_seconds: int = 60, per_ip: bool = True):
    """
    速率限制装饰器
    
    Args:
        max_requests: 时间窗口内最大请求数
        window_seconds: 时间窗口大小（秒）
        per_ip: 是否按IP限制（否则按用户ID限制）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 确定限制标识符
            if per_ip:
                identifier = request.remote_addr or 'unknown'
                # 考虑代理情况
                if 'X-Forwarded-For' in request.headers:
                    identifier = request.headers['X-Forwarded-For'].split(',')[0].strip()
                elif 'X-Real-IP' in request.headers:
                    identifier = request.headers['X-Real-IP']
            else:
                # 按用户ID限制
                user_info = getattr(g, 'current_user', {})
                identifier = user_info.get('user_id', request.remote_addr or 'unknown')
            
            # 集成安全监控
            try:
                from utils.security_monitor import get_security_monitor
                monitor = get_security_monitor()
                
                # 检查IP是否被封禁
                if monitor.is_ip_banned(identifier):
                    logger.warning(f"Blocked request from banned IP: {identifier}")
                    monitor.record_request(identifier, request.endpoint, 
                                         request.headers.get('User-Agent'), 
                                         403, blocked=True)
                    return ResponseBuilder.error(
                        error_code=ErrorCode.ACCESS_DENIED,
                        message="IP地址已被封禁",
                        data={'reason': 'IP banned due to suspicious activity'}
                    )
                    
            except ImportError:
                # 如果安全监控不可用，继续执行
                monitor = None
            
            # 检查速率限制
            if not rate_limiter.is_allowed(identifier, max_requests, window_seconds):
                logger.warning(f"Rate limit exceeded for {identifier} on {request.endpoint}")
                
                # 记录到安全监控
                if monitor:
                    monitor.record_request(identifier, request.endpoint, 
                                         request.headers.get('User-Agent'), 
                                         429, blocked=True)
                
                return ResponseBuilder.error(
                    error_code=ErrorCode.RATE_LIMITED,
                    message=f"请求过于频繁，请在{window_seconds}秒后重试",
                    data={
                        'retry_after': window_seconds,
                        'max_requests': max_requests,
                        'window_seconds': window_seconds
                    }
                )
            
            # 执行原函数
            response = func(*args, **kwargs)
            
            # 记录成功的请求
            if monitor:
                status_code = 200
                if hasattr(response, 'status_code'):
                    status_code = response.status_code
                elif isinstance(response, tuple) and len(response) > 1:
                    status_code = response[1]
                    
                monitor.record_request(identifier, request.endpoint, 
                                     request.headers.get('User-Agent'), 
                                     status_code, blocked=False)
            
            return response
        return wrapper
    return decorator

def health_check_rate_limit():
    """专门为健康检查端点设计的速率限制"""
    max_requests = int(os.getenv('RATE_LIMIT_HEALTH_MAX_REQUESTS', '10'))
    window_seconds = int(os.getenv('RATE_LIMIT_HEALTH_WINDOW_SECONDS', '60'))
    return rate_limit(max_requests=max_requests, window_seconds=window_seconds, per_ip=True)

def api_rate_limit():
    """API端点的标准速率限制"""
    max_requests = int(os.getenv('RATE_LIMIT_API_MAX_REQUESTS', '100'))
    window_seconds = int(os.getenv('RATE_LIMIT_API_WINDOW_SECONDS', '60'))
    return rate_limit(max_requests=max_requests, window_seconds=window_seconds, per_ip=True)

def auth_rate_limit():
    """认证端点的速率限制"""
    max_requests = int(os.getenv('RATE_LIMIT_AUTH_MAX_REQUESTS', '50'))
    window_seconds = int(os.getenv('RATE_LIMIT_AUTH_WINDOW_SECONDS', '300'))
    return rate_limit(max_requests=max_requests, window_seconds=window_seconds, per_ip=True)
