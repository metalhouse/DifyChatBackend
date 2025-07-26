#!/usr/bin/env python3
"""
聊天室系统健康检查脚本
用于快速诊断系统状态和常见问题
"""

import requests
import json
import sys
import os
from datetime import datetime

def print_status(message, success=True):
    """打印带颜色的状态信息"""
    icon = "✅" if success else "❌"
    print(f"{icon} {message}")

def check_app_service():
    """检查应用服务状态"""
    try:
        response = requests.get("http://127.0.0.1:5000/health", timeout=5)
        if response.status_code == 200:
            print_status("应用服务: 正常运行")
            return True
        else:
            print_status(f"应用服务: HTTP {response.status_code}", False)
            return False
    except requests.exceptions.ConnectionError:
        print_status("应用服务: 连接被拒绝 (服务可能未启动)", False)
        return False
    except requests.exceptions.Timeout:
        print_status("应用服务: 连接超时", False)
        return False
    except Exception as e:
        print_status(f"应用服务: {e}", False)
        return False

def check_database():
    """检查数据库连接"""
    try:
        from chatroom.mariadb_config import initialize_mariadb_for_chatroom, db_manager
        
        # 检查初始化
        if initialize_mariadb_for_chatroom():
            print_status("数据库初始化: 成功")
        else:
            print_status("数据库初始化: 失败", False)
            return False
            
        # 检查连接
        if db_manager.test_connection():
            print_status("数据库连接: 正常")
        else:
            print_status("数据库连接: 失败", False)
            return False
            
        # 检查表结构
        if db_manager.check_tables_exist():
            print_status("数据库表: 完整")
            return True
        else:
            print_status("数据库表: 缺失或不完整", False)
            return False
            
    except ImportError as e:
        print_status(f"数据库模块: 导入失败 - {e}", False)
        return False
    except Exception as e:
        print_status(f"数据库检查: {e}", False)
        return False

def check_authentication():
    """检查用户认证功能"""
    try:
        login_data = {
            "username": "metalhouse",
            "password": "Iwhyi3589"
        }
        
        response = requests.post(
            "http://127.0.0.1:5000/api/v1/auth/login",
            json=login_data,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and "tokens" in data.get("data", {}):
                print_status("用户认证: 正常")
                return True, data["data"]["tokens"]["access_token"]
            else:
                print_status("用户认证: 响应格式异常", False)
                return False, None
        else:
            print_status(f"用户认证: HTTP {response.status_code}", False)
            try:
                error_data = response.json()
                print(f"   错误详情: {error_data.get('message', 'Unknown error')}")
            except:
                pass
            return False, None
            
    except Exception as e:
        print_status(f"认证检查: {e}", False)
        return False, None

def check_chatroom_api(token):
    """检查聊天室API功能"""
    if not token:
        print_status("聊天室API: 跳过 (无认证令牌)", False)
        return False
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # 测试创建聊天室
        create_data = {
            "name": f"健康检查室_{datetime.now().strftime('%H%M%S')}",
            "description": "系统健康检查自动创建",
            "is_public": False,
            "max_users": 10
        }
        
        response = requests.post(
            "http://127.0.0.1:5000/api/v1/chatroom/create",
            json=create_data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            print_status("聊天室创建: 正常")
            
            # 获取创建的聊天室ID
            data = response.json()
            chatroom_id = data.get("data", {}).get("id")
            
            if chatroom_id:
                # 测试获取聊天室详情
                detail_response = requests.get(
                    f"http://127.0.0.1:5000/api/v1/chatroom/{chatroom_id}",
                    headers=headers,
                    timeout=5
                )
                
                if detail_response.status_code == 200:
                    print_status("聊天室查询: 正常")
                    
                    # 清理测试数据
                    requests.delete(
                        f"http://127.0.0.1:5000/api/v1/chatroom/{chatroom_id}",
                        headers=headers,
                        timeout=5
                    )
                    print_status("测试数据清理: 完成")
                    
                    return True
                else:
                    print_status("聊天室查询: 失败", False)
                    return False
            else:
                print_status("聊天室创建: 响应缺少ID", False)
                return False
        else:
            print_status(f"聊天室创建: HTTP {response.status_code}", False)
            try:
                error_data = response.json()
                print(f"   错误详情: {error_data.get('message', 'Unknown error')}")
            except:
                pass
            return False
            
    except Exception as e:
        print_status(f"聊天室API: {e}", False)
        return False

def check_environment():
    """检查环境配置"""
    print("\n🔧 环境配置检查:")
    
    # 首先加载环境变量（与应用保持一致）
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        
        env_files = ['.env', '.env.dev', '.env.local']
        loaded = False
        for env_file in env_files:
            if Path(env_file).exists():
                load_dotenv(env_file)
                loaded = True
                print(f"   🔄 已加载环境文件: {env_file}")
                break
        
        if not loaded:
            print("   ⚠️ 未找到环境文件")
    except ImportError:
        print("   ⚠️ python-dotenv 不可用")
    
    required_vars = [
        "MARIADB_ENABLED",
        "MARIADB_HOST", 
        "MARIADB_DATABASE",
        "CHATROOM_ENABLED"
    ]
    
    # JWT_SECRET_KEY 是可选的，因为系统有默认值
    optional_vars = [
        "JWT_SECRET_KEY",
        "SECRET_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # 隐藏敏感信息
            if "SECRET" in var or "PASSWORD" in var:
                display_value = "***"
            else:
                display_value = value
            print(f"   {var}: {display_value}")
        else:
            missing_vars.append(var)
            print(f"   {var}: ❌ 未设置")
    
    # 检查可选变量
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"   {var}: *** (可选)")
        else:
            print(f"   {var}: ⚠️ 未设置 (将使用默认值)")
    
    if missing_vars:
        print_status(f"环境变量: 缺少 {len(missing_vars)} 个必需变量", False)
        return False
    else:
        print_status("环境变量: 配置完整")
        return True

def main():
    """主检查流程"""
    print("🏥 聊天室系统健康检查")
    print("=" * 50)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 检查计数器
    total_checks = 0
    passed_checks = 0
    
    # 1. 环境配置检查
    total_checks += 1
    if check_environment():
        passed_checks += 1
    
    print("\n🚀 核心功能检查:")
    
    # 2. 应用服务检查
    total_checks += 1
    if check_app_service():
        passed_checks += 1
    
    # 3. 数据库检查
    total_checks += 1
    if check_database():
        passed_checks += 1
    
    # 4. 认证检查
    total_checks += 1
    auth_success, token = check_authentication()
    if auth_success:
        passed_checks += 1
    
    # 5. API功能检查
    total_checks += 1
    if check_chatroom_api(token):
        passed_checks += 1
    
    # 总结
    print("\n" + "=" * 50)
    print(f"📊 检查结果: {passed_checks}/{total_checks} 项通过")
    
    if passed_checks == total_checks:
        print_status("系统状态: 全部正常 🎉")
        return 0
    elif passed_checks >= total_checks * 0.8:
        print_status("系统状态: 基本正常 ⚠️")
        print("   建议: 修复失败的检查项以确保最佳性能")
        return 1
    else:
        print_status("系统状态: 存在严重问题 🚨", False)
        print("   建议: 立即查看故障排除文档")
        return 2

if __name__ == "__main__":
    exit_code = main()
    print(f"\n退出代码: {exit_code}")
    print("0=正常, 1=警告, 2=错误")
    sys.exit(exit_code)
