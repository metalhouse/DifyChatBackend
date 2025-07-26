"""
安全配置和防护措施
"""
import os
from dataclasses import dataclass
from typing import List, Dict, Any
import ipaddress
import re

@dataclass
class SecurityConfig:
    """安全配置类"""
    
    # 速率限制配置
    rate_limit_enabled: bool = True
    health_check_rate_limit: int = 10  # 每分钟最多10次健康检查
    api_rate_limit: int = 100  # 每分钟最多100次API调用
    auth_rate_limit: int = 5   # 每5分钟最多5次认证尝试
    
    # IP白名单（开发环境）
    allowed_ips: List[str] = None
    
    # WebSocket安全配置
    websocket_max_connections_per_ip: int = 5
    websocket_connection_timeout: int = 30
    websocket_message_rate_limit: int = 60  # 每分钟最多60条消息
    
    # 静态文件访问控制
    static_file_access_enabled: bool = False
    allowed_static_extensions: List[str] = None
    
    # 调试模式安全
    debug_mode_allowed_ips: List[str] = None
    
    def __post_init__(self):
        # 设置默认值
        if self.allowed_ips is None:
            self.allowed_ips = ['127.0.0.1', '::1', 'localhost']
        
        if self.allowed_static_extensions is None:
            self.allowed_static_extensions = ['.css', '.js', '.png', '.jpg', '.ico']
        
        if self.debug_mode_allowed_ips is None:
            self.debug_mode_allowed_ips = ['127.0.0.1', '::1']
    
    def is_ip_allowed(self, ip_address: str, whitelist: List[str] = None) -> bool:
        """检查IP是否在白名单中"""
        if whitelist is None:
            whitelist = self.allowed_ips
        
        try:
            client_ip = ipaddress.ip_address(ip_address)
            
            for allowed in whitelist:
                try:
                    # 支持CIDR格式
                    if '/' in allowed:
                        if client_ip in ipaddress.ip_network(allowed, strict=False):
                            return True
                    else:
                        if client_ip == ipaddress.ip_address(allowed):
                            return True
                except ValueError:
                    # 如果不是有效的IP地址，尝试域名匹配
                    if allowed.lower() == 'localhost' and ip_address in ['127.0.0.1', '::1']:
                        return True
                    
        except ValueError:
            # 无效的IP地址格式
            pass
        
        return False
    
    def is_safe_static_file(self, filename: str) -> bool:
        """检查静态文件是否安全"""
        if not self.static_file_access_enabled:
            return False
        
        # 检查文件扩展名
        for ext in self.allowed_static_extensions:
            if filename.lower().endswith(ext):
                return True
        
        return False
    
    def validate_websocket_origin(self, origin: str, allowed_origins: List[str] = None) -> bool:
        """验证WebSocket连接的Origin"""
        if not origin:
            return False
        
        if allowed_origins is None:
            allowed_origins = [
                'http://127.0.0.1:5000',
                'http://localhost:5000',
                'https://127.0.0.1:5000',
                'https://localhost:5000'
            ]
        
        return origin in allowed_origins

def get_security_config() -> SecurityConfig:
    """获取安全配置"""
    return SecurityConfig(
        rate_limit_enabled=os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true',
        health_check_rate_limit=int(os.getenv('HEALTH_CHECK_RATE_LIMIT', '10')),
        api_rate_limit=int(os.getenv('API_RATE_LIMIT', '100')),
        auth_rate_limit=int(os.getenv('AUTH_RATE_LIMIT', '5')),
        static_file_access_enabled=os.getenv('STATIC_FILE_ACCESS_ENABLED', 'false').lower() == 'true',
        websocket_max_connections_per_ip=int(os.getenv('WEBSOCKET_MAX_CONNECTIONS_PER_IP', '5')),
        websocket_connection_timeout=int(os.getenv('WEBSOCKET_CONNECTION_TIMEOUT', '30')),
        websocket_message_rate_limit=int(os.getenv('WEBSOCKET_MESSAGE_RATE_LIMIT', '60'))
    )

class SecurityMiddleware:
    """安全中间件"""
    
    def __init__(self, app, config: SecurityConfig):
        self.app = app
        self.config = config
        self.setup_security_headers()
        self.setup_static_file_protection()
    
    def setup_security_headers(self):
        """设置安全头"""
        @self.app.after_request
        def add_security_headers(response):
            # 防止点击劫持
            response.headers['X-Frame-Options'] = 'DENY'
            
            # 防止MIME类型嗅探
            response.headers['X-Content-Type-Options'] = 'nosniff'
            
            # XSS保护
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # 强制HTTPS（生产环境）
            if not self.app.debug:
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
            # CSP策略
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "connect-src 'self' ws: wss:; "
                "font-src 'self'"
            )
            response.headers['Content-Security-Policy'] = csp
            
            return response
    
    def setup_static_file_protection(self):
        """设置静态文件保护"""
        @self.app.before_request
        def protect_static_files():
            from flask import request, abort
            
            # 检查是否为静态文件请求
            if request.path.startswith('/static/') or any(request.path.endswith(ext) for ext in ['.html', '.htm']):
                # 如果是HTML文件且不在允许列表中，拒绝访问
                if request.path.endswith(('.html', '.htm')):
                    # 允许特定的HTML文件（如果需要）
                    allowed_html_files = []  # 可以在这里添加允许的HTML文件
                    
                    if not any(request.path.endswith(allowed) for allowed in allowed_html_files):
                        abort(403)
                
                # 检查其他静态文件
                if not self.config.is_safe_static_file(request.path):
                    abort(403)

def setup_security(app):
    """设置应用安全措施"""
    config = get_security_config()
    
    # 应用安全中间件
    SecurityMiddleware(app, config)
    
    # 禁用调试模式下的自动重载（生产环境）
    if not app.debug:
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
    
    # 设置会话安全
    app.config['SESSION_COOKIE_SECURE'] = not app.debug
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    return config
