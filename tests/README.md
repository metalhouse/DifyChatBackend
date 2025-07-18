# 新增API端点测试指南

## 📋 概述

本文档说明如何测试新增加的8个Dify API功能端点。这些API端点实现了完整的Dify官方功能，包括消息反馈、建议问题、对话管理、音频转换等功能。

## 🆕 新增API端点列表

| API端点 | 方法 | 路径 | 功能描述 |
|---------|------|------|----------|
| 消息反馈 | POST | `/api/v1/messages/{message_id}/feedbacks` | 对消息进行点赞/点踩反馈 |
| 建议问题 | GET | `/api/v1/messages/{message_id}/suggested-questions` | 获取下一轮建议问题列表 |
| 对话删除 | DELETE | `/api/v1/conversations/{conversation_id}` | 删除指定对话 |
| 对话重命名 | POST | `/api/v1/conversations/{conversation_id}/name` | 重命名对话或自动生成名称 |
| 语音转文字 | POST | `/api/v1/audio-to-text` | 将音频文件转换为文字 |
| 文字转语音 | POST | `/api/v1/text-to-audio` | 将文字转换为音频 |
| 历史消息 | GET | `/api/v1/conversations/{conversation_id}/messages` | 获取会话历史消息 |
| 应用信息 | GET | `/api/v1/info` | 获取应用基本信息 |

## 🧪 测试工具

### 1. 快速测试脚本 (`quick_api_test.py`)

**用途**: 快速验证所有API端点的基本可用性  
**特点**: 轻量级，快速执行，适合CI/CD

```bash
# 运行快速测试
python tests/quick_api_test.py

# 指定服务器地址
python tests/quick_api_test.py --url http://localhost:5000

# 指定用户凭据
python tests/quick_api_test.py --user testuser --password testpass123
```

### 2. 全面测试脚本 (`test_new_api_endpoints.py`)

**用途**: 详细测试每个API端点的各种场景  
**特点**: 全面覆盖，包含错误处理、权限验证、边界测试

```bash
# 运行全面测试
python tests/test_new_api_endpoints.py
```

### 3. 测试运行器 (`test_runner.py`)

**用途**: 自动启动应用并执行测试  
**特点**: 一键运行，自动管理应用生命周期

```bash
# 快速测试
python tests/test_runner.py quick

# 全面测试  
python tests/test_runner.py comprehensive

# 所有测试
python tests/test_runner.py all

# 查看测试摘要
python tests/test_runner.py --summary
```

### 4. Postman集合 (`DifyChatBackend_New_APIs.postman_collection.json`)

**用途**: 手动测试和API文档  
**特点**: 图形界面，易于调试，支持参数化

**导入方法**:
1. 打开Postman
2. 点击 Import 按钮
3. 选择 `tests/DifyChatBackend_New_APIs.postman_collection.json` 文件
4. 配置环境变量 `base_url` (默认: http://localhost:5000)

## 🚀 快速开始

### 方法1: 使用测试运行器 (推荐)

```bash
# 1. 进入项目目录
cd d:\ChatDify_Codes\DifyChatBackend

# 2. 运行快速测试
python tests/test_runner.py quick
```

### 方法2: 手动启动和测试

```bash
# 1. 启动应用
python app_standard.py

# 2. 在另一个终端运行测试
python tests/quick_api_test.py
```

### 方法3: 使用Postman

1. 导入Postman集合
2. 先运行 "0. 登录获取Token" 请求
3. 按顺序运行其他API测试

## 📊 测试场景

### 1. 消息反馈API测试

```bash
POST /api/v1/messages/{message_id}/feedbacks
```

**测试场景**:
- ✅ 正常点赞反馈
- ✅ 正常点踩反馈  
- ❌ 无效评分值
- ❌ 缺少必需字段
- ❌ 无认证访问

**测试数据**:
```json
{
    "rating": "like",           // 或 "dislike"
    "content": "反馈内容"
}
```

### 2. 建议问题API测试

```bash
GET /api/v1/messages/{message_id}/suggested-questions
```

**测试场景**:
- ✅ 获取现有消息的建议问题
- ⚠️ 不存在的消息ID (返回404或空列表)
- ❌ 无认证访问

### 3. 对话管理API测试

**对话重命名**:
```bash
POST /api/v1/conversations/{conversation_id}/name
```

测试数据:
```json
{
    "name": "新对话名称",      // 手动命名
    "auto_generate": false
}
```

或:
```json
{
    "auto_generate": true      // 自动生成
}
```

**对话删除**:
```bash
DELETE /api/v1/conversations/{conversation_id}
```

### 4. 音频转换API测试

**语音转文字**:
```bash
POST /api/v1/audio-to-text
Content-Type: multipart/form-data
```

支持格式: mp3, mp4, mpeg, mpga, m4a, wav, webm

**文字转语音**:
```bash
POST /api/v1/text-to-audio
```

测试数据:
```json
{
    "text": "要转换的文字"      // 或使用 message_id
}
```

### 5. 历史消息API测试

```bash
GET /api/v1/conversations/{conversation_id}/messages?limit=10&first_id=msg_123
```

**查询参数**:
- `limit`: 限制返回消息数量 (默认20，最大100)
- `first_id`: 起始消息ID (可选)

### 6. 应用信息API测试

```bash
GET /api/v1/info
```

返回应用的基本信息，如名称、版本、描述等。

## 🔐 认证和权限

所有API端点都需要JWT认证：

```http
Authorization: Bearer {access_token}
```

**权限要求**:
- `send_messages`: 消息反馈、音频转换
- `view_conversations`: 建议问题、历史消息、应用信息
- `delete_conversations`: 对话删除
- `edit_conversations`: 对话重命名

## 📋 测试检查清单

### 功能测试
- [ ] 所有API端点可正常访问
- [ ] 请求验证正常工作
- [ ] 响应格式符合标准
- [ ] 错误处理正确

### 安全测试  
- [ ] 无认证访问被拒绝
- [ ] 无效Token被拒绝
- [ ] 权限控制正常
- [ ] 敏感信息正确处理

### 性能测试
- [ ] 响应时间在合理范围内
- [ ] 文件上传处理正常
- [ ] 并发请求处理稳定

### 错误处理测试
- [ ] 不存在的资源ID
- [ ] 无效的请求参数
- [ ] 网络错误恢复
- [ ] 服务器错误处理

## 🐛 常见问题

### 1. 连接失败
```
❌ 无法连接到服务，请确保应用已启动
```
**解决**: 确保Flask应用正在运行，检查端口是否正确

### 2. 认证失败
```
❌ 登录失败，无法进行测试
```
**解决**: 检查用户凭据，确保用户存在且密码正确

### 3. 权限错误
```
❌ 权限不足
```
**解决**: 确保测试用户具有必要的权限

### 4. 文件上传失败
```
❌ 不支持的音频格式
```
**解决**: 使用支持的音频格式 (mp3, wav, m4a等)

## 📈 测试报告示例

```
🎯 测试完成: 8/8 个测试组通过
🎉 所有测试组都已完成！

✅ 消息反馈API: 正常 (状态码: 200)
✅ 建议问题API: 正常 (状态码: 200)  
✅ 对话重命名API: 正常 (状态码: 200)
✅ 对话删除API: 正常 (状态码: 200)
✅ 语音转文字API: 正常 (状态码: 200)
✅ 文字转语音API: 正常 (状态码: 200)
✅ 历史消息API: 正常 (状态码: 200)
✅ 应用信息API: 正常 (状态码: 200)

📊 成功率: 100.0%
```

## 🔧 自定义测试

如需自定义测试，可以修改测试脚本：

1. **修改测试数据**: 编辑 `test_new_api_endpoints.py` 中的测试用例
2. **添加新场景**: 在相应的测试方法中添加新的测试场景  
3. **调整超时**: 修改测试脚本中的 `timeout` 参数
4. **更改服务器**: 使用 `--url` 参数指定不同的服务器地址

## 📚 参考资料

- [DifyChatBackend API文档](../API_DOCUMENTATION_v2.md)
- [错误码定义](../ERROR_CODES.md)
- [API响应格式规范](../API_RESPONSE_FORMAT.md)
- [项目优化任务文档](../backend_optimization_tasks.md)
