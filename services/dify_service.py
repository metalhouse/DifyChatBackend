"""
Dify API服务模块
提供与Dify平台的API交互功能，支持缓存
"""
import requests
import logging
from functools import wraps
import json
import time
from typing import Optional, List, Dict, Any, Tuple
from config import get_dify_config, get_database_config
from utils.cache_manager import get_cache_manager, CacheKeyGenerator


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
        
        # 缓存配置
        self.cache_manager = get_cache_manager()
        self.conversation_cache_ttl = 300  # 5分钟
        self.agent_cache_ttl = 3600  # 1小时
        self.permission_cache_ttl = 1800  # 30分钟
    
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
                {"agent_id": aid, "name": agents[aid]["name"]}
                for aid in agent_ids if aid in agents
            ]
            
            # 缓存结果
            if use_cache:
                self._cache_agents(username, result)
            
            return result
            
        except Exception as e:
            logging.error(f"[AGENT] get_user_agents error: {e}")
            return []
    
    def get_conversations(self, username: str, agent_id: str = None, 
                         params: Dict = None, use_cache: bool = True) -> Tuple[Dict, int]:
        """获取对话列表，支持缓存"""
        params = params or {}
        
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

# 全局Dify服务实例
dify_service = DifyService()
