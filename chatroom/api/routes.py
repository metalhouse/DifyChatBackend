"""
聊天室HTTP API路由
提供聊天室管理的REST API接口
"""
from flask import Blueprint, request, jsonify, g
from datetime import datetime
import logging

# 导入服务
from ..services.permissions import require_chatroom_permission, get_current_user
from ..services.database_service import ChatroomDatabaseService
from ..services.online_user_manager import online_user_manager

logger = logging.getLogger(__name__)

# 创建蓝图
chatroom_bp = Blueprint('chatroom', __name__, url_prefix='/api/v1/chatroom')

def get_db_service():
    """获取数据库服务实例"""
    try:
        # 直接使用MariaDB会话
        from ..services.database_service import ChatroomDatabaseService
        return ChatroomDatabaseService("mariadb")
    except Exception as e:
        logger.error(f"无法创建数据库服务: {e}")
        return None

def standard_response(success=True, data=None, message="", error_code=None, status_code=200):
    """标准化API响应格式"""
    response = {
        "success": success,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response["data"] = data
    
    if error_code:
        response["error_code"] = error_code
    
    return jsonify(response), status_code

# ========== 管理员API ==========

@chatroom_bp.route('/create', methods=['POST'])
@require_chatroom_permission('chatroom_admin')
def create_chatroom():
    """创建聊天室 - 仅管理员"""
    try:
        data = request.get_json()
        if not data:
            return standard_response(
                success=False,
                message="请求数据为空",
                error_code="EMPTY_REQUEST_DATA",
                status_code=400
            )
        
        # 验证必要字段
        name = data.get('name')
        if not name or not name.strip():
            return standard_response(
                success=False,
                message="聊天室名称不能为空",
                error_code="CHATROOM_NAME_REQUIRED",
                status_code=400
            )
        
        description = data.get('description', '')
        is_public = data.get('is_public', False)
        max_users = data.get('max_users', 100)
        settings = data.get('settings', {})
        
        # 获取当前用户
        current_user = get_current_user()
        if not current_user:
            return standard_response(
                success=False,
                message="用户认证失败",
                error_code="USER_AUTHENTICATION_FAILED",
                status_code=401
            )
        
        # 创建聊天室
        db_service = get_db_service()
        if not db_service:
            return standard_response(
                success=False,
                message="数据库服务不可用",
                error_code="DATABASE_SERVICE_UNAVAILABLE",
                status_code=500
            )
        
        chatroom = db_service.create_chatroom(
            name=name.strip(),
            description=description,
            created_by=current_user['id'],
            is_public=is_public,
            max_users=max_users,
            settings=settings
        )
        
        if not chatroom:
            return standard_response(
                success=False,
                message="创建聊天室失败，可能名称已存在",
                error_code="CHATROOM_CREATION_FAILED",
                status_code=400
            )
        
        # 将创建者添加为管理员成员
        db_service.add_chatroom_member(chatroom.id, current_user['id'], 'admin')
        
        logger.info(f"创建聊天室成功: {name} (ID: {chatroom.id})")
        
        return standard_response(
            success=True,
            data={
                "id": chatroom.id,
                "name": chatroom.name,
                "description": chatroom.description,
                "is_public": chatroom.is_public,
                "max_users": chatroom.max_users,
                "created_at": chatroom.created_at.isoformat()
            },
            message="创建聊天室成功"
        )
        
    except Exception as e:
        logger.error(f"创建聊天室失败: {e}")
        return standard_response(
            success=False,
            message="创建聊天室时发生错误",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

@chatroom_bp.route('/admin/list', methods=['GET'])
@require_chatroom_permission('chatroom_admin')
def get_all_chatrooms():
    """获取所有聊天室 - 仅管理员"""
    try:
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)  # 最大100条
        
        db_service = get_db_service()
        if not db_service:
            return standard_response(
                success=False,
                message="数据库服务不可用",
                error_code="DATABASE_SERVICE_UNAVAILABLE",
                status_code=500
            )
        
        # 这里需要实现管理员获取所有聊天室的方法
        # 简化处理，使用普通用户的方法
        current_user = get_current_user()
        chatrooms, total = db_service.get_user_chatrooms(
            current_user['id'], 
            include_public=True, 
            page=page, 
            page_size=limit
        )
        
        return standard_response(
            success=True,
            data={
                "chatrooms": chatrooms,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": (total + limit - 1) // limit
                }
            },
            message="获取聊天室列表成功"
        )
        
    except ValueError:
        return standard_response(
            success=False,
            message="分页参数格式错误",
            error_code="INVALID_PAGINATION_PARAMS",
            status_code=400
        )
    except Exception as e:
        logger.error(f"获取聊天室列表失败: {e}")
        return standard_response(
            success=False,
            message="获取聊天室列表时发生错误",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

@chatroom_bp.route('/<chatroom_id>', methods=['PUT'])
@require_chatroom_permission('chatroom_admin')
def update_chatroom(chatroom_id):
    """更新聊天室信息"""
    try:
        data = request.get_json()
        if not data:
            return standard_response(
                success=False,
                message="请求数据为空",
                error_code="EMPTY_REQUEST_DATA",
                status_code=400
            )
        
        db_service = get_db_service()
        if not db_service:
            return standard_response(
                success=False,
                message="数据库服务不可用",
                error_code="DATABASE_SERVICE_UNAVAILABLE",
                status_code=500
            )
        
        # 检查聊天室是否存在
        chatroom = db_service.get_chatroom_by_id(chatroom_id)
        if not chatroom:
            return standard_response(
                success=False,
                message="聊天室不存在",
                error_code="CHATROOM_NOT_FOUND",
                status_code=404
            )
        
        # 更新聊天室
        success = db_service.update_chatroom(
            chatroom_id=chatroom_id,
            name=data.get('name'),
            description=data.get('description'),
            is_active=data.get('is_active'),
            max_users=data.get('max_users'),
            settings=data.get('settings')
        )
        
        if not success:
            return standard_response(
                success=False,
                message="更新聊天室失败",
                error_code="CHATROOM_UPDATE_FAILED",
                status_code=500
            )
        
        return standard_response(
            success=True,
            message="更新聊天室成功"
        )
        
    except Exception as e:
        logger.error(f"更新聊天室失败: {e}")
        return standard_response(
            success=False,
            message="更新聊天室时发生错误",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

@chatroom_bp.route('/<chatroom_id>', methods=['DELETE'])
@require_chatroom_permission('chatroom_admin')
def delete_chatroom(chatroom_id):
    """删除聊天室"""
    try:
        db_service = get_db_service()
        if not db_service:
            return standard_response(
                success=False,
                message="数据库服务不可用",
                error_code="DATABASE_SERVICE_UNAVAILABLE",
                status_code=500
            )
        
        # 检查聊天室是否存在
        chatroom = db_service.get_chatroom_by_id(chatroom_id)
        if not chatroom:
            return standard_response(
                success=False,
                message="聊天室不存在",
                error_code="CHATROOM_NOT_FOUND",
                status_code=404
            )
        
        # 删除聊天室
        success = db_service.delete_chatroom(chatroom_id)
        
        if not success:
            return standard_response(
                success=False,
                message="删除聊天室失败",
                error_code="CHATROOM_DELETE_FAILED",
                status_code=500
            )
        
        logger.info(f"删除聊天室成功: {chatroom_id}")
        
        return standard_response(
            success=True,
            message="删除聊天室成功"
        )
        
    except Exception as e:
        logger.error(f"删除聊天室失败: {e}")
        return standard_response(
            success=False,
            message="删除聊天室时发生错误",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

@chatroom_bp.route('/<chatroom_id>/members', methods=['POST'])
@require_chatroom_permission('chatroom_admin')
def add_members(chatroom_id):
    """添加用户到聊天室"""
    try:
        data = request.get_json()
        if not data:
            return standard_response(
                success=False,
                message="请求数据为空",
                error_code="EMPTY_REQUEST_DATA",
                status_code=400
            )
        
        user_ids = data.get('user_ids', [])
        role = data.get('role', 'member')
        
        if not user_ids or not isinstance(user_ids, list):
            return standard_response(
                success=False,
                message="用户ID列表不能为空",
                error_code="USER_IDS_REQUIRED",
                status_code=400
            )
        
        db_service = get_db_service()
        if not db_service:
            return standard_response(
                success=False,
                message="数据库服务不可用",
                error_code="DATABASE_SERVICE_UNAVAILABLE",
                status_code=500
            )
        
        # 检查聊天室是否存在
        chatroom = db_service.get_chatroom_by_id(chatroom_id)
        if not chatroom:
            return standard_response(
                success=False,
                message="聊天室不存在",
                error_code="CHATROOM_NOT_FOUND",
                status_code=404
            )
        
        # 添加成员
        added_members = []
        failed_members = []
        
        for user_id in user_ids:
            if db_service.add_chatroom_member(chatroom_id, user_id, role):
                added_members.append(user_id)
            else:
                failed_members.append(user_id)
        
        return standard_response(
            success=True,
            data={
                "added_members": added_members,
                "failed_members": failed_members,
                "total_added": len(added_members)
            },
            message=f"成功添加 {len(added_members)} 个成员"
        )
        
    except Exception as e:
        logger.error(f"添加聊天室成员失败: {e}")
        return standard_response(
            success=False,
            message="添加聊天室成员时发生错误",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

@chatroom_bp.route('/<chatroom_id>/members/<user_id>', methods=['DELETE'])
@require_chatroom_permission('chatroom_admin')
def remove_member(chatroom_id, user_id):
    """移除聊天室成员"""
    try:
        db_service = get_db_service()
        if not db_service:
            return standard_response(
                success=False,
                message="数据库服务不可用",
                error_code="DATABASE_SERVICE_UNAVAILABLE",
                status_code=500
            )
        
        # 检查聊天室是否存在
        chatroom = db_service.get_chatroom_by_id(chatroom_id)
        if not chatroom:
            return standard_response(
                success=False,
                message="聊天室不存在",
                error_code="CHATROOM_NOT_FOUND",
                status_code=404
            )
        
        # 移除成员
        success = db_service.remove_chatroom_member(chatroom_id, user_id)
        
        if not success:
            return standard_response(
                success=False,
                message="移除成员失败",
                error_code="REMOVE_MEMBER_FAILED",
                status_code=500
            )
        
        return standard_response(
            success=True,
            message="移除成员成功"
        )
        
    except Exception as e:
        logger.error(f"移除聊天室成员失败: {e}")
        return standard_response(
            success=False,
            message="移除聊天室成员时发生错误",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

# ========== 用户API ==========

@chatroom_bp.route('/my-chatrooms', methods=['GET'])
@require_chatroom_permission('chatroom_access')
def get_my_chatrooms():
    """获取用户可访问的聊天室"""
    try:
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)
        
        current_user = get_current_user()
        if not current_user:
            return standard_response(
                success=False,
                message="用户认证失败",
                error_code="USER_AUTHENTICATION_FAILED",
                status_code=401
            )
        
        db_service = get_db_service()
        if not db_service:
            return standard_response(
                success=False,
                message="数据库服务不可用",
                error_code="DATABASE_SERVICE_UNAVAILABLE",
                status_code=500
            )
        
        chatrooms, total = db_service.get_user_chatrooms(
            current_user['id'], 
            include_public=True, 
            page=page, 
            page_size=limit
        )
        
        return standard_response(
            success=True,
            data={
                "chatrooms": chatrooms,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "total_pages": (total + limit - 1) // limit
                }
            },
            message="获取聊天室列表成功"
        )
        
    except ValueError:
        return standard_response(
            success=False,
            message="分页参数格式错误",
            error_code="INVALID_PAGINATION_PARAMS",
            status_code=400
        )
    except Exception as e:
        logger.error(f"获取用户聊天室失败: {e}")
        return standard_response(
            success=False,
            message="获取聊天室列表时发生错误",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

@chatroom_bp.route('/<chatroom_id>', methods=['GET'])
@require_chatroom_permission('chatroom_access')
def get_chatroom_detail(chatroom_id):
    """获取聊天室详情"""
    try:
        current_user = get_current_user()
        if not current_user:
            return standard_response(
                success=False,
                message="用户认证失败",
                error_code="USER_AUTHENTICATION_FAILED",
                status_code=401
            )
        
        db_service = get_db_service()
        if not db_service:
            return standard_response(
                success=False,
                message="数据库服务不可用",
                error_code="DATABASE_SERVICE_UNAVAILABLE",
                status_code=500
            )
        
        # 获取聊天室信息
        chatroom = db_service.get_chatroom_by_id(chatroom_id)
        if not chatroom:
            return standard_response(
                success=False,
                message="聊天室不存在",
                error_code="CHATROOM_NOT_FOUND",
                status_code=404
            )
        
        # 检查访问权限
        if not chatroom.is_public and not db_service.is_chatroom_member(chatroom_id, current_user['id']):
            return standard_response(
                success=False,
                message="没有访问权限",
                error_code="ACCESS_DENIED",
                status_code=403
            )
        
        # 获取成员列表
        members = db_service.get_chatroom_members(chatroom_id)
        
        # 获取在线用户 - 暂时使用空列表，因为online_user_manager.get_online_users是异步的
        online_users = []  # TODO: 实现同步版本的get_online_users
        
        return standard_response(
            success=True,
            data={
                "id": chatroom.id,
                "name": chatroom.name,
                "description": chatroom.description,
                "is_public": chatroom.is_public,
                "max_users": chatroom.max_users,
                "created_at": chatroom.created_at.isoformat(),
                "members": members,
                "online_users": online_users,
                "member_count": len(members),
                "online_count": len(online_users)
            },
            message="获取聊天室详情成功"
        )
        
    except Exception as e:
        logger.error(f"获取聊天室详情失败: {e}")
        return standard_response(
            success=False,
            message="获取聊天室详情时发生错误",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

@chatroom_bp.route('/<chatroom_id>/messages', methods=['GET'])
@require_chatroom_permission('chatroom_access')
def get_chatroom_messages(chatroom_id):
    """获取聊天室消息历史"""
    try:
        limit = min(int(request.args.get('limit', 50)), 100)
        before_message_id = request.args.get('before')
        
        current_user = get_current_user()
        if not current_user:
            return standard_response(
                success=False,
                message="用户认证失败",
                error_code="USER_AUTHENTICATION_FAILED",
                status_code=401
            )
        
        db_service = get_db_service()
        if not db_service:
            return standard_response(
                success=False,
                message="数据库服务不可用",
                error_code="DATABASE_SERVICE_UNAVAILABLE",
                status_code=500
            )
        
        # 检查访问权限
        chatroom = db_service.get_chatroom_by_id(chatroom_id)
        if not chatroom:
            return standard_response(
                success=False,
                message="聊天室不存在",
                error_code="CHATROOM_NOT_FOUND",
                status_code=404
            )
        
        if not chatroom.is_public and not db_service.is_chatroom_member(chatroom_id, current_user['id']):
            return standard_response(
                success=False,
                message="没有访问权限",
                error_code="ACCESS_DENIED",
                status_code=403
            )
        
        # 获取消息
        messages = db_service.get_chatroom_messages(chatroom_id, limit, before_message_id)
        
        # 转换消息格式
        from ..services.message_crypto import MessageCrypto
        formatted_messages = [
            MessageCrypto.prepare_encrypted_message_for_client(msg)
            for msg in messages
        ]
        
        return standard_response(
            success=True,
            data={
                "messages": formatted_messages,
                "has_more": len(messages) == limit
            },
            message="获取消息历史成功"
        )
        
    except ValueError:
        return standard_response(
            success=False,
            message="参数格式错误",
            error_code="INVALID_PARAMS",
            status_code=400
        )
    except Exception as e:
        logger.error(f"获取聊天室消息失败: {e}")
        return standard_response(
            success=False,
            message="获取消息历史时发生错误",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

@chatroom_bp.route('/<chatroom_id>/members', methods=['GET'])
@require_chatroom_permission('chatroom_access')
def get_chatroom_members(chatroom_id):
    """获取聊天室成员列表"""
    try:
        current_user = get_current_user()
        if not current_user:
            return standard_response(
                success=False,
                message="用户认证失败",
                error_code="USER_AUTHENTICATION_FAILED",
                status_code=401
            )
        
        db_service = get_db_service()
        if not db_service:
            return standard_response(
                success=False,
                message="数据库服务不可用",
                error_code="DATABASE_SERVICE_UNAVAILABLE",
                status_code=500
            )
        
        # 检查访问权限
        chatroom = db_service.get_chatroom_by_id(chatroom_id)
        if not chatroom:
            return standard_response(
                success=False,
                message="聊天室不存在",
                error_code="CHATROOM_NOT_FOUND",
                status_code=404
            )
        
        if not chatroom.is_public and not db_service.is_chatroom_member(chatroom_id, current_user['id']):
            return standard_response(
                success=False,
                message="没有访问权限",
                error_code="ACCESS_DENIED",
                status_code=403
            )
        
        # 获取成员列表
        members = db_service.get_chatroom_members(chatroom_id)
        online_users = online_user_manager.get_online_users(chatroom_id)
        
        return standard_response(
            success=True,
            data={
                "members": members,
                "online_users": online_users,
                "member_count": len(members),
                "online_count": len(online_users)
            },
            message="获取成员列表成功"
        )
        
    except Exception as e:
        logger.error(f"获取聊天室成员失败: {e}")
        return standard_response(
            success=False,
            message="获取成员列表时发生错误",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )

# ========== 统计API ==========

@chatroom_bp.route('/stats', methods=['GET'])
@require_chatroom_permission('chatroom_admin')
def get_chatroom_stats():
    """获取聊天室统计信息"""
    try:
        chatroom_id = request.args.get('chatroom_id')
        
        db_service = get_db_service()
        if not db_service:
            return standard_response(
                success=False,
                message="数据库服务不可用",
                error_code="DATABASE_SERVICE_UNAVAILABLE",
                status_code=500
            )
        
        # 获取统计信息
        stats = db_service.get_chatroom_statistics(chatroom_id)
        
        # 获取在线用户统计
        online_stats = online_user_manager.get_chatroom_stats(chatroom_id)
        
        return standard_response(
            success=True,
            data={
                "database_stats": stats,
                "online_stats": online_stats
            },
            message="获取统计信息成功"
        )
        
    except Exception as e:
        logger.error(f"获取聊天室统计失败: {e}")
        return standard_response(
            success=False,
            message="获取统计信息时发生错误",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500
        )
