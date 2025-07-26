# MariaDB数据库配置和连接管理
import os
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
from pathlib import Path

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
        parent_dir = Path(__file__).parent.parent
        for env_file in env_files:
            env_path = parent_dir / env_file
            if env_path.exists():
                load_dotenv(env_path)
                break
except ImportError:
    pass  # python-dotenv not available

logger = logging.getLogger(__name__)

class MariaDBConfig:
    """MariaDB数据库配置类"""
    
    def __init__(self):
        # 从环境变量读取数据库配置
        self.enabled = os.getenv('MARIADB_ENABLED', 'false').lower() == 'true'
        self.host = os.getenv('MARIADB_HOST', 'localhost')
        self.port = int(os.getenv('MARIADB_PORT', 3306))
        self.database = os.getenv('MARIADB_DATABASE', 'chatroom_db')
        self.username = os.getenv('MARIADB_USERNAME', 'chatroom_user')
        self.password = os.getenv('MARIADB_PASSWORD', 'chatroom_password')
        self.charset = os.getenv('MARIADB_CHARSET', 'utf8mb4')
        
        # 连接池配置
        self.pool_size = int(os.getenv('MARIADB_POOL_SIZE', 10))
        self.max_overflow = int(os.getenv('MARIADB_MAX_OVERFLOW', 20))
        self.pool_timeout = int(os.getenv('MARIADB_POOL_TIMEOUT', 30))
        self.pool_recycle = int(os.getenv('MARIADB_POOL_RECYCLE', 3600))
        
        # SSL配置（如果需要）
        self.ssl_disabled = os.getenv('MARIADB_SSL_DISABLED', 'true').lower() == 'true'
        
    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        from urllib.parse import quote_plus
        
        # 对密码进行URL编码以处理特殊字符
        encoded_password = quote_plus(self.password)
        
        return f"mysql+pymysql://{self.username}:{encoded_password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"
    
    def get_connection_params(self) -> Dict[str, Any]:
        """获取连接参数字典"""
        params = {
            'host': self.host,
            'port': self.port,
            'user': self.username,
            'password': self.password,
            'database': self.database,
            'charset': self.charset,
            'autocommit': False,
            'connect_timeout': 10,
            'read_timeout': 30,
            'write_timeout': 30
        }
        
        if self.ssl_disabled:
            params['ssl_disabled'] = True
            
        return params

class MariaDBManager:
    """MariaDB数据库管理器"""
    
    def __init__(self, config: MariaDBConfig = None):
        self.config = config or MariaDBConfig()
        self.engine = None
        self.Session = None
        
    def initialize_sqlalchemy(self):
        """初始化SQLAlchemy引擎和会话"""
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy.pool import QueuePool
            
            # 创建引擎
            self.engine = create_engine(
                self.config.get_database_url(),
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                pool_pre_ping=True,  # 自动检测断开的连接
                echo=False  # 设置为True可以看到SQL日志
            )
            
            # 创建会话工厂
            self.Session = sessionmaker(bind=self.engine)
            
            logger.info("✅ SQLAlchemy MariaDB引擎初始化成功")
            return True
            
        except ImportError as e:
            logger.error(f"❌ SQLAlchemy未安装: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ SQLAlchemy初始化失败: {e}")
            return False
    
    def initialize_pymysql(self):
        """初始化PyMySQL连接（作为备选方案）"""
        try:
            import pymysql
            
            # 测试连接
            conn = pymysql.connect(**self.config.get_connection_params())
            conn.close()
            
            logger.info("✅ PyMySQL MariaDB连接测试成功")
            return True
            
        except ImportError as e:
            logger.error(f"❌ PyMySQL未安装: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ PyMySQL连接失败: {e}")
            return False
    
    @contextmanager
    def get_session(self):
        """获取数据库会话上下文管理器"""
        if not self.Session:
            if not self.initialize_sqlalchemy():
                raise Exception("无法初始化数据库会话")
        
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @contextmanager
    def get_connection(self):
        """获取原始数据库连接上下文管理器"""
        import pymysql
        
        conn = pymysql.connect(**self.config.get_connection_params())
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            if self.engine:
                # 使用SQLAlchemy测试
                try:
                    from sqlalchemy import text
                    with self.engine.connect() as conn:
                        result = conn.execute(text("SELECT 1"))
                        return result.fetchone()[0] == 1
                except ImportError:
                    # 如果没有SQLAlchemy，降级到PyMySQL
                    return self.initialize_pymysql()
            else:
                # 使用PyMySQL测试
                return self.initialize_pymysql()
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False
    
    def create_database_if_not_exists(self):
        """创建数据库（如果不存在）"""
        try:
            import pymysql
            
            # 连接到MySQL服务器（不指定数据库）
            params = self.config.get_connection_params()
            database = params.pop('database')
            
            conn = pymysql.connect(**params)
            cursor = conn.cursor()
            
            # 创建数据库
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            
            logger.info(f"✅ 数据库 '{database}' 创建成功或已存在")
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建数据库失败: {e}")
            return False
    
    def execute_sql_file(self, sql_file_path: str) -> bool:
        """执行SQL文件"""
        try:
            # 读取SQL文件
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 分割SQL语句（简单分割，可能需要更复杂的解析）
            sql_statements = []
            current_statement = ""
            
            for line in sql_content.split('\n'):
                line = line.strip()
                
                # 跳过注释和空行
                if not line or line.startswith('--'):
                    continue
                
                current_statement += line + '\n'
                
                # 如果行以分号结尾，表示语句结束
                if line.endswith(';'):
                    sql_statements.append(current_statement.strip())
                    current_statement = ""
            
            # 执行SQL语句
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for sql in sql_statements:
                    if sql.strip():
                        try:
                            cursor.execute(sql)
                        except Exception as e:
                            logger.warning(f"SQL语句执行警告: {e}")
                            logger.warning(f"问题SQL: {sql[:100]}...")
                
                logger.info(f"✅ SQL文件 '{sql_file_path}' 执行完成")
                return True
                
        except Exception as e:
            logger.error(f"❌ 执行SQL文件失败: {e}")
            return False
    
    def check_tables_exist(self) -> bool:
        """检查聊天室相关表是否已存在"""
        required_tables = ['chatrooms', 'chatroom_members', 'chatroom_messages', 'chatroom_online_users']
        
        try:
            import pymysql
            connection = pymysql.connect(**self.config.get_connection_params())
            
            with connection.cursor() as cursor:
                existing_tables = []
                for table in required_tables:
                    cursor.execute(f"SHOW TABLES LIKE '{table}'")
                    if cursor.fetchone():
                        existing_tables.append(table)
                
                connection.close()
                
                if len(existing_tables) == len(required_tables):
                    logger.info(f"✅ 所有必需的表已存在: {existing_tables}")
                    return True
                elif len(existing_tables) > 0:
                    logger.warning(f"⚠️ 部分表已存在: {existing_tables}，缺少: {set(required_tables) - set(existing_tables)}")
                    return False
                else:
                    logger.info("ℹ️ 未找到聊天室表，需要初始化")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ 检查表存在性失败: {e}")
            return False

# 全局数据库管理器实例
db_manager = MariaDBManager()

def initialize_mariadb_for_chatroom():
    """为聊天室系统初始化MariaDB"""
    logger.info("🔧 开始初始化MariaDB聊天室数据库...")
    
    # 1. 创建数据库
    if not db_manager.create_database_if_not_exists():
        logger.error("❌ 数据库创建失败")
        return False
    
    # 2. 初始化SQLAlchemy
    if not db_manager.initialize_sqlalchemy():
        logger.error("❌ SQLAlchemy初始化失败")
        return False
    
    # 3. 检查表是否已存在，如果存在则跳过SQL文件执行
    if db_manager.check_tables_exist():
        logger.info("✅ 聊天室数据库表已存在，跳过初始化")
        
        # 仍然需要测试连接
        if not db_manager.test_connection():
            logger.error("❌ 数据库连接测试失败")
            return False
        
        logger.info("✅ MariaDB聊天室数据库检查完成（表已存在）")
        return True
    
    # 4. 表不存在，执行数据库结构SQL文件
    # 首先尝试使用修复版SQL文件
    fixed_sql_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'chatroom_database_fixed.sql')
    simple_sql_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'chatroom_database_simple.sql')
    original_sql_file = os.path.join(os.path.dirname(__file__), 'chatroom_database.sql')
    
    sql_file_to_use = None
    
    # 按优先级选择SQL文件
    if os.path.exists(fixed_sql_file):
        sql_file_to_use = fixed_sql_file
        logger.info(f"🔧 首次初始化，使用修复版SQL文件: {fixed_sql_file}")
    elif os.path.exists(simple_sql_file):
        sql_file_to_use = simple_sql_file
        logger.info(f"🔧 首次初始化，使用简化版SQL文件: {simple_sql_file}")
    elif os.path.exists(original_sql_file):
        sql_file_to_use = original_sql_file
        logger.warning(f"⚠️ 首次初始化，使用原始SQL文件（可能有语法问题）: {original_sql_file}")
    
    if sql_file_to_use:
        if not db_manager.execute_sql_file(sql_file_to_use):
            logger.error("❌ 数据库结构创建失败")
            return False
    else:
        logger.warning("⚠️ 未找到任何SQL文件")
    
    # 5. 测试连接
    if not db_manager.test_connection():
        logger.error("❌ 数据库连接测试失败")
        return False
    
    logger.info("✅ MariaDB聊天室数据库初始化完成")
    return True

def get_mariadb_session():
    """获取MariaDB会话"""
    return db_manager.get_session()

def get_mariadb_connection():
    """获取MariaDB原始连接"""
    return db_manager.get_connection()

# 示例使用方法
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🧪 测试MariaDB连接...")
    
    # 测试初始化
    if initialize_mariadb_for_chatroom():
        print("✅ MariaDB初始化成功!")
        
        # 测试会话
        try:
            with get_mariadb_session() as session:
                result = session.execute("SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name LIKE 'chatroom%'")
                table_count = result.fetchone()[0]
                print(f"📊 发现 {table_count} 个聊天室相关表")
                
        except Exception as e:
            print(f"❌ 会话测试失败: {e}")
    else:
        print("❌ MariaDB初始化失败!")
