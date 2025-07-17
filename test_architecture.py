#!/usr/bin/env python3
"""
测试脚本 - 验证重构后的架构
"""
import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_imports():
    """测试所有模块导入"""
    try:
        print("🔄 测试模块导入...")
        
        # 测试服务模块
        from services.user_service import user_service
        print("✅ 用户服务导入成功")
        
        from services.dify_service import dify_service
        print("✅ Dify服务导入成功")
        
        # 测试API路由
        from api.auth_routes import login
        print("✅ 认证路由导入成功")
        
        from api.chat_routes import api_conversations, api_chat, api_agents
        print("✅ 对话路由导入成功")
        
        # 测试主应用
        from app_v2 import create_app
        app = create_app()
        print("✅ Flask应用创建成功")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_basic_functionality():
    """测试基本功能"""
    try:
        print("\n🔄 测试基本功能...")
        
        # 测试用户服务
        from services.user_service import user_service
        users = user_service.load_users()
        print(f"✅ 用户数据加载成功，共{len(users)}个用户")
        
        # 测试Dify服务
        from services.dify_service import dify_service
        agents = dify_service.get_user_agents("test_user")
        print(f"✅ 智能体数据加载成功，共{len(agents)}个智能体")
        
        return True
        
    except Exception as e:
        print(f"❌ 功能测试失败: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 DifyChatBackend 架构重构测试")
    print("=" * 50)
    
    # 测试导入
    import_success = test_imports()
    
    if import_success:
        # 测试功能
        func_success = test_basic_functionality()
        
        if func_success:
            print("\n🎉 所有测试通过！新架构工作正常。")
            print("\n📝 下一步建议:")
            print("  1. 运行: python app_v2.py 启动新版本服务")
            print("  2. 测试API接口是否正常工作")
            print("  3. 确认无误后可以替换原有的app.py")
        else:
            print("\n⚠️  功能测试失败，需要检查配置文件。")
    else:
        print("\n❌ 模块导入失败，请检查代码结构。")
    
    print("=" * 50)
