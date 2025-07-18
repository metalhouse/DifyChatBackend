#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量修复feature_check.py中的make_response问题
"""

import re

def fix_make_response_issues():
    file_path = "middleware/feature_check.py"
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除所有的 make_response 导入行
    content = re.sub(r'\s*from flask import make_response\n', '', content)
    
    # 修复所有的 make_response 调用模式
    # 模式: response = make_response(error_response, XXX)\n                return response
    # 替换为: return error_response
    pattern = r'(\s*)response = make_response\(error_response, \d+\)\n\s*return response'
    replacement = r'\1return error_response'
    content = re.sub(pattern, replacement, content)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ make_response问题修复完成")

if __name__ == "__main__":
    fix_make_response_issues()
