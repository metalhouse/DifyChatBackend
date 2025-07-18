"""
智能体功能配置API路由

提供智能体功能配置的CRUD操作接口，包括：
- 查看所有智能体功能配置
- 获取特定智能体功能配置
- 更新智能体功能配置
- 删除智能体功能配置
- 功能检查工具接口
"""

from flask import Blueprint, request
from typing import List, Optional
import logging

from auth.decorators import require_auth, require_permissions
from models.agent_features import (
    AgentFeatureType, 
    agent_feature_manager,
    AgentFeatureUpdateRequest,
    AgentFeatureResponse,
    AgentFeatureListResponse
)
from utils.response_builder import ResponseBuilder, ErrorCode
from middleware.feature_check import (
    get_agent_feature_status,
    check_multiple_features
)

logger = logging.getLogger(__name__)

# 创建蓝图
agent_config_bp = Blueprint('agent_config', __name__)


@agent_config_bp.route('/api/v1/agent-features', methods=['GET'])
@require_auth()
@require_permissions(['admin'])
def list_agent_features():
    """
    获取所有智能体功能配置列表
    
    Query Parameters:
        - page: 页码 (可选)
        - per_page: 每页数量 (可选) 
        - search: 搜索关键词 (可选)
    """
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '').strip()
        
        # 获取所有配置
        all_configs = agent_feature_manager.list_all_agents()
        
        # 搜索过滤
        if search:
            filtered_configs = [
                config for config in all_configs
                if search.lower() in config.agent_name.lower() 
                or search.lower() in config.agent_id.lower()
            ]
        else:
            filtered_configs = all_configs
        
        # 分页处理
        total_count = len(filtered_configs)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_configs = filtered_configs[start:end]
        
        # 转换为响应格式
        agent_responses = [
            AgentFeatureResponse.from_config(config)
            for config in paginated_configs
        ]
        
        # 获取功能统计
        feature_stats = agent_feature_manager.get_feature_statistics()
        
        response_data = AgentFeatureListResponse(
            agents=agent_responses,
            total_count=total_count,
            feature_statistics=feature_stats
        )
        
        from utils.response_builder import PaginationInfo
        
        pagination_info = PaginationInfo(
            page=page,
            page_size=per_page,
            total=total_count,
            total_pages=(total_count + per_page - 1) // per_page
        )
        
        return ResponseBuilder.success(
            data=response_data.dict(),
            message=f"获取智能体功能配置列表成功 (共 {total_count} 个)",
            pagination=pagination_info
        )
        
    except Exception as e:
        logger.error(f"Failed to list agent features: {e}")
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="获取智能体功能配置列表失败"
        )


@agent_config_bp.route('/api/v1/agent-features/<agent_id>', methods=['GET'])
@require_auth()
def get_agent_features(agent_id: str):
    """
    获取特定智能体的功能配置
    
    Path Parameters:
        - agent_id: 智能体ID
    """
    try:
        config = agent_feature_manager.get_agent_config(agent_id)
        
        if not config:
            return ResponseBuilder.error(
                message=f"未找到智能体 {agent_id} 的功能配置",
                error_code=ErrorCode.RESOURCE_NOT_FOUND
            )
        
        response_data = AgentFeatureResponse.from_config(config)
        
        return ResponseBuilder.success(
            data=response_data.dict(),
            message=f"获取智能体 {agent_id} 功能配置成功"
        )
        
    except Exception as e:
        logger.error(f"Failed to get agent features for {agent_id}: {e}")
        return ResponseBuilder.error(
            message="获取智能体功能配置失败",
            error_code=ErrorCode.INTERNAL_ERROR
        )


@agent_config_bp.route('/api/v1/agent-features/<agent_id>', methods=['PUT'])
@require_auth()
@require_permissions(['admin'])
def update_agent_features(agent_id: str):
    """
    更新智能体功能配置
    
    Path Parameters:
        - agent_id: 智能体ID
        
    Request Body:
        - agent_name: 智能体名称 (可选)
        - enabled_features: 启用的功能列表
        - notes: 配置备注 (可选)
    """
    try:
        # 验证请求数据
        data = request.get_json()
        if not data:
            return ResponseBuilder.error(
                message="请求数据不能为空",
                error_code=ErrorCode.INVALID_REQUEST
            )
        
        # 验证请求模型
        try:
            update_request = AgentFeatureUpdateRequest(**data)
        except Exception as e:
            return ResponseBuilder.error(
                message=f"请求数据格式错误: {e}",
                error_code=ErrorCode.INVALID_JSON
            )
        
        # 检查智能体是否存在配置
        existing_config = agent_feature_manager.get_agent_config(agent_id)
        
        if existing_config:
            # 更新现有配置
            updated_config = agent_feature_manager.update_agent_features(
                agent_id=agent_id,
                enabled_features=update_request.enabled_features,
                updated_by=request.current_user.get('username') if hasattr(request, 'current_user') else None
            )
            
            # 更新名称和备注
            if update_request.agent_name:
                updated_config.agent_name = update_request.agent_name
            if update_request.notes is not None:
                updated_config.notes = update_request.notes
                
            agent_feature_manager.set_agent_config(updated_config)
            
        else:
            # 创建新配置
            agent_name = update_request.agent_name or f"智能体_{agent_id}"
            updated_config = agent_feature_manager.create_agent_config(
                agent_id=agent_id,
                agent_name=agent_name,
                enabled_features=update_request.enabled_features,
                updated_by=request.current_user.get('username') if hasattr(request, 'current_user') else None,
                notes=update_request.notes
            )
        
        response_data = AgentFeatureResponse.from_config(updated_config)
        
        logger.info(f"Updated agent features for {agent_id}: {update_request.enabled_features}")
        
        return ResponseBuilder.success(
            data=response_data.dict(),
            message=f"更新智能体 {agent_id} 功能配置成功"
        )
        
    except Exception as e:
        logger.error(f"Failed to update agent features for {agent_id}: {e}")
        return ResponseBuilder.error(
            message="更新智能体功能配置失败",
            error_code=ErrorCode.INTERNAL_ERROR
        )


@agent_config_bp.route('/api/v1/agent-features/<agent_id>', methods=['DELETE'])
@require_auth()
@require_permissions(['admin'])
def delete_agent_features(agent_id: str):
    """
    删除智能体功能配置
    
    Path Parameters:
        - agent_id: 智能体ID
    """
    try:
        success = agent_feature_manager.delete_agent_config(agent_id)
        
        if not success:
            return ResponseBuilder.error(
                message=f"未找到智能体 {agent_id} 的功能配置",
                error_code=ErrorCode.RESOURCE_NOT_FOUND
            )
        
        logger.info(f"Deleted agent features config for {agent_id}")
        
        return ResponseBuilder.success(
            message=f"删除智能体 {agent_id} 功能配置成功"
        )
        
    except Exception as e:
        logger.error(f"Failed to delete agent features for {agent_id}: {e}")
        return ResponseBuilder.error(
            message="删除智能体功能配置失败",
            error_code=ErrorCode.INTERNAL_ERROR
        )


@agent_config_bp.route('/api/v1/agent-features/<agent_id>/status', methods=['GET'])
@require_auth()
def get_agent_feature_status_api(agent_id: str):
    """
    获取智能体功能状态（包含详细的功能检查信息）
    
    Path Parameters:
        - agent_id: 智能体ID
    """
    try:
        status = get_agent_feature_status(agent_id)
        
        return ResponseBuilder.success(
            data=status,
            message=f"获取智能体 {agent_id} 功能状态成功"
        )
        
    except Exception as e:
        logger.error(f"Failed to get agent feature status for {agent_id}: {e}")
        return ResponseBuilder.error(
            message="获取智能体功能状态失败",
            error_code=ErrorCode.INTERNAL_ERROR
        )


@agent_config_bp.route('/api/v1/agent-features/<agent_id>/check', methods=['POST'])
@require_auth()
def check_agent_features_api(agent_id: str):
    """
    批量检查智能体功能支持情况
    
    Path Parameters:
        - agent_id: 智能体ID
        
    Request Body:
        - features: 要检查的功能列表 (可选，默认检查所有功能)
    """
    try:
        data = request.get_json() or {}
        
        # 获取要检查的功能列表
        feature_names = data.get('features', [f.value for f in AgentFeatureType])
        
        # 验证功能名称
        valid_features = []
        invalid_features = []
        
        for feature_name in feature_names:
            try:
                feature = AgentFeatureType(feature_name)
                valid_features.append(feature)
            except ValueError:
                invalid_features.append(feature_name)
        
        if invalid_features:
            return ResponseBuilder.error(
                message=f"无效的功能名称: {', '.join(invalid_features)}",
                error_code=ErrorCode.INVALID_FIELD_VALUE,
                details={
                    "invalid_features": invalid_features,
                    "valid_features": [f.value for f in AgentFeatureType]
                }
            )
        
        # 执行功能检查
        check_results = check_multiple_features(agent_id, valid_features)
        
        return ResponseBuilder.success(
            data=check_results,
            message=f"智能体 {agent_id} 功能检查完成"
        )
        
    except Exception as e:
        logger.error(f"Failed to check agent features for {agent_id}: {e}")
        return ResponseBuilder.error(
            message="智能体功能检查失败",
            error_code=ErrorCode.INTERNAL_ERROR
        )


@agent_config_bp.route('/api/v1/feature-types', methods=['GET'])
@require_auth()
def list_feature_types():
    """
    获取所有可用的功能类型
    """
    try:
        feature_types = [
            {
                "value": feature.value,
                "name": feature.value,
                "description": _get_feature_description(feature)
            }
            for feature in AgentFeatureType
        ]
        
        return ResponseBuilder.success(
            data={
                "feature_types": feature_types,
                "total_count": len(feature_types)
            },
            message="获取功能类型列表成功"
        )
        
    except Exception as e:
        logger.error(f"Failed to list feature types: {e}")
        return ResponseBuilder.error(
            message="获取功能类型列表失败",
            error_code=ErrorCode.INTERNAL_ERROR
        )


@agent_config_bp.route('/api/v1/agent-features/statistics', methods=['GET'])
@require_auth()
@require_permissions(['admin'])
def get_feature_statistics():
    """
    获取功能使用统计信息
    """
    try:
        stats = agent_feature_manager.get_feature_statistics()
        total_agents = len(agent_feature_manager.list_all_agents())
        
        # 计算使用率
        usage_stats = {}
        for feature, count in stats.items():
            usage_rate = (count / total_agents * 100) if total_agents > 0 else 0
            usage_stats[feature] = {
                "enabled_count": count,
                "total_agents": total_agents,
                "usage_rate": round(usage_rate, 2)
            }
        
        return ResponseBuilder.success(
            data={
                "feature_statistics": usage_stats,
                "summary": {
                    "total_agents": total_agents,
                    "total_features": len(AgentFeatureType),
                    "most_used_feature": max(stats, key=stats.get) if stats else None,
                    "least_used_feature": min(stats, key=stats.get) if stats else None
                }
            },
            message="获取功能统计信息成功"
        )
        
    except Exception as e:
        logger.error(f"Failed to get feature statistics: {e}")
        return ResponseBuilder.error(
            message="获取功能统计信息失败",
            error_code=ErrorCode.INTERNAL_ERROR
        )


def _get_feature_description(feature: AgentFeatureType) -> str:
    """获取功能描述"""
    descriptions = {
        AgentFeatureType.SUGGESTED_QUESTIONS: "智能推荐问题功能，为用户提供相关问题建议",
        AgentFeatureType.FILE_UPLOAD: "文件上传功能，支持用户上传各种类型的文件",
        AgentFeatureType.TEXT_TO_AUDIO: "文字转语音功能，将文本内容转换为语音播放",
        AgentFeatureType.AUDIO_TO_TEXT: "语音转文字功能，将语音消息转换为文本",
        AgentFeatureType.MESSAGE_FEEDBACK: "消息反馈功能，用户可以对AI回复进行评价",
        AgentFeatureType.CONVERSATION_RENAME: "对话重命名功能，允许用户自定义对话标题",
        AgentFeatureType.MESSAGE_ANNOTATION: "消息标注功能，支持对对话内容进行标注",
        AgentFeatureType.RETRIEVAL: "知识检索功能，从知识库中检索相关信息",
        AgentFeatureType.CITATION: "引用显示功能，显示AI回复的信息来源"
    }
    return descriptions.get(feature, f"功能: {feature.value}")
