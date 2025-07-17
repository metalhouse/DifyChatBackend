"""
兼容性工具函数
保持与旧版本的兼容性
"""
import hashlib
import base64

# 为了保持向后兼容，保留原有的工具函数
def hash_password(password: str) -> str:
    """密码哈希函数 - 兼容旧版本"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def encode_token(token: str) -> str:
    """Token编码函数 - 兼容旧版本"""
    return base64.urlsafe_b64encode(token.encode('utf-8')).decode('utf-8')

def decode_token(token_enc: str) -> str:
    """Token解码函数 - 兼容旧版本"""
    return base64.urlsafe_b64decode(token_enc.encode('utf-8')).decode('utf-8')
