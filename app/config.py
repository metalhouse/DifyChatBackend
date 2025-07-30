import os
from datetime import timedelta

class Config:
    # ...existing code...
    
    # 流式响应配置
    STREAM_CHUNK_SIZE = 1024  # 每个数据块大小
    STREAM_BUFFER_SIZE = 5  # 缓冲区块数
    STREAM_FLUSH_INTERVAL = 1.0  # 强制刷新间隔（秒）
    STREAM_HEARTBEAT_INTERVAL = 5.0  # 心跳间隔（秒）
    STREAM_TIMEOUT = 300  # 流式请求超时（秒）
    
    # 代理设置（如果需要）
    HTTP_PROXY = os.getenv('HTTP_PROXY', None)
    HTTPS_PROXY = os.getenv('HTTPS_PROXY', None)
    
    # ...existing code...