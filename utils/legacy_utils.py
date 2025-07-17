import hashlib
import base64

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def encode_token(token: str) -> str:
    return base64.urlsafe_b64encode(token.encode('utf-8')).decode('utf-8')

def decode_token(token_enc: str) -> str:
    return base64.urlsafe_b64decode(token_enc.encode('utf-8')).decode('utf-8')
