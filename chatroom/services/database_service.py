"""
聊天室数据库服务
处理聊天室、消息、成员的数据库操作
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_, text

# 导入模型
from ..models.chatroom_models import Chatroom, ChatroomMember, ChatroomMessage, ChatroomOnlineUser

logger = logging.getLogger(__name__)

class ChatroomDatabaseService:
    """聊天室数据库服务"""
    
    def __init__(self, db_session=None):
        """
        初始化数据库服务
        
        Args:
            db_session: 数据库会话或"mariadb"标记
        """
        # 数据库会话处理
        if db_session == "mariadb":
            # 标记使用MariaDB，实际会话在使用时创建
            self.db = None
            self.use_mariadb = True
            logger.info("📦 数据库服务配置为使用MariaDB数据库")
        else:
            # 使用SQLite或提供的会话
            self.db = db_session
            self.use_mariadb = False
            logger.info("📦 数据库服务配置为使用SQLite数据库")
    
    def _get_db_session(self):
        """获取数据库会话"""
        if self.use_mariadb:
            try:
                from ..mariadb_config import get_mariadb_session
                return get_mariadb_session()
            except ImportError:
                logger.error("❌ 无法导入MariaDB配置")
                return None
        else:
            return self.db
    
    def _execute_with_session(self, operation):
        """使用数据库会话执行操作"""
        if self.use_mariadb:
            try:
                from ..mariadb_config import get_mariadb_session
                with get_mariadb_session() as session:
                    return operation(session)
            except ImportError:
                logger.error("❌ 无法导入MariaDB配置")
                return None
        else:
            if self.db:
                return operation(self.db)
            return None
    
    # ========== 聊天室管理 ==========
    
    def create_chatroom(
        self, 
        name: str, 
        description: str, 
        created_by: str,
        is_public: bool = False,
        max_users: int = 100,
        settings: Dict = None
    ) -> Optional[Chatroom]:
        """
        创建聊天室
        
        Args:
            name: 聊天室名称
            description: 聊天室描述
            created_by: 创建者用户ID
            is_public: 是否公开
            max_users: 最大用户数
            settings: 聊天室设置
            
        Returns:
            Chatroom: 创建的聊天室对象
        """
        def _create_operation(db):
            try:
                # 检查聊天室名称是否已存在
                check_sql = "SELECT id FROM chatrooms WHERE name = :name"
                result = db.execute(text(check_sql), {"name": name})
                if result.fetchone():
                    logger.warning(f"聊天室名称已存在: {name}")
                    return None
                
                # 创建聊天室
                import uuid
                chatroom_id = str(uuid.uuid4())
                
                insert_sql = """
                INSERT INTO chatrooms (id, name, description, is_public, max_users, created_by, created_at, updated_at, status)
                VALUES (:id, :name, :description, :is_public, :max_users, :created_by, NOW(), NOW(), 'active')
                """
                
                db.execute(text(insert_sql), {
                    "id": chatroom_id,
                    "name": name,
                    "description": description,
                    "is_public": 1 if is_public else 0,
                    "max_users": max_users,
                    "created_by": created_by
                })
                
                # 获取创建的聊天室信息
                select_sql = """
                SELECT id, name, description, is_public, max_users, created_by, created_at
                FROM chatrooms WHERE id = :id
                """
                result = db.execute(text(select_sql), {"id": chatroom_id})
                row = result.fetchone()
                
                if row:
                    # 创建一个简单的对象来模拟模型
                    class ChatroomResult:
                        def __init__(self, row):
                            self.id = row[0]
                            self.name = row[1]
                            self.description = row[2]
                            self.is_public = bool(row[3])
                            self.max_users = row[4]
                            self.created_by = row[5]
                            self.created_at = row[6]
                    
                    chatroom = ChatroomResult(row)
                    logger.info(f"创建聊天室成功: {name} (ID: {chatroom.id})")
                    return chatroom
                
                return None
                
            except Exception as e:
                logger.error(f"创建聊天室失败: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        return self._execute_with_session(_create_operation)
    
    def get_chatroom_by_id(self, chatroom_id: str) -> Optional[Chatroom]:
        """
        根据ID获取聊天室
        
        Args:
            chatroom_id: 聊天室ID
            
        Returns:
            Chatroom: 聊天室对象
        """
        def _get_operation(db):
            try:
                # 使用原始SQL查询
                sql = "SELECT id, name, description, is_public, max_users, created_at FROM chatrooms WHERE id = :chatroom_id AND status = 'active'"
                result = db.execute(text(sql), {"chatroom_id": chatroom_id})
                row = result.fetchone()
                
                if row:
                    # 创建一个简单的对象来模拟模型
                    class ChatroomResult:
                        def __init__(self, row):
                            self.id = row[0]
                            self.name = row[1] 
                            self.description = row[2]
                            self.is_public = bool(row[3])
                            self.max_users = row[4]
                            self.created_at = row[5]
                    
                    return ChatroomResult(row)
                return None
                
            except Exception as e:
                logger.error(f"获取聊天室失败: {e}")
                return None
        
        return self._execute_with_session(_get_operation)
    
    def get_user_chatrooms(
        self, 
        user_id: str, 
        include_public: bool = False, 
        page: int = 1, 
        page_size: int = 20
    ) -> Tuple[List[Dict], int]:
        """
        获取用户的聊天室列表
        
        Args:
            user_id: 用户ID
            include_public: 是否包含公开聊天室
            page: 页码
            page_size: 每页大小
            
        Returns:
            Tuple[List[Dict], int]: (聊天室列表, 总数)
        """
        def _get_chatrooms_operation(db):
            try:
                # 初始化参数字典
                params = {}
                
                # 构建基础WHERE条件
                base_where = "WHERE c.status = 'active'"
                
                if include_public:
                    # 包含公开聊天室或用户加入的聊天室
                    base_where += """
                    AND (c.is_public = 1 OR c.id IN (
                        SELECT DISTINCT chatroom_id 
                        FROM chatroom_members 
                        WHERE user_id = :user_id AND status = 'active'
                    ))
                    """
                    params['user_id'] = user_id
                else:
                    # 只返回用户加入的聊天室
                    base_where += """
                    AND c.id IN (
                        SELECT DISTINCT chatroom_id 
                        FROM chatroom_members 
                        WHERE user_id = :user_id AND status = 'active'
                    )
                    """
                    params['user_id'] = user_id
                
                # 获取总数的查询
                count_sql = f"""
                SELECT COUNT(DISTINCT c.id)
                FROM chatrooms c
                {base_where}
                """
                
                total_result = db.execute(text(count_sql), params)
                total = int(total_result.fetchone()[0])  # 确保返回整数
                
                # 获取详细数据的查询
                data_sql = f"""
                SELECT c.id, c.name, c.description, c.is_public, c.max_users, c.created_at,
                       COUNT(m.id) as member_count
                FROM chatrooms c
                LEFT JOIN chatroom_members m ON c.id = m.chatroom_id AND m.status = 'active'
                {base_where}
                GROUP BY c.id, c.name, c.description, c.is_public, c.max_users, c.created_at
                ORDER BY c.created_at DESC
                LIMIT :page_size OFFSET :offset
                """
                
                # 分页参数
                offset = (page - 1) * page_size
                params['page_size'] = page_size
                params['offset'] = offset
                
                result = db.execute(text(data_sql), params)
                rows = result.fetchall()
                
                # 转换为字典格式
                chatrooms = []
                for row in rows:
                    chatrooms.append({
                        "id": row[0],
                        "name": row[1],
                        "description": row[2] or "",
                        "is_public": bool(row[3]),
                        "max_users": row[4],
                        "created_at": row[5].isoformat(),
                        "member_count": row[6]
                    })
                
                return chatrooms, total
                
            except Exception as e:
                logger.error(f"获取用户聊天室列表失败: {e}")
                import traceback
                traceback.print_exc()
                return [], 0
        
        return self._execute_with_session(_get_chatrooms_operation) or ([], 0)
    
    def update_chatroom(
        self,
        chatroom_id: str,
        name: str = None,
        description: str = None,
        is_active: bool = None,
        max_users: int = None,
        settings: Dict = None
    ) -> bool:
        """
        更新聊天室信息
        
        Args:
            chatroom_id: 聊天室ID
            name: 新名称
            description: 新描述
            is_active: 是否活跃
            max_users: 最大用户数
            settings: 设置
            
        Returns:
            bool: 是否成功
        """
        def _update_operation(db):
            try:
                # 构建动态更新SQL
                update_fields = []
                params = {"chatroom_id": chatroom_id}
                
                if name is not None:
                    update_fields.append("name = :name")
                    params["name"] = name
                
                if description is not None:
                    update_fields.append("description = :description")
                    params["description"] = description
                
                if is_active is not None:
                    update_fields.append("status = :status")
                    params["status"] = "active" if is_active else "inactive"
                
                if max_users is not None:
                    update_fields.append("max_users = :max_users")
                    params["max_users"] = max_users
                
                # 始终更新updated_at
                update_fields.append("updated_at = NOW()")
                
                if not update_fields:
                    return False  # 没有要更新的字段
                
                update_sql = f"""
                UPDATE chatrooms 
                SET {', '.join(update_fields)}
                WHERE id = :chatroom_id AND status = 'active'
                """
                
                result = db.execute(text(update_sql), params)
                return result.rowcount > 0
                
            except Exception as e:
                logger.error(f"更新聊天室失败: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        return self._execute_with_session(_update_operation) or False
    
    def delete_chatroom(self, chatroom_id: str) -> bool:
        """
        删除聊天室（软删除）
        
        Args:
            chatroom_id: 聊天室ID
            
        Returns:
            bool: 是否成功
        """
        def _delete_operation(db):
            try:
                # 软删除聊天室 - 使用'disabled'状态而不是'inactive'
                update_sql = """
                UPDATE chatrooms 
                SET status = 'disabled', updated_at = NOW()
                WHERE id = :chatroom_id AND status = 'active'
                """
                
                result = db.execute(text(update_sql), {"chatroom_id": chatroom_id})
                return result.rowcount > 0
                
            except Exception as e:
                logger.error(f"删除聊天室失败: {e}")
                return False
        
        return self._execute_with_session(_delete_operation) or False
    
    # ========== 成员管理 ==========
    
    def add_chatroom_member(
        self, 
        chatroom_id: str, 
        user_id: str, 
        role: str = 'member'
    ) -> bool:
        """
        添加聊天室成员
        
        Args:
            chatroom_id: 聊天室ID
            user_id: 用户ID
            role: 角色 (owner, admin, moderator, member)
            
        Returns:
            bool: 是否成功
        """
        def _add_member_operation(db):
            try:
                # 检查是否已存在
                check_sql = "SELECT id, status FROM chatroom_members WHERE chatroom_id = :chatroom_id AND user_id = :user_id"
                result = db.execute(text(check_sql), {"chatroom_id": chatroom_id, "user_id": user_id})
                existing = result.fetchone()
                
                if existing:
                    # 如果存在但不活跃，重新激活
                    if existing[1] != 'active':
                        update_sql = """
                        UPDATE chatroom_members 
                        SET status = 'active', role = :role, joined_at = NOW() 
                        WHERE chatroom_id = :chatroom_id AND user_id = :user_id
                        """
                        db.execute(text(update_sql), {
                            "chatroom_id": chatroom_id, 
                            "user_id": user_id, 
                            "role": role
                        })
                        return True
                    return False
                
                # 创建新成员
                import uuid
                member_id = str(uuid.uuid4())
                insert_sql = """
                INSERT INTO chatroom_members (id, chatroom_id, user_id, role, joined_at, last_active_at, status)
                VALUES (:id, :chatroom_id, :user_id, :role, NOW(), NOW(), 'active')
                """
                db.execute(text(insert_sql), {
                    "id": member_id,
                    "chatroom_id": chatroom_id,
                    "user_id": user_id,
                    "role": role
                })
                
                return True
                
            except Exception as e:
                logger.error(f"添加聊天室成员失败: {e}")
                return False
        
        return self._execute_with_session(_add_member_operation) or False
    
    def remove_chatroom_member(self, chatroom_id: str, user_id: str) -> bool:
        """
        移除聊天室成员（软删除）
        
        Args:
            chatroom_id: 聊天室ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        def _remove_member_operation(db):
            try:
                # 软删除成员
                update_sql = """
                UPDATE chatroom_members 
                SET status = 'inactive', last_active_at = NOW()
                WHERE chatroom_id = :chatroom_id AND user_id = :user_id
                """
                result = db.execute(text(update_sql), {
                    "chatroom_id": chatroom_id,
                    "user_id": user_id
                })
                
                return result.rowcount > 0
                
            except Exception as e:
                logger.error(f"移除聊天室成员失败: {e}")
                return False
        
        return self._execute_with_session(_remove_member_operation) or False
    
    def get_chatroom_members(self, chatroom_id: str) -> List[Dict]:
        """
        获取聊天室成员列表
        
        Args:
            chatroom_id: 聊天室ID
            
        Returns:
            List[Dict]: 成员列表
        """
        def _get_members_operation(db):
            try:
                sql = """
                SELECT m.user_id, m.role, m.joined_at, m.last_active_at
                FROM chatroom_members m
                WHERE m.chatroom_id = :chatroom_id AND m.status = 'active'
                ORDER BY m.joined_at ASC
                """
                result = db.execute(text(sql), {"chatroom_id": chatroom_id})
                rows = result.fetchall()
                
                members = []
                for row in rows:
                    members.append({
                        "user_id": row[0],
                        "role": row[1],
                        "joined_at": row[2].isoformat() if row[2] else None,
                        "last_active_at": row[3].isoformat() if row[3] else None
                    })
                
                return members
                
            except Exception as e:
                logger.error(f"获取聊天室成员失败: {e}")
                return []
        
        return self._execute_with_session(_get_members_operation) or []
    
    def is_chatroom_member(self, chatroom_id: str, user_id: str) -> bool:
        """
        检查用户是否是聊天室成员
        
        Args:
            chatroom_id: 聊天室ID
            user_id: 用户ID
            
        Returns:
            bool: 是否是成员
        """
        def _check_member_operation(db):
            try:
                sql = """
                SELECT 1 FROM chatroom_members 
                WHERE chatroom_id = :chatroom_id AND user_id = :user_id AND status = 'active'
                LIMIT 1
                """
                result = db.execute(text(sql), {
                    "chatroom_id": chatroom_id, 
                    "user_id": user_id
                })
                
                return result.fetchone() is not None
                
            except Exception as e:
                logger.error(f"检查聊天室成员失败: {e}")
                return False
        
        return self._execute_with_session(_check_member_operation) or False
