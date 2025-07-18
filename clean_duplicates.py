"""
清理重复的API函数定义
"""

def clean_duplicate_functions():
    """清理API文件中的重复函数定义"""
    
    file_path = "d:/ChatDify_Codes/DifyChatBackend/api/chat_routes_v2.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 找到重复的API函数部分并移除
    duplicate_start = None
    
    for i, line in enumerate(lines):
        # 查找第二个出现的新增API端点注释
        if "# ========== 新增API端点 ==========" in line and duplicate_start is None:
            # 第一次出现，记录位置
            duplicate_start = i
        elif "# ========== 新增API端点 ==========" in line and duplicate_start is not None:
            # 第二次出现，从这里开始删除到文件末尾
            print(f"发现重复部分，从第{i+1}行开始删除")
            lines = lines[:i]
            break
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("✅ 重复函数定义清理完成")

if __name__ == "__main__":
    clean_duplicate_functions()
