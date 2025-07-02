import json
from utils import hash_password, encode_token

with open('users.json', 'r', encoding='utf-8') as f:
    users = json.load(f)

for username, info in users.items():
    # 只加密明文密码（未加密的）
    pwd = info.get('password', '')
    if len(pwd) != 64:  # sha256 长度为64
        info['password'] = hash_password(pwd)
    # 强制编码 token，无论是否已编码
    token = info.get('dify_token', '')
    info['dify_token'] = encode_token(token)

with open('users.json', 'w', encoding='utf-8') as f:
    json.dump(users, f, ensure_ascii=False, indent=2)

print('批量加密完成！')
