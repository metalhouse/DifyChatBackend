# DifyChatBackend

本项目为 Python Flask 后端，提供 /api/login 接口，校验用户名和密码并返回 dify_token 及用户信息，适用于 DifyChat 安卓客户端。

## 快速开始
1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. 启动服务：
   ```bash
   python app.py
   ```
3. 接口示例：
   - 地址：`POST /api/login`
   - 参数：`username`、`password`
   - 返回：`success`、`dify_token`、`user_id`、`user_name`、`avatar_url`

## 用户数据存储与加密
- 用户名、密码、dify_token 存储在 users.json 文件中。
- 密码使用 SHA256 加密存储，dify_token 使用 base64 编码存储。
- 登录时自动对密码加密校验，token 自动解码返回。

## 示例用户
| 用户名  | 密码    | dify_token         |
| ------- | ------- | ----------------- |
| user1   | 123456  | jsmnfhktmsikwmsX  |
| user2   | abcdef  | LdjsdbnjFDujskmy  |

## 适配说明
- 安卓端登录时 POST 请求本服务，获取 token 后跳转聊天界面。
- 可根据实际需求扩展用户数据和安全校验。

## License
MIT
