"""
修复agent_config_routes.py中的ResponseBuilder.error调用
"""

import re

def fix_response_builder_errors():
    file_path = "api/agent_config_routes.py"
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 定义替换映射
    replacements = [
        # 将字符串错误码替换为ErrorCode枚举
        (r'error_code="AGENT_CONFIG_NOT_FOUND"', 'error_code=ErrorCode.RESOURCE_NOT_FOUND'),
        (r'error_code="INVALID_REQUEST_DATA"', 'error_code=ErrorCode.INVALID_REQUEST'),
        (r'error_code="INVALID_REQUEST_FORMAT"', 'error_code=ErrorCode.INVALID_JSON'),
        (r'error_code="UPDATE_AGENT_FEATURES_FAILED"', 'error_code=ErrorCode.INTERNAL_ERROR'),
        (r'error_code="DELETE_AGENT_FEATURES_FAILED"', 'error_code=ErrorCode.INTERNAL_ERROR'),
        (r'error_code="GET_AGENT_FEATURES_FAILED"', 'error_code=ErrorCode.INTERNAL_ERROR'),
        (r'error_code="GET_AGENT_STATUS_FAILED"', 'error_code=ErrorCode.INTERNAL_ERROR'),
        (r'error_code="CHECK_AGENT_FEATURES_FAILED"', 'error_code=ErrorCode.INTERNAL_ERROR'),
        (r'error_code="INVALID_FEATURE_NAMES"', 'error_code=ErrorCode.INVALID_FIELD_VALUE'),
        (r'error_code="LIST_FEATURE_TYPES_FAILED"', 'error_code=ErrorCode.INTERNAL_ERROR'),
        (r'error_code="GET_STATISTICS_FAILED"', 'error_code=ErrorCode.INTERNAL_ERROR'),
        
        # 移除status_code参数
        (r',\s*status_code=\d+', ''),
    ]
    
    # 应用替换
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ ResponseBuilder.error调用已修复")

if __name__ == "__main__":
    fix_response_builder_errors()
