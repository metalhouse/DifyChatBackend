# Postman集合使用指南

## 概述

`DifyChatBackend_API_v1_Collection.postman_collection.json` 是为DifyChatBackend API v1创建的完整测试集合，包含所有主要API端点的测试用例。

## 导入Postman集合

### 方法1: 通过文件导入
1. 打开Postman应用
2. 点击左上角的 **Import** 按钮
3. 选择 **Upload Files** 或直接拖拽文件
4. 选择 `DifyChatBackend_API_v1_Collection.postman_collection.json` 文件
5. 点击 **Import** 完成导入

### 方法2: 通过链接导入（如果文件在线）
1. 在Postman中点击 **Import**
2. 选择 **Link** 标签
3. 粘贴文件的URL
4. 点击 **Continue** 并 **Import**

## 配置环境变量

### 设置基础变量
导入后，你需要配置以下环境变量：

1. 点击右上角的齿轮图标 ⚙️ (Manage Environments)
2. 点击 **Add** 创建新环境，命名为 "DifyChatBackend Local"
3. 添加以下变量：

| 变量名 | 初始值 | 当前值 | 描述 |
|--------|--------|--------|------|
| baseUrl | http://localhost:5000 | http://localhost:5000 | 服务器基础URL |
| accessToken | (空) | (空) | JWT访问令牌 |
| refreshToken | (空) | (空) | JWT刷新令牌 |
| agentId | (空) | (空) | 智能体ID |
| conversationId | (空) | (空) | 对话ID |
| messageId | (空) | (空) | 消息ID |
| username | admin | admin | 用户名 |

4. 点击 **Add** 保存环境
5. 在右上角的环境下拉列表中选择 "DifyChatBackend Local"

## 使用流程

### 第一步：启动服务器
确保DifyChatBackend服务器正在运行：
```bash
cd d:\ChatDify_Codes\DifyChatBackend
python app.py
```

### 第二步：测试公开端点
1. 展开 **系统信息** 文件夹
2. 运行 **系统健康检查** - 应该返回200状态
3. 运行 **获取系统信息** - 应该返回系统基本信息

### 第三步：用户认证
1. 展开 **认证管理** 文件夹
2. 运行 **用户登录** 请求
   - 确保请求体中的用户名和密码正确
   - 成功后会返回access_token和refresh_token
3. **重要**: 复制返回的tokens到环境变量中：
   - 复制 `access_token` 到环境变量 `accessToken`
   - 复制 `refresh_token` 到环境变量 `refreshToken`

### 第四步：测试认证端点
现在可以测试需要认证的端点：
1. **获取当前用户信息** - 验证认证是否工作
2. **聊天功能** 文件夹中的端点
3. **缓存管理** 文件夹中的端点

## 自动化Token管理

### 添加自动化脚本
为了更好的使用体验，可以在登录请求中添加自动化脚本：

1. 选择 **用户登录** 请求
2. 点击 **Tests** 标签
3. 添加以下脚本：

```javascript
// 自动保存登录返回的tokens
if (pm.response.code === 200) {
    const responseData = pm.response.json();
    if (responseData.success && responseData.data && responseData.data.tokens) {
        // 保存access token
        pm.environment.set("accessToken", responseData.data.tokens.access_token);
        // 保存refresh token  
        pm.environment.set("refreshToken", responseData.data.tokens.refresh_token);
        
        console.log("✅ Tokens saved to environment variables");
        
        // 可选: 保存用户信息
        if (responseData.data.user) {
            pm.environment.set("username", responseData.data.user.username);
        }
    }
} else {
    console.log("❌ Login failed:", pm.response.text());
}
```

### 自动刷新Token脚本
在 **刷新令牌** 请求的Tests中添加：

```javascript
// 自动保存刷新后的新token
if (pm.response.code === 200) {
    const responseData = pm.response.json();
    if (responseData.success && responseData.data && responseData.data.tokens) {
        pm.environment.set("accessToken", responseData.data.tokens.access_token);
        console.log("✅ Access token refreshed");
    }
}
```

## 测试特定功能流程

### 聊天功能测试流程
1. **登录** → 获取tokens
2. **获取智能体列表** → 复制一个agent_id到环境变量
3. **获取对话列表** → 查看现有对话
4. **创建新对话** → 复制conversation_id到环境变量
5. **发送聊天消息** → 测试聊天功能

### 缓存管理测试流程
1. **缓存健康检查** → 确认缓存系统状态
2. **获取缓存统计** → 查看当前缓存情况
3. **预热缓存** → 预加载数据
4. **刷新缓存** → 更新特定缓存
5. **获取缓存统计** → 验证缓存变化

## 高级使用技巧

### 1. 创建测试套件
1. 点击集合名称旁的 **...** 
2. 选择 **Run collection**
3. 选择要运行的请求
4. 设置环境和迭代次数
5. 点击 **Run** 执行批量测试

### 2. 环境切换
创建多个环境用于不同场景：
- **Local Development**: localhost:5000
- **Staging**: your-staging-url
- **Production**: your-production-url

### 3. 使用Pre-request Scripts
在需要动态数据的请求中添加pre-request脚本：

```javascript
// 生成随机对话名称
pm.environment.set("randomConversationName", "测试对话_" + Math.floor(Math.random() * 1000));

// 生成随机消息内容
pm.environment.set("randomMessage", "这是测试消息 " + new Date().toISOString());
```

### 4. 数据驱动测试
1. 准备CSV或JSON数据文件
2. 在Collection Runner中上传数据文件
3. 在请求中使用 `{{variableName}}` 引用数据

## 故障排除

### 常见问题

#### 1. 401 Unauthorized错误
- **原因**: Token过期或无效
- **解决**: 重新登录获取新的token，或使用refresh token

#### 2. 404 Not Found错误
- **原因**: 服务器未启动或URL错误
- **解决**: 检查服务器状态，确认baseUrl正确

#### 3. 环境变量未生效
- **原因**: 环境未选择或变量名错误
- **解决**: 确认选择了正确的环境，检查变量名拼写

#### 4. 请求体格式错误
- **原因**: JSON格式错误或必需字段缺失
- **解决**: 检查请求体格式，参考API文档

### 调试技巧

1. **查看Console**: 打开Postman Console查看详细日志
2. **检查Headers**: 确认Authorization header格式正确
3. **验证环境变量**: 在请求URL中使用`{{baseUrl}}`确认变量解析
4. **使用Tests验证**: 添加测试脚本验证响应内容

## 集合结构说明

```
DifyChatBackend API v1
├── 认证管理/           # 登录、登出、token管理
├── 聊天功能/           # 智能体、对话、消息
├── 缓存管理/           # 缓存操作和监控
├── 用户管理/           # 用户权限和信息
├── 智能体管理/         # 智能体配置
├── 系统信息/           # 健康检查、系统信息
└── Dify标准API/        # Dify兼容接口
```

## 扩展和定制

### 添加新的测试请求
1. 右键点击相应文件夹
2. 选择 **Add Request**
3. 配置请求方法、URL、headers、body
4. 添加Tests脚本进行验证

### 导出和分享
1. 右键点击集合名称
2. 选择 **Export**
3. 选择版本格式（推荐v2.1）
4. 保存并分享给团队成员

这个Postman集合为你提供了完整的API测试能力，可以帮助你验证所有功能并进行开发调试。
