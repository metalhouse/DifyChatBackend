"""
配置管理模块
支持多环境配置，使用环境变量进行配置管理
"""
import os
from typing import Any, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

# 加载环境变量
try:
    from dotenv import load_dotenv
    # 尝试加载不同的环境文件
    env_files = ['.env', '.env.dev', '.env.local']
    loaded = False
    for env_file in env_files:
        if Path(env_file).exists():
            load_dotenv(env_file)
            loaded = True
            break
    if not loaded:
        # 如果没有找到任何环境文件，尝试从上级目录加载
        parent_dir = Path(__file__).parent
        for env_file in env_files:
            env_path = parent_dir / env_file
            if env_path.exists():
                load_dotenv(env_path)
                break
except ImportError:
    pass  # python-dotenv not available


@dataclass
class DatabaseConfig:
    """数据库配置"""
    users_file: str
    agents_file: str
    data_dir: str
    
    def __post_init__(self):
        """确保数据目录存在"""
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)


@dataclass
class BackupConfig:
    """备份配置"""
    enabled: bool = True
    max_backup_files: int = 5
    backup_on_save: bool = True
    cleanup_on_startup: bool = False
    
    
@dataclass 
class DifyConfig:
    """Dify API配置"""
    base_url: str
    default_api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3


@dataclass
class SecurityConfig:
    """安全配置"""
    secret_key: str
    jwt_secret_key: str
    jwt_access_token_expires: int = 3600  # 1小时
    jwt_refresh_token_expires: int = 604800  # 7天
    max_login_attempts: int = 5
    lockout_duration: int = 300  # 5分钟
    password_hash_method: str = 'pbkdf2:sha256'


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = 'INFO'
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_path: str = 'logs/app.log'
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    enable_console: bool = True
    enable_file: bool = True
    enable_syslog: bool = False
    syslog_host: str = 'localhost'
    syslog_port: int = 514


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = '0.0.0.0'
    port: int = 5000
    debug: bool = False
    threaded: bool = True
    cors_enabled: bool = True
    cors_origins: str = '*'


@dataclass
class MariaDBConfig:
    """MariaDB配置"""
    enabled: bool = False
    host: str = 'localhost'
    port: int = 3306
    database: str = 'app_db'
    username: str = 'app_user'
    password: str = 'app_password'
    charset: str = 'utf8mb4'
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600


@dataclass
class RedisConfig:
    """Redis配置（用于缓存和会话管理）"""
    enabled: bool = False
    host: str = 'localhost'
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    decode_responses: bool = True
    socket_timeout: int = 5
    connection_pool_max_connections: int = 10


class Config:
    """主配置类"""
    
    def __init__(self, env: str = None):
        self.env = env or os.getenv('FLASK_ENV', 'development')
        self.app_root = Path(__file__).parent.absolute()
        
        # 初始化各个配置组件
        self.database = self._load_database_config()
        self.backup = self._load_backup_config()
        self.dify = self._load_dify_config()
        self.security = self._load_security_config()
        self.logging = self._load_logging_config()
        self.server = self._load_server_config()
        self.mariadb = self._load_mariadb_config()
        self.redis = self._load_redis_config()
        
        # 为了向后兼容，添加一些属性
        self.MARIADB_ENABLED = self.mariadb.enabled
        
        # 验证配置
        self._validate_config()
    
    def _load_database_config(self) -> DatabaseConfig:
        """加载数据库配置"""
        data_dir = os.getenv('DATA_DIR', str(self.app_root / 'data'))
        return DatabaseConfig(
            users_file=os.getenv('USERS_FILE', str(Path(data_dir) / 'users.json')),
            agents_file=os.getenv('AGENTS_FILE', str(Path(data_dir) / 'agents.json')),
            data_dir=data_dir
        )
    
    def _load_backup_config(self) -> BackupConfig:
        """加载备份配置"""
        return BackupConfig(
            enabled=os.getenv('BACKUP_ENABLED', 'true').lower() == 'true',
            max_backup_files=int(os.getenv('BACKUP_MAX_FILES', '5')),
            backup_on_save=os.getenv('BACKUP_ON_SAVE', 'true').lower() == 'true',
            cleanup_on_startup=os.getenv('BACKUP_CLEANUP_ON_STARTUP', 'false').lower() == 'true'
        )
    
    def _load_dify_config(self) -> DifyConfig:
        """加载Dify API配置"""
        base_url = os.getenv('DIFY_BASE_URL')
        if not base_url:
            raise ValueError("DIFY_BASE_URL环境变量必须设置")
        
        return DifyConfig(
            base_url=base_url,
            default_api_key=os.getenv('DIFY_API_KEY'),
            timeout=int(os.getenv('DIFY_TIMEOUT', '30')),
            max_retries=int(os.getenv('DIFY_MAX_RETRIES', '3'))
        )
    
    def _load_security_config(self) -> SecurityConfig:
        """加载安全配置"""
        secret_key = os.getenv('SECRET_KEY')
        if not secret_key:
            if self.env == 'production':
                raise ValueError("生产环境必须设置SECRET_KEY")
            secret_key = 'dev-secret-key-change-in-production'
        
        jwt_secret = os.getenv('JWT_SECRET_KEY', secret_key)
        
        return SecurityConfig(
            secret_key=secret_key,
            jwt_secret_key=jwt_secret,
            jwt_access_token_expires=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '3600')),
            jwt_refresh_token_expires=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', '604800')),
            max_login_attempts=int(os.getenv('MAX_LOGIN_ATTEMPTS', '5')),
            lockout_duration=int(os.getenv('LOCKOUT_DURATION', '300')),
            password_hash_method=os.getenv('PASSWORD_HASH_METHOD', 'pbkdf2:sha256')
        )
    
    def _load_logging_config(self) -> LoggingConfig:
        """加载日志配置"""
        log_dir = Path(os.getenv('LOG_DIR', str(self.app_root / 'logs')))
        log_dir.mkdir(parents=True, exist_ok=True)
        
        return LoggingConfig(
            level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            format=os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            file_path=str(log_dir / os.getenv('LOG_FILE', 'app.log')),
            max_file_size=int(os.getenv('LOG_MAX_FILE_SIZE', str(10 * 1024 * 1024))),
            backup_count=int(os.getenv('LOG_BACKUP_COUNT', '5')),
            enable_console=os.getenv('LOG_ENABLE_CONSOLE', 'true').lower() == 'true',
            enable_file=os.getenv('LOG_ENABLE_FILE', 'true').lower() == 'true',
            enable_syslog=os.getenv('LOG_ENABLE_SYSLOG', 'false').lower() == 'true',
            syslog_host=os.getenv('LOG_SYSLOG_HOST', 'localhost'),
            syslog_port=int(os.getenv('LOG_SYSLOG_PORT', '514'))
        )
    
    def _load_server_config(self) -> ServerConfig:
        """加载服务器配置"""
        return ServerConfig(
            host=os.getenv('FLASK_HOST', '0.0.0.0'),
            port=int(os.getenv('FLASK_PORT', '5000')),
            debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true',
            threaded=os.getenv('FLASK_THREADED', 'true').lower() == 'true',
            cors_enabled=os.getenv('CORS_ENABLED', 'true').lower() == 'true',
            cors_origins=os.getenv('CORS_ORIGINS', '*')
        )
    
    def _load_mariadb_config(self) -> MariaDBConfig:
        """加载MariaDB配置"""
        return MariaDBConfig(
            enabled=os.getenv('MARIADB_ENABLED', 'false').lower() == 'true',
            host=os.getenv('MARIADB_HOST', 'localhost'),
            port=int(os.getenv('MARIADB_PORT', '3306')),
            database=os.getenv('MARIADB_DATABASE', 'app_db'),
            username=os.getenv('MARIADB_USERNAME', 'app_user'),
            password=os.getenv('MARIADB_PASSWORD', 'app_password'),
            charset=os.getenv('MARIADB_CHARSET', 'utf8mb4'),
            pool_size=int(os.getenv('MARIADB_POOL_SIZE', '5')),
            max_overflow=int(os.getenv('MARIADB_MAX_OVERFLOW', '10')),
            pool_timeout=int(os.getenv('MARIADB_POOL_TIMEOUT', '30')),
            pool_recycle=int(os.getenv('MARIADB_POOL_RECYCLE', '3600'))
        )
    
    def _load_redis_config(self) -> RedisConfig:
        """加载Redis配置"""
        return RedisConfig(
            enabled=os.getenv('REDIS_ENABLED', 'false').lower() == 'true',
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD'),
            decode_responses=os.getenv('REDIS_DECODE_RESPONSES', 'true').lower() == 'true',
            socket_timeout=int(os.getenv('REDIS_SOCKET_TIMEOUT', '5')),
            connection_pool_max_connections=int(os.getenv('REDIS_MAX_CONNECTIONS', '10'))
        )
    
    def _validate_config(self):
        """验证配置有效性"""
        # 验证日志级别
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.logging.level not in valid_log_levels:
            raise ValueError(f"无效的日志级别: {self.logging.level}")
        
        # 验证端口范围
        if not (1 <= self.server.port <= 65535):
            raise ValueError(f"无效的端口号: {self.server.port}")
        
        # 验证Redis端口范围
        if not (1 <= self.redis.port <= 65535):
            raise ValueError(f"无效的Redis端口号: {self.redis.port}")
    
    def get_flask_config(self) -> Dict[str, Any]:
        """获取Flask应用配置字典"""
        return {
            'SECRET_KEY': self.security.secret_key,
            'DEBUG': self.server.debug,
            'TESTING': self.env == 'testing',
            'JSON_AS_ASCII': False,  # 支持中文JSON
            'JSON_SORT_KEYS': False,
            'JSONIFY_PRETTYPRINT_REGULAR': self.server.debug,
        }
    
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.env == 'development'
    
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.env == 'production'
    
    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.env == 'testing'


# 创建配置工厂函数
def create_config(env: str = None) -> Config:
    """创建配置实例的工厂函数"""
    return Config(env)


# 默认配置实例（延迟加载）
_config_instance = None


def get_config() -> Config:
    """获取配置实例（单例模式）"""
    global _config_instance
    if _config_instance is None:
        _config_instance = create_config()
    return _config_instance


def reset_config():
    """重置配置实例（主要用于测试）"""
    global _config_instance
    _config_instance = None


# 便捷访问函数
def get_database_config() -> DatabaseConfig:
    """获取数据库配置"""
    return get_config().database


def get_backup_config() -> BackupConfig:
    """获取备份配置"""
    return get_config().backup


def get_dify_config() -> DifyConfig:
    """获取Dify配置"""
    return get_config().dify


def get_security_config() -> SecurityConfig:
    """获取安全配置"""
    return get_config().security


def get_logging_config() -> LoggingConfig:
    """获取日志配置"""
    return get_config().logging


def get_server_config() -> ServerConfig:
    """获取服务器配置"""
    return get_config().server


def get_redis_config() -> RedisConfig:
    """获取Redis配置"""
    return get_config().redis


def get_mariadb_config() -> MariaDBConfig:
    """获取MariaDB配置"""
    return get_config().mariadb
