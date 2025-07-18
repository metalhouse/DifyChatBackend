# DifyChatBackend API 文档

## 统一接口说明

### 统一响应结构
所有接口均返回如下结构：
```json
{
  "success": true/false,
  "message": "提示或错误信息",
  "data": { ... } // 仅 success 为 true 时返回
}
```

---

### 1. 获取会话列表
- **接口**：GET /api/conversations
- **参数**：
  - user (str, 必填): 用户唯一标识
  - last_id (str, 选填): 当前页最后一条记录ID
  - limit (int, 选填): 返回条数，默认20
  - sort_by (str, 选填): 排序字段
- **返回**：统一格式 {success, message, data}

---

### 2. 发送对话消息
- **接口**：POST /api/chat
- **body参数**：
  - user (str, 必填): 用户唯一标识
  - query (str, 必填): 用户输入内容
  - inputs (dict, 选填): 变量参数
  - response_mode (str, 选填): blocking/streaming，默认blocking
  - conversation_id (str, 选填): 继续对话时传
  - files (list, 选填): 文件列表
  - auto_generate_name (bool, 选填): 自动生成标题
- **返回**：统一格式 {success, message, data} 或流式SSE

---

### 3. 其他说明
- 所有接口均自动带上 DIFY_API_KEY 进行鉴权，前端无需关心。
- streaming 模式下，安卓端需用支持 SSE 的方式处理响应。
- blocking 模式下，直接返回完整 JSON。

---

如需扩展更多 dify API，只需仿照上述结构新增方法和路由。
