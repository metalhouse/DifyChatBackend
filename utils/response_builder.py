"""
API响应构建器模块
提供统一的API响应格式和错误码系统
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid
import json
from flask import jsonify


class ErrorCode(Enum):
    """统一错误码枚举"""
    
    # 成功
    SUCCESS = (0, "操作成功")
    
    # 客户端错误 (4xx)
    INVALID_REQUEST = (4000, "请求参数错误")
    INVALID_JSON = (4001, "JSON格式错误")
    MISSING_PARAMETER = (4002, "缺少必需参数")
    INVALID_FIELD_VALUE = (4003, "字段值无效")
    INVALID_FIELD_TYPE = (4004, "字段类型错误")
    METHOD_NOT_ALLOWED = (4005, "请求方法不被允许")
    
    # 认证错误 (401x)
    AUTHENTICATION_REQUIRED = (4010, "需要身份验证")
    AUTHENTICATION_FAILED = (4011, "身份验证失败")
    INVALID_CREDENTIALS = (4012, "用户名或密码错误")
    INVALID_TOKEN = (4013, "无效的访问令牌")
    TOKEN_EXPIRED = (4014, "访问令牌已过期")
    TOKEN_BLACKLISTED = (4015, "访问令牌已被撤销")
    
    # 权限错误 (403x)
    ACCESS_DENIED = (4030, "访问被拒绝")
    PERMISSION_REQUIRED = (4031, "需要特定权限")
    AGENT_ACCESS_DENIED = (4032, "智能体访问被拒绝")
    
    # 资源错误 (404x)
    RESOURCE_NOT_FOUND = (4040, "资源不存在")
    USER_NOT_FOUND = (4041, "用户不存在")
    AGENT_NOT_FOUND = (4042, "智能体不存在")
    CONVERSATION_NOT_FOUND = (4043, "对话不存在")
    
    # 请求冲突 (409x)
    CONFLICT = (4090, "请求冲突")
    USER_ALREADY_EXISTS = (4091, "用户已存在")
    RESOURCE_LOCKED = (4092, "资源被锁定")
    ACCOUNT_LOCKED = (4093, "账户已被锁定")
    
    # 业务逻辑错误 (422x)
    VALIDATION_ERROR = (4220, "数据验证失败")
    BUSINESS_RULE_VIOLATION = (4221, "违反业务规则")
    WEAK_PASSWORD = (4222, "密码强度不足")
    
    # 限流错误 (429x)
    RATE_LIMITED = (4290, "请求过于频繁")
    
    # 服务器错误 (5xx)
    INTERNAL_ERROR = (5000, "服务器内部错误")
    SERVICE_UNAVAILABLE = (5003, "服务暂时不可用")
    DATABASE_ERROR = (5010, "数据库错误")
    CACHE_ERROR = (5020, "缓存服务错误")
    EXTERNAL_SERVICE_ERROR = (5030, "外部服务错误")
    
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


@dataclass
class ApiResponse:
    """统一API响应格式"""
    
    success: bool
    code: int
    message: str
    data: Any = None
    error_code: str = None
    request_id: str = None
    timestamp: int = None
    
    def __post_init__(self):
        """自动生成请求ID和时间戳"""
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = int(datetime.utcnow().timestamp())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "success": self.success,
            "message": self.message,
            "request_id": self.request_id,
            "timestamp": self.timestamp
        }
        
        # 根据success状态添加不同字段
        if self.success:
            if self.data is not None:
                result["data"] = self.data
        else:
            if self.error_code:
                result["error_code"] = self.error_code
            if self.data is not None:
                result["data"] = self.data
        
        return result
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass  
class PaginationInfo:
    """分页信息"""
    
    page: int = 1
    page_size: int = 20
    total: int = 0
    total_pages: int = 0
    has_next: bool = False
    has_prev: bool = False
    
    def __post_init__(self):
        """自动计算分页信息"""
        if self.total > 0:
            self.total_pages = (self.total + self.page_size - 1) // self.page_size
            self.has_next = self.page < self.total_pages
            self.has_prev = self.page > 1


@dataclass
class PaginatedResponse:
    """分页响应数据"""
    
    items: List[Any]
    pagination: PaginationInfo
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "items": self.items,
            "pagination": asdict(self.pagination)
        }


class ResponseBuilder:
    """API响应构建器"""
    
    @staticmethod
    def success(data: Any = None, message: str = "操作成功", request_id: str = None, pagination: 'PaginationInfo' = None) -> Tuple[Any, int]:
        """构建成功响应"""
        response = ApiResponse(
            success=True,
            code=ErrorCode.SUCCESS.code,
            message=message,
            data=data,
            request_id=request_id
        )
        
        # 如果有分页信息，添加到响应中
        response_dict = response.to_dict()
        if pagination:
            response_dict['pagination'] = asdict(pagination)
        
        return jsonify(response_dict), 200
    
    @staticmethod
    def error(error_code: ErrorCode, message: str = None, data: Any = None, request_id: str = None) -> Tuple[Any, int]:
        """构建错误响应"""
        response = ApiResponse(
            success=False,
            error_code=error_code.name,
            code=error_code.code,
            message=message or error_code.message,
            data=data,
            request_id=request_id
        )
        
        # 根据错误码确定HTTP状态码
        http_status = ResponseBuilder._get_http_status_from_error_code(error_code)
        
        return jsonify(response.to_dict()), http_status
    
    @staticmethod
    def _get_http_status_from_error_code(error_code: ErrorCode) -> int:
        """根据错误码获取HTTP状态码"""
        code_range = error_code.code // 1000
        
        if code_range == 4:  # 4xxx错误
            if error_code.code >= 4010 and error_code.code < 4020:
                return 401  # 认证错误
            elif error_code.code >= 4030 and error_code.code < 4040:
                return 403  # 权限错误
            elif error_code.code >= 4040 and error_code.code < 4050:
                return 404  # 资源不存在
            elif error_code.code >= 4090 and error_code.code < 4100:
                return 409  # 冲突
            elif error_code.code >= 4220 and error_code.code < 4230:
                return 422  # 不可处理的实体
            elif error_code.code >= 4290 and error_code.code < 4300:
                return 429  # 速率限制
            else:
                return 400  # 默认客户端错误
        elif code_range == 5:  # 5xxx错误
            return 500  # 服务器错误
        else:
            return 400  # 默认错误
    
    @staticmethod
    def paginated(items: List[Any], page: int, page_size: int, total: int, 
                  message: str = "获取数据成功", request_id: str = None) -> Tuple[Any, int]:
        """构建分页响应"""
        pagination = PaginationInfo(
            page=page,
            page_size=page_size,
            total=total
        )
        
        return ResponseBuilder.success(
            data=items,
            message=message,
            request_id=request_id,
            pagination=pagination
        )
    
    @staticmethod
    def validation_error(errors: Dict[str, List[str]], request_id: str = None) -> Tuple[Any, int]:
        """构建验证错误响应"""
        return ResponseBuilder.error(
            ErrorCode.VALIDATION_ERROR,
            message="数据验证失败",
            data=errors,
            request_id=request_id
        )
    
    @staticmethod
    def unauthorized(message: str = None, request_id: str = None) -> Tuple[Any, int]:
        """构建未授权响应"""
        return ResponseBuilder.error(
            ErrorCode.AUTHENTICATION_REQUIRED,
            message=message,
            request_id=request_id
        )
    
    @staticmethod
    def forbidden(message: str = None, request_id: str = None) -> Tuple[Any, int]:
        """构建权限不足响应"""
        return ResponseBuilder.error(
            ErrorCode.ACCESS_DENIED,
            message=message,
            request_id=request_id
        )
    
    @staticmethod
    def not_found(resource: str = "资源", request_id: str = None) -> Tuple[Any, int]:
        """构建资源不存在响应"""
        return ResponseBuilder.error(
            ErrorCode.RESOURCE_NOT_FOUND,
            message=f"{resource}不存在",
            request_id=request_id
        )
    
    @staticmethod
    def internal_error(message: str = None, request_id: str = None) -> Tuple[Any, int]:
        """构建服务器内部错误响应"""
        return ResponseBuilder.error(
            ErrorCode.INTERNAL_ERROR,
            message=message,
            request_id=request_id
        )
    
    @staticmethod
    def rate_limit_exceeded(message: str = None, request_id: str = None) -> Tuple[Any, int]:
        """构建速率限制响应"""
        return ResponseBuilder.error(
            ErrorCode.RATE_LIMITED,
            message=message or "请求过于频繁，请稍后再试",
            request_id=request_id
        )


def create_response_middleware():
    """创建响应中间件，用于Flask应用"""
    
    def response_middleware(response_data):
        """响应中间件函数"""
        # 如果已经是ApiResponse格式，直接返回
        if isinstance(response_data, ApiResponse):
            return response_data.to_dict()
        
        # 如果是字典且包含success字段，认为已经格式化
        if isinstance(response_data, dict) and 'success' in response_data:
            return response_data
        
        # 否则包装为成功响应
        return ResponseBuilder.success(data=response_data).to_dict()
    
    return response_middleware


# 请求ID管理
class RequestIdManager:
    """请求ID管理器"""
    
    @staticmethod
    def generate_request_id() -> str:
        """生成新的请求ID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def get_request_id_from_header(headers: dict) -> Optional[str]:
        """从请求头获取请求ID"""
        return headers.get('X-Request-ID') or headers.get('x-request-id')
    
    @staticmethod
    def ensure_request_id(headers: dict) -> str:
        """确保有请求ID，如果没有则生成新的"""
        request_id = RequestIdManager.get_request_id_from_header(headers)
        if not request_id:
            request_id = RequestIdManager.generate_request_id()
        return request_id


# 错误处理助手
class ErrorHandler:
    """错误处理助手类"""
    
    @staticmethod
    def handle_exception(e: Exception, request_id: str = None) -> ApiResponse:
        """处理异常并返回适当的错误响应"""
        
        # JWT相关错误
        if "token" in str(e).lower():
            if "expired" in str(e).lower():
                return ResponseBuilder.error(ErrorCode.TOKEN_EXPIRED, request_id=request_id)
            elif "invalid" in str(e).lower():
                return ResponseBuilder.error(ErrorCode.INVALID_TOKEN, request_id=request_id)
            else:
                return ResponseBuilder.unauthorized(request_id=request_id)
        
        # 权限相关错误
        elif "permission" in str(e).lower() or "forbidden" in str(e).lower():
            return ResponseBuilder.forbidden(request_id=request_id)
        
        # 资源不存在错误
        elif "not found" in str(e).lower() or "does not exist" in str(e).lower():
            return ResponseBuilder.not_found(request_id=request_id)
        
        # 验证错误
        elif "validation" in str(e).lower():
            return ResponseBuilder.error(ErrorCode.VALIDATION_ERROR, message=str(e), request_id=request_id)
        
        # 默认为服务器内部错误
        else:
            return ResponseBuilder.internal_error(
                message="服务器内部错误，请稍后重试",
                request_id=request_id
            )


# 便捷函数
def success_response(data: Any = None, message: str = "操作成功", request_id: str = None) -> Dict[str, Any]:
    """快速创建成功响应"""
    return ResponseBuilder.success(data, message, request_id).to_dict()


def error_response(error_code: ErrorCode, message: str = None, request_id: str = None) -> Dict[str, Any]:
    """快速创建错误响应"""
    return ResponseBuilder.error(error_code, message, request_id=request_id).to_dict()


def paginated_response(items: List[Any], page: int, page_size: int, total: int, 
                      message: str = "获取数据成功", request_id: str = None) -> Dict[str, Any]:
    """快速创建分页响应"""
    return ResponseBuilder.paginated(items, page, page_size, total, message, request_id).to_dict()
