"""
Redis缓存管理器
提供统一的缓存接口，支持连接池和健康检查
"""
import json
import logging
import pickle
import time
from typing import Any, Dict, List, Optional, Union, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
import hashlib

try:
    import redis
    from redis.connection import ConnectionPool
    from redis.exceptions import ConnectionError, TimeoutError, RedisError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from config import Config


logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """缓存统计信息"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    
    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def total_operations(self) -> int:
        """总操作数"""
        return self.hits + self.misses + self.sets + self.deletes


class CacheKeyGenerator:
    """缓存key生成器"""
    
    @staticmethod
    def conversation_list(user_id: str) -> str:
        """对话列表缓存key"""
        return f"conversations:user:{user_id}"
    
    @staticmethod
    def agent_list(user_id: str) -> str:
        """智能体列表缓存key"""
        return f"agents:user:{user_id}"
    
    @staticmethod
    def user_permissions(user_id: str) -> str:
        """用户权限缓存key"""
        return f"permissions:user:{user_id}"
    
    @staticmethod
    def permission(user_id: str) -> str:
        """用户权限缓存key (简化版本)"""
        return f"permission:{user_id}"
    
    @staticmethod
    def agent_config(agent_id: str) -> str:
        """智能体配置缓存key"""
        return f"agent_config:{agent_id}"
    
    @staticmethod
    def agent_access(user_id: str, agent_id: str) -> str:
        """智能体访问权限缓存key"""
        return f"access:user:{user_id}:agent:{agent_id}"
    
    @staticmethod
    def user_session(user_id: str, device_id: str) -> str:
        """用户会话缓存key"""
        return f"session:user:{user_id}:device:{device_id}"
    
    @staticmethod
    def rate_limit(user_id: str, endpoint: str) -> str:
        """速率限制缓存key"""
        return f"ratelimit:user:{user_id}:endpoint:{endpoint}"
    
    @staticmethod
    def custom(prefix: str, *args) -> str:
        """自定义缓存key"""
        parts = [prefix] + [str(arg) for arg in args]
        return ":".join(parts)
    
    @staticmethod
    def hash_key(key: str) -> str:
        """对长key进行哈希处理"""
        if len(key) > 250:  # Redis key长度限制
            hash_obj = hashlib.md5(key.encode('utf-8'))
            return f"hash:{hash_obj.hexdigest()}"
        return key


class CacheManager:
    """Redis缓存管理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.redis_config = config.redis
        self._client: Optional[redis.Redis] = None
        self._pool: Optional[ConnectionPool] = None
        self._stats = CacheStats()
        self._enabled = self.redis_config.enabled and REDIS_AVAILABLE
        
        if self._enabled:
            self._initialize_redis()
        else:
            if not REDIS_AVAILABLE:
                logger.warning("Redis不可用，缓存功能将被禁用")
            else:
                logger.info("Redis缓存已禁用")
    
    def _initialize_redis(self):
        """初始化Redis连接"""
        try:
            # 创建连接池
            self._pool = ConnectionPool(
                host=self.redis_config.host,
                port=self.redis_config.port,
                db=self.redis_config.db,
                password=self.redis_config.password,
                decode_responses=self.redis_config.decode_responses,
                socket_timeout=self.redis_config.socket_timeout,
                socket_connect_timeout=self.redis_config.socket_timeout,
                max_connections=self.redis_config.connection_pool_max_connections,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # 创建Redis客户端
            self._client = redis.Redis(connection_pool=self._pool)
            
            # 测试连接
            self._client.ping()
            logger.info(f"Redis缓存管理器初始化成功: {self.redis_config.host}:{self.redis_config.port}")
            
        except Exception as e:
            logger.error(f"Redis初始化失败: {e}")
            self._enabled = False
            self._client = None
            self._pool = None
    
    @property
    def enabled(self) -> bool:
        """缓存是否可用"""
        return self._enabled and self._client is not None
    
    @property
    def stats(self) -> CacheStats:
        """获取缓存统计信息"""
        return self._stats
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        if not self._enabled:
            return {
                "status": "disabled",
                "message": "Redis缓存已禁用",
                "enabled": False
            }
        
        try:
            if self._client:
                # 基本连接测试
                start_time = time.time()
                self._client.ping()
                ping_time = (time.time() - start_time) * 1000  # ms
                
                # 获取服务器信息
                info = self._client.info()
                
                return {
                    "status": "healthy",
                    "ping_time_ms": round(ping_time, 2),
                    "redis_version": info.get("redis_version"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory": info.get("used_memory_human"),
                    "stats": {
                        "hits": self._stats.hits,
                        "misses": self._stats.misses,
                        "hit_rate": round(self._stats.hit_rate * 100, 2)
                    },
                    "enabled": True
                }
            else:
                return {
                    "status": "error",
                    "message": "Redis客户端未初始化",
                    "enabled": False
                }
                
        except Exception as e:
            logger.error(f"Redis健康检查失败: {e}")
            return {
                "status": "error",
                "message": str(e),
                "enabled": False
            }
    
    def _serialize(self, value: Any) -> str:
        """序列化数据"""
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False)
        elif isinstance(value, (int, float, bool)):
            return json.dumps(value)
        elif isinstance(value, str):
            return value
        else:
            # 对于复杂对象使用pickle
            return pickle.dumps(value).hex()
    
    def _deserialize(self, value: str, use_pickle: bool = False) -> Any:
        """反序列化数据"""
        if use_pickle:
            try:
                return pickle.loads(bytes.fromhex(value))
            except:
                return value
        
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, nx: bool = False) -> bool:
        """设置缓存"""
        if not self.enabled:
            return False
        
        try:
            # 处理长key
            cache_key = CacheKeyGenerator.hash_key(key)
            
            # 序列化值
            serialized_value = self._serialize(value)
            
            # 设置缓存
            result = self._client.set(cache_key, serialized_value, ex=ttl, nx=nx)
            
            if result:
                self._stats.sets += 1
                logger.debug(f"缓存设置成功: {key[:50]}...")
            
            return bool(result)
            
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"设置缓存失败: {key[:50]}... - {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存"""
        if not self.enabled:
            return default
        
        try:
            # 处理长key
            cache_key = CacheKeyGenerator.hash_key(key)
            
            # 获取缓存
            value = self._client.get(cache_key)
            
            if value is not None:
                self._stats.hits += 1
                # 反序列化
                return self._deserialize(value)
            else:
                self._stats.misses += 1
                return default
                
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"获取缓存失败: {key[:50]}... - {e}")
            return default
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.enabled:
            return False
        
        try:
            # 处理长key
            cache_key = CacheKeyGenerator.hash_key(key)
            
            result = self._client.delete(cache_key)
            
            if result:
                self._stats.deletes += 1
                logger.debug(f"缓存删除成功: {key[:50]}...")
            
            return bool(result)
            
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"删除缓存失败: {key[:50]}... - {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """按模式删除缓存"""
        if not self.enabled:
            return 0
        
        try:
            keys = self._client.keys(pattern)
            if keys:
                deleted = self._client.delete(*keys)
                self._stats.deletes += deleted
                logger.debug(f"按模式删除缓存: {pattern} - 删除了{deleted}个key")
                return deleted
            return 0
            
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"按模式删除缓存失败: {pattern} - {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """检查key是否存在"""
        if not self.enabled:
            return False
        
        try:
            cache_key = CacheKeyGenerator.hash_key(key)
            return bool(self._client.exists(cache_key))
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"检查缓存存在性失败: {key[:50]}... - {e}")
            return False
    
    def expire(self, key: str, ttl: int) -> bool:
        """设置key过期时间"""
        if not self.enabled:
            return False
        
        try:
            cache_key = CacheKeyGenerator.hash_key(key)
            return bool(self._client.expire(cache_key, ttl))
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"设置缓存过期时间失败: {key[:50]}... - {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """获取key剩余生存时间"""
        if not self.enabled:
            return -1
        
        try:
            cache_key = CacheKeyGenerator.hash_key(key)
            return self._client.ttl(cache_key)
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"获取缓存TTL失败: {key[:50]}... - {e}")
            return -1
    
    def mget(self, keys: List[str]) -> List[Any]:
        """批量获取缓存"""
        if not self.enabled:
            return [None] * len(keys)
        
        try:
            # 处理长key
            cache_keys = [CacheKeyGenerator.hash_key(key) for key in keys]
            
            values = self._client.mget(cache_keys)
            result = []
            
            for value in values:
                if value is not None:
                    self._stats.hits += 1
                    result.append(self._deserialize(value))
                else:
                    self._stats.misses += 1
                    result.append(None)
            
            return result
            
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"批量获取缓存失败: {e}")
            return [None] * len(keys)
    
    def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置缓存"""
        if not self.enabled:
            return False
        
        try:
            # 处理长key和序列化
            cache_mapping = {}
            for key, value in mapping.items():
                cache_key = CacheKeyGenerator.hash_key(key)
                cache_mapping[cache_key] = self._serialize(value)
            
            # 批量设置
            pipeline = self._client.pipeline()
            pipeline.mset(cache_mapping)
            
            # 如果指定了TTL，为所有key设置过期时间
            if ttl is not None:
                for cache_key in cache_mapping.keys():
                    pipeline.expire(cache_key, ttl)
            
            results = pipeline.execute()
            
            if results[0]:  # mset的结果
                self._stats.sets += len(mapping)
                logger.debug(f"批量设置缓存成功: {len(mapping)}个key")
                return True
            
            return False
            
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"批量设置缓存失败: {e}")
            return False
    
    def count_keys(self, pattern: str) -> int:
        """统计匹配模式的key数量"""
        if not self.enabled:
            return 0
        
        try:
            keys = self._client.keys(pattern)
            return len(keys)
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"统计key数量失败: {pattern} - {e}")
            return 0
    
    def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        """递增计数器"""
        if not self.enabled:
            return 0
        
        try:
            cache_key = CacheKeyGenerator.hash_key(key)
            
            pipeline = self._client.pipeline()
            pipeline.incr(cache_key, amount)
            
            if ttl is not None:
                pipeline.expire(cache_key, ttl)
            
            results = pipeline.execute()
            return results[0]
            
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"递增计数器失败: {key[:50]}... - {e}")
            return 0
    
    def get_with_lock(self, key: str, lock_timeout: int = 10) -> tuple[Any, bool]:
        """带锁获取缓存"""
        if not self.enabled:
            return None, False
        
        lock_key = f"lock:{key}"
        try:
            # 尝试获取锁
            lock_acquired = self._client.set(lock_key, "1", nx=True, ex=lock_timeout)
            
            if lock_acquired:
                value = self.get(key)
                return value, True
            else:
                return None, False
                
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"带锁获取缓存失败: {key[:50]}... - {e}")
            return None, False
    
    def release_lock(self, key: str) -> bool:
        """释放锁"""
        if not self.enabled:
            return False
        
        lock_key = f"lock:{key}"
        try:
            return bool(self._client.delete(lock_key))
        except Exception as e:
            logger.error(f"释放锁失败: {key[:50]}... - {e}")
            return False
    
    def clear_all(self) -> bool:
        """清空所有缓存（慎用）"""
        if not self.enabled:
            return False
        
        try:
            self._client.flushdb()
            logger.warning("已清空所有缓存")
            return True
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        if not self.enabled:
            return {"enabled": False, "message": "缓存未启用"}
        
        try:
            info = self._client.info()
            return {
                "enabled": True,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "stats": {
                    "hits": self._stats.hits,
                    "misses": self._stats.misses,
                    "sets": self._stats.sets,
                    "deletes": self._stats.deletes,
                    "errors": self._stats.errors,
                    "hit_rate": round(self._stats.hit_rate * 100, 2),
                    "total_operations": self._stats.total_operations
                }
            }
        except Exception as e:
            return {"enabled": False, "error": str(e)}
    
    def close(self):
        """关闭连接"""
        if self._pool:
            self._pool.disconnect()
            self._pool = None
        self._client = None
        logger.info("Redis缓存管理器已关闭")


# 创建全局缓存管理器实例
_cache_manager: Optional[CacheManager] = None


def init_cache_manager(config: Config) -> CacheManager:
    """初始化缓存管理器"""
    global _cache_manager
    _cache_manager = CacheManager(config)
    return _cache_manager


def get_cache_manager() -> Optional[CacheManager]:
    """获取缓存管理器实例"""
    return _cache_manager


# 缓存装饰器
def cached(key_func, ttl: int = 300):
    """缓存装饰器
    
    Args:
        key_func: 生成缓存key的函数
        ttl: 缓存时间（秒）
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            if not cache or not cache.enabled:
                return func(*args, **kwargs)
            
            # 生成缓存key
            cache_key = key_func(*args, **kwargs)
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            
            return result
        return wrapper
    return decorator
