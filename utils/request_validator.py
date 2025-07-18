"""
请求验证系统

该模块提供统一的请求数据验证功能，包括：
1. Pydantic模型定义和验证
2. 自定义验证器
3. 错误信息处理
4. 验证装饰器
"""

from typing import Any, Dict, List, Optional, Union, Callable
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError
from pydantic_core import ErrorDetails
from functools import wraps
import re
from datetime import datetime
import uuid

from utils.response_builder import ResponseBuilder, ErrorCode


# ==================== 基础验证模型 ====================

class BaseRequestModel(BaseModel):
    """所有请求模型的基类"""
    
    model_config = {
        "validate_assignment": True,
        "use_enum_values": True,
        "extra": "forbid"  # 禁止额外字段
    }


class PaginationRequest(BaseModel):
    """分页请求模型"""
    
    page: int = Field(default=1, ge=1, le=10000, description="页码，从1开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量，最大100")
    
    @field_validator('page')
    @classmethod
    def validate_page(cls, v):
        if v < 1:
            raise ValueError('页码必须大于0')
        if v > 10000:
            raise ValueError('页码不能超过10000')
        return v
    
    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v):
        if v < 1:
            raise ValueError('每页数量必须大于0')
        if v > 100:
            raise ValueError('每页数量不能超过100')
        return v


# ==================== 用户相关模型 ====================

class UserLoginRequest(BaseRequestModel):
    """用户登录请求"""
    
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    remember_me: bool = Field(default=False, description="记住登录状态")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        # 用户名只能包含字母、数字、下划线和连字符
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('用户名只能包含字母、数字、下划线和连字符')
        return v.lower()  # 转换为小写
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        # 密码强度验证
        if len(v) < 6:
            raise ValueError('密码长度至少6位')
        if len(v) > 128:
            raise ValueError('密码长度不能超过128位')
        # 可以添加更多密码强度规则
        return v


class UserCreateRequest(BaseRequestModel):
    """创建用户请求"""
    
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=8, max_length=128, description="密码")
    email: Optional[str] = Field(None, max_length=255, description="邮箱地址")
    display_name: Optional[str] = Field(None, max_length=100, description="显示名称")
    is_active: bool = Field(default=True, description="是否激活")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('用户名只能包含字母、数字、下划线和连字符')
        return v.lower()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        # 密码必须包含字母和数字
        if not re.search(r'[a-zA-Z]', v) or not re.search(r'\d', v):
            raise ValueError('密码必须包含字母和数字')
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v is None:
            return v
        # 简单的邮箱格式验证
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('邮箱格式不正确')
        return v.lower()


class UserUpdateRequest(BaseRequestModel):
    """更新用户请求"""
    
    display_name: Optional[str] = Field(None, max_length=100, description="显示名称")
    email: Optional[str] = Field(None, max_length=255, description="邮箱地址")
    is_active: Optional[bool] = Field(None, description="是否激活")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v is None:
            return v
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('邮箱格式不正确')
        return v.lower()


class ChangePasswordRequest(BaseRequestModel):
    """修改密码请求"""
    
    old_password: str = Field(..., min_length=1, max_length=128, description="原密码")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="确认新密码")
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('新密码长度至少8位')
        if not re.search(r'[a-zA-Z]', v) or not re.search(r'\d', v):
            raise ValueError('新密码必须包含字母和数字')
        return v
    
    @model_validator(mode='after')
    def validate_passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError('新密码和确认密码不匹配')
        return self


# ==================== 智能体相关模型 ====================

class AgentCreateRequest(BaseRequestModel):
    """创建智能体请求"""
    
    name: str = Field(..., min_length=1, max_length=100, description="智能体名称")
    description: Optional[str] = Field(None, max_length=500, description="智能体描述")
    dify_agent_id: str = Field(..., min_length=1, max_length=100, description="Dify平台智能体ID")
    is_active: bool = Field(default=True, description="是否激活")
    owner_only: bool = Field(default=False, description="是否仅所有者可用")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        # 去除首尾空白字符
        v = v.strip()
        if not v:
            raise ValueError('智能体名称不能为空')
        return v
    
    @field_validator('dify_agent_id')
    @classmethod
    def validate_dify_agent_id(cls, v):
        # Dify智能体ID格式验证
        if not re.match(r'^[a-zA-Z0-9-_]+$', v):
            raise ValueError('Dify智能体ID格式不正确')
        return v


class AgentUpdateRequest(BaseRequestModel):
    """更新智能体请求"""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="智能体名称")
    description: Optional[str] = Field(None, max_length=500, description="智能体描述")
    is_active: Optional[bool] = Field(None, description="是否激活")
    owner_only: Optional[bool] = Field(None, description="是否仅所有者可用")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('智能体名称不能为空')
        return v


# ==================== 对话相关模型 ====================

class ChatMessageRequest(BaseRequestModel):
    """发送聊天消息请求"""
    
    agent_id: str = Field(..., description="智能体ID")
    message: str = Field(..., min_length=1, max_length=4000, description="消息内容")
    conversation_id: Optional[str] = Field(None, description="对话ID，新对话时为空")
    stream: bool = Field(default=False, description="是否流式响应")
    inputs: Optional[Dict[str, Any]] = Field(default=None, description="输入参数")
    files: Optional[List[str]] = Field(default=None, description="文件列表")
    auto_generate_name: Optional[bool] = Field(default=None, description="是否自动生成对话名称")


class MessageFeedbackRequest(BaseRequestModel):
    """消息反馈请求"""
    
    rating: str = Field(..., description="反馈评分: like, dislike, null")
    content: Optional[str] = Field(None, max_length=500, description="反馈内容")
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        allowed_ratings = ['like', 'dislike', 'null']
        if v not in allowed_ratings:
            raise ValueError(f'评分必须是: {", ".join(allowed_ratings)}')
        return v


class ConversationDeleteRequest(BaseRequestModel):
    """删除对话请求"""
    pass  # 只需要用户认证，无需额外参数


class ConversationRenameRequest(BaseRequestModel):
    """对话重命名请求"""
    
    name: Optional[str] = Field(None, max_length=200, description="对话名称")
    auto_generate: bool = Field(default=False, description="是否自动生成名称")
    
    @model_validator(mode='after')
    def validate_name_or_auto_generate(self):
        if not self.auto_generate and (not self.name or not self.name.strip()):
            raise ValueError('必须提供名称或启用自动生成')
        return self


class AudioToTextRequest(BaseRequestModel):
    """语音转文字请求"""
    
    file: str = Field(..., description="音频文件路径或ID")
    
    @field_validator('file')
    @classmethod
    def validate_file(cls, v):
        if not v.strip():
            raise ValueError('音频文件不能为空')
        return v.strip()


class TextToAudioRequest(BaseRequestModel):
    """文字转语音请求"""
    
    message_id: Optional[str] = Field(None, description="消息ID")
    text: Optional[str] = Field(None, max_length=1000, description="要转换的文字")
    
    @model_validator(mode='after')
    def validate_text_or_message_id(self):
        if not self.message_id and not self.text:
            raise ValueError('必须提供消息ID或文字内容')
        return self
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('文字内容不能为空')
            if len(v) > 1000:
                raise ValueError('文字长度不能超过1000字符')
        return v


class ConversationCreateRequest(BaseRequestModel):
    """创建对话请求"""
    
    agent_id: str = Field(..., description="智能体ID")
    first_message: str = Field(..., min_length=1, max_length=4000, description="第一条消息")
    inputs: Optional[Dict[str, Any]] = Field(default=None, description="输入参数")
    title: Optional[str] = Field(None, max_length=200, description="对话标题")
    
    @field_validator('agent_id')
    @classmethod
    def validate_agent_id(cls, v):
        if not v.strip():
            raise ValueError('智能体ID不能为空')
        return v.strip()
    
    @field_validator('first_message')
    @classmethod
    def validate_first_message(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('第一条消息不能为空')
        if len(v) > 4000:
            raise ValueError('消息长度不能超过4000字符')
        return v
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class ConversationUpdateRequest(BaseRequestModel):
    """更新对话请求"""
    
    title: Optional[str] = Field(None, max_length=200, description="对话标题")
    is_archived: Optional[bool] = Field(None, description="是否归档")
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('对话标题不能为空')
        return v


class ConversationListRequest(PaginationRequest):
    """对话列表请求"""
    
    agent_id: Optional[str] = Field(None, description="智能体ID筛选")
    is_archived: Optional[bool] = Field(None, description="是否归档筛选")
    search: Optional[str] = Field(None, max_length=100, description="搜索关键词")
    
    @field_validator('search')
    @classmethod
    def validate_search(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


# ==================== 管理相关模型 ====================

class AgentPermissionRequest(BaseRequestModel):
    """智能体权限管理请求"""
    
    user_id: str = Field(..., description="用户ID")
    agent_id: str = Field(..., description="智能体ID")
    granted: bool = Field(..., description="是否授予权限")
    
    @field_validator('user_id', 'agent_id')
    @classmethod
    def validate_ids(cls, v):
        if not v.strip():
            raise ValueError('ID不能为空')
        return v.strip()


class SystemConfigRequest(BaseRequestModel):
    """系统配置更新请求"""
    
    dify_api_url: Optional[str] = Field(None, description="Dify API URL")
    dify_api_key: Optional[str] = Field(None, description="Dify API Key")
    cache_ttl: Optional[int] = Field(None, ge=60, le=86400, description="缓存TTL(秒)")
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=1000, description="每分钟请求限制")
    
    @field_validator('dify_api_url')
    @classmethod
    def validate_dify_api_url(cls, v):
        if v is not None:
            v = v.strip()
            if v and not v.startswith(('http://', 'https://')):
                raise ValueError('Dify API URL必须以http://或https://开头')
        return v
    
    @field_validator('dify_api_key')
    @classmethod
    def validate_dify_api_key(cls, v):
        if v is not None:
            v = v.strip()
            if v and len(v) < 10:
                raise ValueError('Dify API Key长度至少10位')
        return v


# ==================== 验证错误处理 ====================

class ValidationError(Exception):
    """自定义验证异常"""
    
    def __init__(self, errors: Dict[str, List[str]]):
        self.errors = errors
        super().__init__(str(errors))


def format_pydantic_errors(errors: List[ErrorDetails]) -> Dict[str, List[str]]:
    """格式化Pydantic验证错误"""
    formatted_errors = {}
    
    for error in errors:
        # 获取字段路径
        field_path = '.'.join(str(loc) for loc in error['loc'])
        if not field_path:
            field_path = 'root'
        
        # 获取错误消息
        msg = error['msg']
        error_type = error['type']
        
        # 根据错误类型自定义消息
        if error_type == 'missing':
            msg = '该字段为必填项'
        elif error_type == 'string_type':
            msg = '该字段必须是字符串类型'
        elif error_type == 'int_type':
            msg = '该字段必须是整数类型'
        elif error_type == 'bool_type':
            msg = '该字段必须是布尔类型'
        elif error_type == 'string_too_short':
            ctx = error.get('ctx', {})
            min_length = ctx.get('min_length', '未知')
            msg = f'字段长度至少{min_length}位'
        elif error_type == 'string_too_long':
            ctx = error.get('ctx', {})
            max_length = ctx.get('max_length', '未知')
            msg = f'字段长度不能超过{max_length}位'
        elif error_type == 'greater_than_equal':
            ctx = error.get('ctx', {})
            limit = ctx.get('ge', '未知')
            msg = f'数值必须大于等于{limit}'
        elif error_type == 'less_than_equal':
            ctx = error.get('ctx', {})
            limit = ctx.get('le', '未知')
            msg = f'数值必须小于等于{limit}'
        
        # 添加到错误字典
        if field_path not in formatted_errors:
            formatted_errors[field_path] = []
        formatted_errors[field_path].append(msg)
    
    return formatted_errors


# ==================== 验证装饰器 ====================

def validate_request(model_class: type) -> Callable:
    """
    请求验证装饰器
    
    用法:
    @validate_request(UserCreateRequest)
    def create_user(request: UserCreateRequest):
        # 处理已验证的请求
        pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request, g
            
            try:
                # 获取请求数据
                if request.method in ['POST', 'PUT', 'PATCH']:
                    data = request.get_json() or {}
                else:
                    data = request.args.to_dict()
                
                # 验证数据
                validated_data = model_class(**data)
                
                # 将验证后的数据添加到g对象中
                g.validated_data = validated_data
                
                # 调用原函数
                return func(*args, **kwargs)
                
            except PydanticValidationError as e:
                # 格式化验证错误
                validation_errors = format_pydantic_errors(e.errors())
                
                # 返回验证失败响应
                response = ResponseBuilder.validation_error(
                    validation_errors,
                    message="请求数据验证失败"
                )
                return response.to_dict(), 422
                
            except Exception as e:
                # 其他异常
                response = ResponseBuilder.error(
                    ErrorCode.INTERNAL_SERVER_ERROR,
                    message=f"请求处理失败: {str(e)}"
                )
                return response.to_dict(), 500
        
        return wrapper
    return decorator


def validate_json_request(model_class: type) -> Callable:
    """
    JSON请求验证装饰器（仅用于POST/PUT/PATCH）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request, g
            
            try:
                # 检查Content-Type
                if not request.is_json:
                    response = ResponseBuilder.error(
                        ErrorCode.JSON_FORMAT_ERROR,
                        message="请求必须使用application/json格式"
                    )
                    return response.to_dict(), 400
                
                # 获取JSON数据
                data = request.get_json()
                if data is None:
                    response = ResponseBuilder.error(
                        ErrorCode.JSON_FORMAT_ERROR,
                        message="请求体不能为空"
                    )
                    return response.to_dict(), 400
                
                # 验证数据
                validated_data = model_class(**data)
                g.validated_data = validated_data
                
                return func(*args, **kwargs)
                
            except PydanticValidationError as e:
                validation_errors = format_pydantic_errors(e.errors())
                response = ResponseBuilder.validation_error(
                    validation_errors,
                    message="请求数据验证失败"
                )
                return response.to_dict(), 422
                
            except Exception as e:
                response = ResponseBuilder.error(
                    ErrorCode.INTERNAL_SERVER_ERROR,
                    message=f"请求处理失败: {str(e)}"
                )
                return response.to_dict(), 500
        
        return wrapper
    return decorator


def validate_query_params(model_class: type) -> Callable:
    """
    查询参数验证装饰器（仅用于GET请求）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request, g
            
            try:
                # 获取查询参数
                data = {}
                for key, value in request.args.items():
                    # 处理多值参数
                    if key in data:
                        if not isinstance(data[key], list):
                            data[key] = [data[key]]
                        data[key].append(value)
                    else:
                        data[key] = value
                
                # 验证数据
                validated_data = model_class(**data)
                g.validated_data = validated_data
                
                return func(*args, **kwargs)
                
            except PydanticValidationError as e:
                validation_errors = format_pydantic_errors(e.errors())
                response = ResponseBuilder.validation_error(
                    validation_errors,
                    message="查询参数验证失败"
                )
                return response.to_dict(), 422
                
            except Exception as e:
                response = ResponseBuilder.error(
                    ErrorCode.INTERNAL_SERVER_ERROR,
                    message=f"请求处理失败: {str(e)}"
                )
                return response.to_dict(), 500
        
        return wrapper
    return decorator


# ==================== 自定义验证器 ====================

class CustomValidators:
    """自定义验证器集合"""
    
    @staticmethod
    def validate_uuid(value: str) -> str:
        """验证UUID格式"""
        try:
            uuid.UUID(value)
            return value
        except ValueError:
            raise ValueError('UUID格式不正确')
    
    @staticmethod
    def validate_username(value: str) -> str:
        """验证用户名格式"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise ValueError('用户名只能包含字母、数字、下划线和连字符')
        return value.lower()
    
    @staticmethod
    def validate_password_strength(value: str) -> str:
        """验证密码强度"""
        if len(value) < 8:
            raise ValueError('密码长度至少8位')
        
        checks = [
            (r'[a-z]', '密码必须包含小写字母'),
            (r'[A-Z]', '密码必须包含大写字母'),
            (r'\d', '密码必须包含数字'),
            (r'[!@#$%^&*(),.?":{}|<>]', '密码必须包含特殊字符')
        ]
        
        failed_checks = []
        for pattern, message in checks:
            if not re.search(pattern, value):
                failed_checks.append(message)
        
        if len(failed_checks) > 2:  # 允许最多2个检查失败
            raise ValueError('密码强度不足: ' + ', '.join(failed_checks))
        
        return value
    
    @staticmethod
    def validate_url(value: str) -> str:
        """验证URL格式"""
        url_pattern = r'^https?://.+$'
        if not re.match(url_pattern, value):
            raise ValueError('URL格式不正确')
        return value
    
    @staticmethod
    def validate_email_domain(value: str, allowed_domains: List[str] = None) -> str:
        """验证邮箱域名"""
        if allowed_domains:
            domain = value.split('@')[1]
            if domain not in allowed_domains:
                raise ValueError(f'邮箱域名必须是: {", ".join(allowed_domains)}')
        return value


# ==================== 验证辅助函数 ====================

def validate_and_convert(data: dict, model_class: type) -> BaseRequestModel:
    """
    验证并转换数据
    
    Args:
        data: 原始数据字典
        model_class: Pydantic模型类
        
    Returns:
        验证后的模型实例
        
    Raises:
        ValidationError: 验证失败时抛出
    """
    try:
        return model_class(**data)
    except PydanticValidationError as e:
        validation_errors = format_pydantic_errors(e.errors())
        raise ValidationError(validation_errors)


def get_validation_error_response(validation_error: ValidationError, 
                                request_id: str = None) -> dict:
    """
    获取验证错误响应
    
    Args:
        validation_error: 验证错误对象
        request_id: 请求ID
        
    Returns:
        标准错误响应字典
    """
    response = ResponseBuilder.validation_error(
        validation_error.errors,
        message="请求数据验证失败",
        request_id=request_id
    )
    return response.to_dict()


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 示例：验证用户登录请求
    login_data = {
        "username": "test_user",
        "password": "password123",
        "remember_me": True
    }
    
    try:
        validated_login = UserLoginRequest(**login_data)
        print("登录验证成功:", validated_login.model_dump())
    except PydanticValidationError as e:
        errors = format_pydantic_errors(e.errors())
        print("登录验证失败:", errors)
    
    # 示例：验证创建智能体请求
    agent_data = {
        "name": "GPT助手",
        "description": "基于GPT的智能对话助手",
        "dify_agent_id": "gpt-assistant-001",
        "is_active": True,
        "owner_only": False
    }
    
    try:
        validated_agent = AgentCreateRequest(**agent_data)
        print("智能体验证成功:", validated_agent.model_dump())
    except PydanticValidationError as e:
        errors = format_pydantic_errors(e.errors())
        print("智能体验证失败:", errors)
