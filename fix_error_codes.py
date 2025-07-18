#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量修复中间件中的错误码引用
"""

import re

def fix_error_codes():
    file_path = "middleware/feature_check.py"
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 定义替换映射
    replacements = {
        'error_code="MISSING_AGENT_ID"': 'error_code=ErrorCode.MISSING_AGENT_ID',
        'error_code="AGENT_CONFIG_NOT_FOUND"': 'error_code=ErrorCode.AGENT_CONFIG_NOT_FOUND',
        'error_code="FEATURE_NOT_SUPPORTED"': 'error_code=ErrorCode.FEATURE_NOT_SUPPORTED',
        'error_code="FEATURES_NOT_SUPPORTED"': 'error_code=ErrorCode.FEATURES_NOT_SUPPORTED'
    }
    
    # 应用替换
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 错误码修复完成")

if __name__ == "__main__":
    fix_error_codes()
