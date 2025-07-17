"""
时间同步检查脚本
"""
import time
from datetime import datetime

def check_time_sync():
    """检查时间同步问题"""
    print("⏰ 时间同步检查")
    print("=" * 50)
    
    # 当前时间
    now_utc = datetime.utcnow()
    now_local = datetime.now()
    timestamp = time.time()
    
    print(f"datetime.utcnow(): {now_utc}")
    print(f"datetime.now(): {now_local}")
    print(f"time.time(): {timestamp}")
    print(f"从时间戳转换: {datetime.fromtimestamp(timestamp)}")
    print(f"从时间戳转换(UTC): {datetime.utcfromtimestamp(timestamp)}")
    
    # 检查时间戳是否合理（应该接近当前时间2024年左右）
    expected_year = 2024
    actual_year = now_utc.year
    
    print(f"\n期望年份: {expected_year}")
    print(f"实际年份: {actual_year}")
    
    if abs(actual_year - expected_year) > 1:
        print(f"⚠️  系统时间可能不正确！")
        print(f"当前系统时间显示为 {actual_year} 年，这可能导致JWT令牌立即过期。")
        
        # 使用更短的过期时间进行测试
        print(f"\n🔧 建议使用较短的过期时间进行测试（如60秒）")
    else:
        print(f"✅ 系统时间正常")

if __name__ == '__main__':
    check_time_sync()
