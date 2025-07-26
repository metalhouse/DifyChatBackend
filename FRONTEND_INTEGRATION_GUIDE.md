# 前端集成指南 v2.1

## 📋 本次更新概览 (v2.1.2 - 2025-07-24)

### 🆕 智能体欢迎语功能

**智能体数据结构扩展**:
- 新增 `welcome_message` 字段，提供智能体欢迎语
- 支持多行文本、换行符和格式化内容
- 前端可用于智能体介绍页面或对话开始时的欢迎信息

### 🔧 重要数据格式修复 (v2.1.1)

**智能体列表API数据格式标准化**:
- 修复了 `GET /api/v1/chat/agents` 返回的数据格式
- 字段名从 `agent_id` 更改为 `id`，现在符合前端JavaScript标准
- 确保前端可以正确解析和使用智能体数据

### ✅ 验证通过的API端点

以下API端点已经过完整测试，可以直接用于前端集成：

1. **用户认证**: `POST /api/v1/auth/login`
2. **智能体列表**: `GET /api/v1/chat/agents` ⭐ **数据格式已修复**
3. **聊天消息**: `POST /api/v1/chat/messages`
4. **系统信息**: `GET /api/v1/info/public` (公开) / `GET /api/v1/info` (认证)

## 🎯 关键数据格式更新

### 智能体列表数据格式 (已修复)

**修复前** ❌:
```json
{
  "data": [
    {
      "agent_id": "agent_1751526225_7744",  // 错误字段名
      "name": "财务助手_A"
    }
  ]
}
```

**修复后** ✅:
```json
{
  "data": [
    {
      "id": "agent_1751526225_7744",      // 正确字段名
      "name": "财务助手_A",
      "welcome_message": "您好！我是您的财务助手，可以高效协助您记录或查询收支信息。\n\n使用方式举例：\n📝 添加记录 → \"不使用预算刷交行卡补交去年个税，费用5800元\"\n🔍 查询记录 → \"请显示2023年所有个税缴纳记录\"\n\n我会自动归类消费类型（如\"税费\"）、支付渠道（如\"交行卡\"）并标注非预算支出。需要其他财务服务也可随时告诉我！\n\n查一下这个月消费情况\n查一下这个月预算使用情况\n请生成本周财务报告，分析支出趋势和预算执行情况。"  // 🆕 v2.1.2 新增欢迎语
    }
  ],
  "success": true,
  "message": "获取智能体列表成功",
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 1,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

根据前端需求，我们在 v2.1 版本中新增了以下关键功能：

### 🆕 新增API端点

1. **单个智能体详情**: `GET /api/v1/agents/{id}`
2. **单个对话详情**: `GET /api/v1/conversations/{id}`
3. **系统统计信息**: `GET /api/v1/stats`
4. **分层系统信息**: 公开版 `/api/v1/info/public` 和认证版 `/api/v1/info`

### 🔒 安全优化

- **分层信息披露**: 基础信息公开访问，敏感信息需要认证
- **统计信息权限控制**: 只有管理员可以访问系统统计
- **用户权限增强**: 在认证版系统信息中返回用户权限列表

## 🎯 前端集成要点

### 1. 智能体列表获取 (已修复)

**正确的前端JavaScript代码**:
```javascript
// 获取智能体列表
const getAgents = async (token) => {
  const response = await fetch('/api/v1/chat/agents', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  const result = await response.json();
  
  if (result.success) {
    // ✅ 现在可以正确访问 id 字段
    const agents = result.data.map(agent => ({
      id: agent.id,           // 正确的字段名
      name: agent.name,
      // 其他字段...
    }));
    return agents;
  } else {
    throw new Error(result.message);
  }
};

// 使用智能体ID发送消息
const sendMessage = async (message, agentId, token, conversationId = null) => {
  const response = await fetch('/api/v1/chat/messages', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      message: message,
      agent_id: agentId,      // 使用获取到的智能体ID
      conversation_id: conversationId
    })
  });
  
  return await response.json();
};
```

### 2. 系统信息获取策略

**推荐做法**:
```javascript
// 应用启动时获取公开信息
const getPublicInfo = async () => {
  const response = await fetch('/api/v1/info/public');
  const data = await response.json();
  return data.data; // 无需认证
};

// 用户登录后获取完整信息
const getFullInfo = async (token) => {
  const response = await fetch('/api/v1/info', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  const data = await response.json();
  return data.data; // 包含用户权限和系统详情
};
```

### 3. 单资源详情页面

**智能体详情页**:
```javascript
const getAgentDetail = async (agentId, token) => {
  const response = await fetch(`/api/v1/agents/${agentId}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (response.ok) {
    const data = await response.json();
    return data.data; // 包含完整的智能体信息和统计
  }
  
  throw new Error('获取智能体详情失败');
};
```

**对话详情页**:
```javascript
const getConversationDetail = async (conversationId, token, includeMessages = false) => {
  const url = new URL(`/api/v1/conversations/${conversationId}`, window.location.origin);
  if (includeMessages) {
    url.searchParams.append('include_messages', 'true');
  }
  
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (response.ok) {
    const data = await response.json();
    return data.data;
  }
  
  throw new Error('获取对话详情失败');
};
```

### 3. 管理员统计面板

**系统统计获取**:
```javascript
const getSystemStats = async (token, timeRange = '24h', includeDetails = false) => {
  const url = new URL('/api/v1/stats', window.location.origin);
  url.searchParams.append('time_range', timeRange);
  url.searchParams.append('include_details', includeDetails.toString());
  
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (response.ok) {
    const data = await response.json();
    return data.data;
  }
  
  // 检查是否为权限不足
  if (response.status === 403) {
    throw new Error('需要管理员权限才能查看统计信息');
  }
  
  throw new Error('获取系统统计失败');
};
```

## 🔄 权限管理建议

### 权限检查
```javascript
const checkUserPermissions = (userInfo) => {
  const permissions = userInfo.user_permissions || [];
  
  return {
    canViewAgents: permissions.includes('access_agents'),
    canViewConversations: permissions.includes('view_conversations'),
    canCreateConversations: permissions.includes('create_conversations'),
    canViewStats: permissions.includes('admin'),
    canManageCache: permissions.includes('manage_cache')
  };
};
```

### 路由守卫示例
```javascript
// React Router 示例
const ProtectedRoute = ({ children, requiredPermission, userPermissions }) => {
  if (!userPermissions.includes(requiredPermission)) {
    return <Navigate to="/unauthorized" />;
  }
  return children;
};

// 使用示例
<ProtectedRoute requiredPermission="admin" userPermissions={user.permissions}>
  <StatsPage />
</ProtectedRoute>
```

## 📊 数据缓存建议

### 缓存策略
```javascript
class APICache {
  constructor() {
    this.cache = new Map();
    this.ttl = new Map();
  }
  
  set(key, data, ttlSeconds = 300) {
    this.cache.set(key, data);
    this.ttl.set(key, Date.now() + ttlSeconds * 1000);
  }
  
  get(key) {
    if (this.ttl.get(key) < Date.now()) {
      this.cache.delete(key);
      this.ttl.delete(key);
      return null;
    }
    return this.cache.get(key);
  }
  
  // 智能体详情缓存（5分钟）
  async getAgentDetail(id, token) {
    const cacheKey = `agent_${id}`;
    let data = this.get(cacheKey);
    
    if (!data) {
      data = await getAgentDetail(id, token);
      this.set(cacheKey, data, 300);
    }
    
    return data;
  }
  
  // 系统统计缓存（1分钟，因为需要实时性）
  async getStats(token, timeRange = '24h') {
    const cacheKey = `stats_${timeRange}`;
    let data = this.get(cacheKey);
    
    if (!data) {
      data = await getSystemStats(token, timeRange);
      this.set(cacheKey, data, 60);
    }
    
    return data;
  }
}
```

## 🎨 UI组件建议

### 智能体详情卡片
```jsx
const AgentDetailCard = ({ agentId }) => {
  const [agent, setAgent] = useState(null);
  const [loading, setLoading] = useState(true);
  const { token } = useAuth();
  
  useEffect(() => {
    getAgentDetail(agentId, token)
      .then(setAgent)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [agentId, token]);
  
  if (loading) return <Spinner />;
  if (!agent) return <ErrorMessage />;
  
  return (
    <div className="agent-detail-card">
      <h2>{agent.name}</h2>
      <p>{agent.description}</p>
      <div className="agent-stats">
        <div>总对话: {agent.stats.total_conversations}</div>
        <div>总消息: {agent.stats.total_messages}</div>
        <div>平均响应时间: {agent.stats.avg_response_time}</div>
      </div>
      <div className="agent-settings">
        <p>温度: {agent.settings.temperature}</p>
        <p>最大令牌: {agent.settings.max_tokens}</p>
      </div>
    </div>
  );
};
```

### 系统统计仪表板
```jsx
const StatsDashboard = () => {
  const [stats, setStats] = useState(null);
  const [timeRange, setTimeRange] = useState('24h');
  const { token, user } = useAuth();
  
  // 权限检查
  if (!user.permissions.includes('admin')) {
    return <div>需要管理员权限</div>;
  }
  
  useEffect(() => {
    getSystemStats(token, timeRange, true)
      .then(setStats)
      .catch(console.error);
  }, [token, timeRange]);
  
  return (
    <div className="stats-dashboard">
      <div className="time-range-selector">
        <button onClick={() => setTimeRange('24h')}>24小时</button>
        <button onClick={() => setTimeRange('7d')}>7天</button>
        <button onClick={() => setTimeRange('30d')}>30天</button>
      </div>
      
      {stats && (
        <div className="stats-grid">
          <StatCard title="用户统计" data={stats.users} />
          <StatCard title="智能体统计" data={stats.agents} />
          <StatCard title="对话统计" data={stats.conversations} />
          <StatCard title="消息统计" data={stats.messages} />
          <StatCard title="性能指标" data={stats.performance} />
        </div>
      )}
    </div>
  );
};
```

## 🐛 错误处理建议

### 统一错误处理
```javascript
const handleAPIError = (error, response) => {
  if (response.status === 401) {
    // 认证失败，重定向到登录页
    window.location.href = '/login';
    return;
  }
  
  if (response.status === 403) {
    // 权限不足
    toast.error('权限不足，请联系管理员');
    return;
  }
  
  if (response.status === 404) {
    // 资源不存在
    toast.error('请求的资源不存在');
    return;
  }
  
  if (response.status >= 500) {
    // 服务器错误
    toast.error('服务器错误，请稍后重试');
    return;
  }
  
  // 其他错误
  toast.error(error.message || '操作失败');
};
```

## ⚡ 性能优化建议

1. **懒加载**: 对话详情页的消息历史可以分页加载
2. **虚拟滚动**: 长对话列表使用虚拟滚动
3. **预加载**: 智能体列表页可以预加载前几个智能体的详情
4. **防抖**: 搜索功能使用防抖，减少API请求
5. **缓存**: 合理使用本地缓存，减少重复请求

## 🔄 Token自动刷新

系统会在响应头中返回新的访问令牌，前端需要处理：

```javascript
const apiRequest = async (url, options = {}) => {
  const response = await fetch(url, options);
  
  // 检查是否有新的访问令牌
  const newToken = response.headers.get('X-New-Access-Token');
  if (newToken) {
    // 更新存储的令牌
    localStorage.setItem('access_token', newToken);
    // 更新应用状态
    updateAuthToken(newToken);
  }
  
  return response;
};
```

## 🚀 部署前检查清单

- [ ] 确认所有新端点的权限配置正确
- [ ] 测试分层信息披露功能
- [ ] 验证缓存功能正常工作
- [ ] 检查错误处理逻辑
- [ ] 确认统计端点的性能
- [ ] 验证前端权限检查逻辑
- [ ] 测试Token自动刷新机制

---

**文档版本**: v2.1.0  
**更新时间**: 2025年1月15日  
**适用前端**: React/Vue/Angular 等现代前端框架
