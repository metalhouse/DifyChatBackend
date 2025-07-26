# DifyChatBackend v2.1.2 发布说明

## 📅 发布信息
- **版本**: v2.1.2
- **发布日期**: 2025-07-24
- **类型**: 功能增强版本

## 🆕 主要新功能

### 智能体欢迎语支持

#### 功能描述
为智能体添加了 `welcome_message` 字段，支持自定义欢迎语文本，前端可用于：
- 智能体介绍页面
- 对话开始时的欢迎信息
- 智能体卡片的描述文本

#### 技术实现
- **数据存储**: `data/agents.json` 中新增 `welcome_message` 字段
- **API响应**: `GET /api/v1/chat/agents` 现在包含欢迎语字段
- **向后兼容**: 使用 `.get("welcome_message", "")` 确保兼容性

#### 示例数据
```json
{
  "id": "agent_1751526225_7744",
  "name": "财务助手_A",
  "welcome_message": "您好！我是您的财务助手，可以高效协助您记录或查询收支信息。\n\n使用方式举例：\n📝 添加记录 → \"不使用预算刷交行卡补交去年个税，费用5800元\"\n🔍 查询记录 → \"请显示2023年所有个税缴纳记录\"\n\n我会自动归类消费类型（如\"税费\"）、支付渠道（如\"交行卡\"）并标注非预算支出。需要其他财务服务也可随时告诉我！\n\n查一下这个月消费情况\n查一下这个月预算使用情况\n请生成本周财务报告，分析支出趋势和预算执行情况。"
}
```

## 🔧 技术改进

### 数据格式支持
- **多行文本**: 支持换行符 `\n` 实现多行显示
- **特殊字符**: 支持引号、emoji等特殊字符
- **格式化内容**: 支持结构化的欢迎语内容

### 代码优化
- **服务层更新**: `services/dify_service.py` 中的 `get_user_agents` 方法
- **容错处理**: 使用 `.get()` 方法确保字段不存在时不会报错
- **缓存兼容**: 新字段自动包含在缓存机制中

## 📚 文档更新

### 更新的文档
1. **API_DOCUMENTATION.md**: 智能体列表API响应格式更新
2. **FRONTEND_INTEGRATION_GUIDE.md**: 前端集成指南新增欢迎语说明
3. **CHANGELOG.md**: 完整的版本变更记录

### 前端集成建议

#### JavaScript 示例
```javascript
// 获取智能体列表
fetch('/api/v1/chat/agents', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
.then(response => response.json())
.then(data => {
  if (data.success) {
    data.data.forEach(agent => {
      console.log('智能体:', agent.name);
      console.log('ID:', agent.id);
      
      // 显示欢迎语
      if (agent.welcome_message) {
        // 处理换行符用于HTML显示
        const welcomeHtml = agent.welcome_message.replace(/\n/g, '<br>');
        document.getElementById('welcome').innerHTML = welcomeHtml;
      }
    });
  }
});
```

#### React 示例
```jsx
function AgentCard({ agent }) {
  return (
    <div className="agent-card">
      <h3>{agent.name}</h3>
      {agent.welcome_message && (
        <div className="welcome-message">
          {agent.welcome_message.split('\n').map((line, index) => (
            <p key={index}>{line}</p>
          ))}
        </div>
      )}
    </div>
  );
}
```

## 🔄 升级说明

### 向后兼容性
- ✅ 完全向后兼容，现有前端代码无需修改
- ✅ `welcome_message` 字段为可选，不存在时返回空字符串
- ✅ 原有的 `id` 和 `name` 字段保持不变

### 建议操作
1. 更新前端代码以支持显示欢迎语
2. 根据需要为其他智能体添加欢迎语内容
3. 测试智能体列表API的新响应格式

## 🎯 下一步计划
- 支持智能体头像和描述图片
- 智能体分类和标签系统
- 智能体能力标签展示
- 动态欢迎语模板系统

---

**完整变更记录**: 查看 [CHANGELOG.md](CHANGELOG.md)  
**前端集成指南**: 查看 [FRONTEND_INTEGRATION_GUIDE.md](FRONTEND_INTEGRATION_GUIDE.md)  
**API文档**: 查看 [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
