"""
安全监控工具
监控和报告可疑的API访问活动
"""
import time
import logging
from collections import defaultdict, deque
from typing import Dict, List, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class SecurityMonitor:
    """安全监控器"""
    
    def __init__(self):
        # 存储访问模式
        self.access_patterns = defaultdict(lambda: {
            'requests': deque(),
            'endpoints': defaultdict(int),
            'user_agents': defaultdict(int),
            'first_seen': None,
            'last_seen': None,
            'total_requests': 0,
            'blocked_requests': 0
        })
        
        # 可疑活动阈值
        self.suspicious_thresholds = {
            'requests_per_minute': 30,      # 每分钟超过30次请求
            'health_check_per_minute': 5,    # 每分钟超过5次健康检查
            'failed_auth_per_hour': 10,      # 每小时超过10次认证失败
            'unique_endpoints_per_minute': 15 # 每分钟访问超过15个不同端点
        }
        
        # 自动封禁配置
        self.auto_ban_enabled = True
        self.ban_duration = 3600  # 封禁1小时
        self.banned_ips = {}  # IP -> 封禁到期时间
        
        # 监控统计
        self.stats = {
            'total_requests': 0,
            'blocked_requests': 0,
            'suspicious_activities': 0,
            'auto_bans': 0
        }
    
    def record_request(self, ip: str, endpoint: str, user_agent: str = None, 
                      status_code: int = 200, blocked: bool = False):
        """记录请求"""
        current_time = time.time()
        
        # 更新全局统计
        self.stats['total_requests'] += 1
        if blocked:
            self.stats['blocked_requests'] += 1
        
        # 记录IP访问模式
        pattern = self.access_patterns[ip]
        pattern['requests'].append({
            'timestamp': current_time,
            'endpoint': endpoint,
            'user_agent': user_agent,
            'status_code': status_code,
            'blocked': blocked
        })
        
        # 更新统计信息
        pattern['endpoints'][endpoint] += 1
        if user_agent:
            pattern['user_agents'][user_agent] += 1
        pattern['total_requests'] += 1
        if blocked:
            pattern['blocked_requests'] += 1
        
        # 更新时间戳
        if pattern['first_seen'] is None:
            pattern['first_seen'] = current_time
        pattern['last_seen'] = current_time
        
        # 清理旧数据（保留1小时的数据）
        cutoff_time = current_time - 3600
        while pattern['requests'] and pattern['requests'][0]['timestamp'] < cutoff_time:
            pattern['requests'].popleft()
        
        # 检查可疑活动
        if not blocked:  # 只检查未被阻止的请求
            self._check_suspicious_activity(ip, endpoint, current_time)
    
    def _check_suspicious_activity(self, ip: str, endpoint: str, current_time: float):
        """检查可疑活动"""
        pattern = self.access_patterns[ip]
        
        # 检查每分钟请求数
        minute_ago = current_time - 60
        recent_requests = [r for r in pattern['requests'] if r['timestamp'] > minute_ago]
        
        if len(recent_requests) > self.suspicious_thresholds['requests_per_minute']:
            self._log_suspicious_activity(ip, 'high_request_rate', {
                'requests_per_minute': len(recent_requests),
                'threshold': self.suspicious_thresholds['requests_per_minute']
            })
        
        # 检查健康检查频率
        health_check_requests = [r for r in recent_requests 
                               if r['endpoint'] in ['/health', '/api/v1/health']]
        
        if len(health_check_requests) > self.suspicious_thresholds['health_check_per_minute']:
            self._log_suspicious_activity(ip, 'health_check_abuse', {
                'health_checks_per_minute': len(health_check_requests),
                'threshold': self.suspicious_thresholds['health_check_per_minute']
            })
        
        # 检查端点多样性（可能的扫描行为）
        unique_endpoints = len(set(r['endpoint'] for r in recent_requests))
        if unique_endpoints > self.suspicious_thresholds['unique_endpoints_per_minute']:
            self._log_suspicious_activity(ip, 'endpoint_scanning', {
                'unique_endpoints_per_minute': unique_endpoints,
                'threshold': self.suspicious_thresholds['unique_endpoints_per_minute']
            })
        
        # 检查认证失败（需要从请求中获取状态码）
        hour_ago = current_time - 3600
        auth_failures = [r for r in pattern['requests'] 
                        if r['timestamp'] > hour_ago 
                        and r['endpoint'].startswith('/api/v1/auth/login')
                        and r['status_code'] in [401, 403]]
        
        if len(auth_failures) > self.suspicious_thresholds['failed_auth_per_hour']:
            self._log_suspicious_activity(ip, 'brute_force_attempt', {
                'failed_auths_per_hour': len(auth_failures),
                'threshold': self.suspicious_thresholds['failed_auth_per_hour']
            })
    
    def _log_suspicious_activity(self, ip: str, activity_type: str, details: Dict):
        """记录可疑活动"""
        self.stats['suspicious_activities'] += 1
        
        log_data = {
            'ip': ip,
            'activity_type': activity_type,
            'details': details,
            'timestamp': datetime.now().isoformat(),
        }
        
        logger.warning(f"Suspicious activity detected: {json.dumps(log_data)}")
        
        # 根据活动类型决定是否自动封禁
        if self.auto_ban_enabled and self._should_auto_ban(activity_type, details):
            self.ban_ip(ip, f"Auto-ban for {activity_type}")
    
    def _should_auto_ban(self, activity_type: str, details: Dict) -> bool:
        """判断是否应该自动封禁"""
        auto_ban_rules = {
            'high_request_rate': lambda d: d['requests_per_minute'] > 60,
            'health_check_abuse': lambda d: d['health_checks_per_minute'] > 10,
            'brute_force_attempt': lambda d: d['failed_auths_per_hour'] > 20,
            'endpoint_scanning': lambda d: d['unique_endpoints_per_minute'] > 25
        }
        
        rule = auto_ban_rules.get(activity_type)
        return rule and rule(details)
    
    def ban_ip(self, ip: str, reason: str, duration: int = None):
        """封禁IP"""
        if duration is None:
            duration = self.ban_duration
        
        ban_until = time.time() + duration
        self.banned_ips[ip] = ban_until
        self.stats['auto_bans'] += 1
        
        logger.warning(f"IP {ip} banned for {duration} seconds. Reason: {reason}")
    
    def is_ip_banned(self, ip: str) -> bool:
        """检查IP是否被封禁"""
        if ip not in self.banned_ips:
            return False
        
        ban_until = self.banned_ips[ip]
        if time.time() > ban_until:
            # 封禁已过期，移除
            del self.banned_ips[ip]
            return False
        
        return True
    
    def unban_ip(self, ip: str):
        """解除IP封禁"""
        if ip in self.banned_ips:
            del self.banned_ips[ip]
            logger.info(f"IP {ip} unbanned")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取监控统计"""
        current_time = time.time()
        
        # 清理过期的封禁
        expired_bans = [ip for ip, ban_until in self.banned_ips.items() 
                       if current_time > ban_until]
        for ip in expired_bans:
            del self.banned_ips[ip]
        
        return {
            **self.stats,
            'active_bans': len(self.banned_ips),
            'banned_ips': list(self.banned_ips.keys()),
            'monitoring_period': '1 hour',
            'timestamp': datetime.now().isoformat()
        }
    
    def get_ip_report(self, ip: str) -> Dict[str, Any]:
        """获取特定IP的报告"""
        if ip not in self.access_patterns:
            return {'error': 'IP not found'}
        
        pattern = self.access_patterns[ip]
        current_time = time.time()
        
        # 计算最近一小时的统计
        hour_ago = current_time - 3600
        recent_requests = [r for r in pattern['requests'] if r['timestamp'] > hour_ago]
        
        return {
            'ip': ip,
            'total_requests': pattern['total_requests'],
            'blocked_requests': pattern['blocked_requests'],
            'first_seen': datetime.fromtimestamp(pattern['first_seen']).isoformat() if pattern['first_seen'] else None,
            'last_seen': datetime.fromtimestamp(pattern['last_seen']).isoformat() if pattern['last_seen'] else None,
            'recent_requests_count': len(recent_requests),
            'top_endpoints': dict(sorted(pattern['endpoints'].items(), key=lambda x: x[1], reverse=True)[:10]),
            'top_user_agents': dict(sorted(pattern['user_agents'].items(), key=lambda x: x[1], reverse=True)[:5]),
            'is_banned': self.is_ip_banned(ip),
            'ban_expires': datetime.fromtimestamp(self.banned_ips[ip]).isoformat() if ip in self.banned_ips else None
        }

# 全局安全监控器实例
security_monitor = SecurityMonitor()

def get_security_monitor() -> SecurityMonitor:
    """获取安全监控器实例"""
    return security_monitor
