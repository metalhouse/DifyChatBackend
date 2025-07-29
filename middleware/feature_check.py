"""
智能体功能检查中间件
该模块提供功能检查装饰器和中间件，用于在API调用前
检查智能体是否支持特定功能，避免调用不支持的API。
"""

import time
from functools import wraps
from typing import Optional, Callable, List
from flask import request, g
import logging

from models.agent_features import (
    AgentFeatureType,
    agent_feature_manager,
    AgentFeatureManager
)
from utils.response_builder import ResponseBuilder, ErrorCode

logger = logging.getLogger(__name__)

def extract_agent_id_from_request() -> Optional[str]:
    """从请求中提取智能体ID"""
    # 从URL路径参数中提取
    if hasattr(request, 'view_args') and request.view_args:
        agent_id = request.view_args.get('agent_id')
        if agent_id:
            return agent_id

    # 从JSON请求体中提取
    if request.is_json:
        try:
            data = request.get_json()
            if data and 'agent_id' in data:
                return data['agent_id']
        except Exception:
            pass

    # 从查询参数中提取
    agent_id = request.args.get('agent_id')
    if agent_id:
        return agent_id

    # 从表单数据中提取
    if request.form:
        agent_id = request.form.get('agent_id')
        if agent_id:
            return agent_id

    return None

def require_agent_feature(
    feature: AgentFeatureType,
    error_message: Optional[str] = None,
    allow_missing_config: bool = False
):
    """
    装饰器：要求智能体支持特定功能

    Args:
        feature: 需要的功能类型
        error_message: 自定义错误消息
        allow_missing_config: 是否允许没有配置的智能体（默认False）
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 提取智能体ID
            agent_id = extract_agent_id_from_request()

            if not agent_id:
                logger.warning(f"Feature check failed: No agent_id found in request for {feature.value}")
                error_response = ResponseBuilder.error(
                    message="缺少智能体ID参数",
                    error_code=ErrorCode.MISSING_AGENT_ID
                )
                return error_response

            # 检查功能是否启用
            is_enabled = agent_feature_manager.is_feature_enabled(agent_id, feature)

            # 如果功能未启用
            if not is_enabled:
                # 检查是否存在配置
                config = agent_feature_manager.get_agent_config(agent_id)

                if not config and not allow_missing_config:
                    # 没有配置且不允许缺失配置
                    logger.warning(f"Feature check failed: No configuration found for agent {agent_id}")
                    error_response = ResponseBuilder.error(
                        message=f"智能体 {agent_id} 没有功能配置",
                        error_code=ErrorCode.AGENT_CONFIG_NOT_FOUND
                    )
                    return error_response
                elif not config and allow_missing_config:
                    # 没有配置但允许缺失配置，记录并继续
                    logger.info(f"Feature check: No configuration for agent {agent_id}, allowing access to {feature.value}")        
                else:
                    # 有配置但功能未启用
                    default_message = f"智能体不支持 {feature.value} 功能"
                    message = error_message or default_message

                    logger.info(f"Feature check blocked: Agent {agent_id} does not support {feature.value}")

                    error_response = ResponseBuilder.error(
                        message=message,
                        error_code=ErrorCode.FEATURE_NOT_SUPPORTED
                    )
                    return error_response

            # 功能检查通过，将智能体ID保存到上下文
            g.agent_id = agent_id
            g.checked_feature = feature

            logger.debug(f"Feature check passed: Agent {agent_id} supports {feature.value}")
            return func(*args, **kwargs)

        return wrapper
    return decorator

def require_any_agent_feature(
    features: List[AgentFeatureType],
    error_message: Optional[str] = None,
    allow_missing_config: bool = False
):
    """
    装饰器：要求智能体支持任意一个功能

    Args:
        features: 功能类型列表，支持任意一个即可
        error_message: 自定义错误消息
        allow_missing_config: 是否允许没有配置的智能体
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 提取智能体ID
            agent_id = extract_agent_id_from_request()

            if not agent_id:
                logger.warning(f"Feature check failed: No agent_id found in request for features {[f.value for f in features]}")
                error_response = ResponseBuilder.error(
                    message="缺少智能体ID参数",
                    error_code=ErrorCode.MISSING_AGENT_ID
                )
                return error_response

            # 检查是否支持任意一个功能
            supported_features = []
            for feature in features:
                if agent_feature_manager.is_feature_enabled(agent_id, feature):
                    supported_features.append(feature)

            if not supported_features:
                # 检查是否存在配置
                config = agent_feature_manager.get_agent_config(agent_id)

                if not config and not allow_missing_config:
                    logger.warning(f"Feature check failed: No configuration found for agent {agent_id}")
                    error_response = ResponseBuilder.error(
                        message=f"智能体 {agent_id} 没有功能配置",
                        error_code=ErrorCode.AGENT_CONFIG_NOT_FOUND
                    )
                    return error_response
                elif not config and allow_missing_config:
                    logger.info(f"Feature check: No configuration for agent {agent_id}, allowing access")
                else:
                    # 有配置但不支持任何所需功能
                    feature_names = [f.value for f in features]
                    default_message = f"智能体不支持以下任何功能: {', '.join(feature_names)}"
                    message = error_message or default_message

                    logger.info(f"Feature check blocked: Agent {agent_id} does not support any of {feature_names}")

                    error_response = ResponseBuilder.error(
                        message=message,
                        error_code=ErrorCode.FEATURES_NOT_SUPPORTED
                    )
                    return error_response

            # 功能检查通过
            g.agent_id = agent_id
            g.supported_features = supported_features

            logger.debug(f"Feature check passed: Agent {agent_id} supports {[f.value for f in supported_features]}")
            return func(*args, **kwargs)

        return wrapper
    return decorator

class FeatureCheckMiddleware:
    """功能检查中间件类"""

    def __init__(self, app=None, feature_manager: Optional[AgentFeatureManager] = None):
        self.feature_manager = feature_manager or agent_feature_manager
        if app:
            self.init_app(app)

    def init_app(self, app):
        """初始化Flask应用"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self):
        """请求前处理"""
        # 记录请求开始时间（用于性能监控）
        g.feature_check_start_time = time.time()

        # 预提取智能体ID到上下文
        agent_id = extract_agent_id_from_request()
        if agent_id:
            g.agent_id = agent_id

    def after_request(self, response):
        """请求后处理"""
        # 记录功能检查性能指标
        if hasattr(g, 'feature_check_start_time'):
            duration = time.time() - g.feature_check_start_time
            if duration > 0.1:  # 如果检查耗时超过100ms
                logger.warning(f"Feature check took {duration:.3f}s for {request.endpoint}")

        return response

def get_agent_feature_status(agent_id: str) -> dict:
    """获取智能体功能状态（工具函数）"""
    config = agent_feature_manager.get_agent_config(agent_id)
    if not config:
        return {
            "agent_id": agent_id,
            "configured": False,
            "enabled_features": [],
            "available_features": [f.value for f in AgentFeatureType]
        }

    return {
        "agent_id": agent_id,
        "configured": True,
        "enabled_features": [f.value for f in config.enabled_features],
        "disabled_features": [f.value for f in config.disabled_features],
        "available_features": [f.value for f in AgentFeatureType],
        "last_updated": config.last_updated.isoformat(),
        "feature_summary": config.get_feature_summary()
    }

def check_multiple_features(
    agent_id: str,
    features: List[AgentFeatureType]
) -> dict:
    """批量检查多个功能（工具函数）"""
    results = {}
    for feature in features:
        results[feature.value] = agent_feature_manager.is_feature_enabled(agent_id, feature)

    return {
        "agent_id": agent_id,
        "feature_checks": results,
        "supported_count": sum(results.values()),
        "total_count": len(features)
    }

# 预定义的功能检查装饰器（常用功能）
require_suggested_questions = lambda: require_agent_feature(
    AgentFeatureType.SUGGESTED_QUESTIONS,
    "智能体不支持问题建议功能"
)

require_file_upload = lambda: require_agent_feature(
    AgentFeatureType.FILE_UPLOAD,
    "智能体不支持文件上传功能"
)

require_text_to_audio = lambda: require_agent_feature(
    AgentFeatureType.TEXT_TO_AUDIO,
    "智能体不支持文字转语音功能"
)

require_audio_to_text = lambda: require_agent_feature(
    AgentFeatureType.AUDIO_TO_TEXT,
    "智能体不支持语音转文字功能"
)

require_message_feedback = lambda: require_agent_feature(
    AgentFeatureType.MESSAGE_FEEDBACK,
    "智能体不支持消息反馈功能"
)

require_conversation_rename = lambda: require_agent_feature(
    AgentFeatureType.CONVERSATION_RENAME,
    "智能体不支持对话重命名功能"
)
