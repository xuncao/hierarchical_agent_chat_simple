# 智能助手对话界面

这是一个基于 Vue 3 + Element Plus 构建的智能助手对话界面，支持流式输出和实时交互。

## 功能特性

- ✅ **对话容器**：固定高度的滚动区域显示对话历史
- ✅ **消息渲染**：区分用户消息(右侧)和AI回复(左侧)，使用不同样式气泡
- ✅ **输入区域**：底部固定输入框+发送按钮组合
- ✅ **流式输出**：AI回复时逐字显示效果
- ✅ **请求处理**：使用fetch发送请求并处理流式响应
- ✅ **演示模式**：在没有后端服务时自动使用演示模式

## 技术栈

- **前端框架**：Vue 3 + Composition API
- **UI组件库**：Element Plus + @element-plus/icons-vue
- **构建工具**：Vite
- **HTTP客户端**：Fetch
- **样式**：CSS3 + Flexbox布局

## 项目结构

```bash
frontend/
├── src/
│   ├── components/
│   │   └── ChatInterface.vue     # 主对话组件
│   ├── App.vue                  # 根组件
│   └── main.js                  # 入口文件
├── mock-server.js               # 模拟后端服务
├── vite.config.js              # Vite配置
└── package.json                 # 项目依赖
```

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
# 方式一：仅启动前端（使用演示模式）
npm run dev

# 方式二：同时启动模拟后端服务
# 终端1：启动模拟后端
node mock-server.js

# 终端2：启动前端
npm run dev
```

### 3. 访问应用

打开浏览器访问 `http://localhost:3000`

## 配置说明

### 后端API配置

在 `vite.config.js` 中配置了代理，将 `/api` 请求转发到后端服务：

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
```

### 演示模式

当后端服务不可用时，系统会自动切换到演示模式：
- 根据用户输入生成智能回复
- 模拟流式输出效果
- 支持常见问题类型识别

## API接口

### 聊天接口

**请求**
```javascript
POST /api/chat
{
  "question": "用户消息",
}
```

**响应**
- 流式响应：markdown格式，逐字返回
- 普通响应：JSON格式，包含完整回复

### 调整样式

主要样式类：
- `.chat-container` - 整体容器
- `.chat-history` - 对话历史区域
- `.message-container` - 消息容器
- `.message-bubble` - 消息气泡
- `.input-area` - 输入区域

### 添加消息类型

在演示模式中扩展智能回复逻辑：

```javascript
if (userMessage.includes('特定关键词')) {
  responseText = '自定义回复内容'
}
```

## 部署说明

### 构建生产版本

```bash
npm run build
```

### 预览生产版本

```bash
npm run preview
```

## 注意事项

1. **跨域问题**：开发环境下使用Vite代理解决，生产环境需要配置CORS
2. **流式响应**：确保后端服务支持流式输出格式
3. **移动端适配**：界面已做基础响应式设计，可根据需要进一步优化
4. **性能优化**：对话历史较多时可考虑虚拟滚动

## 故障排除

### 后端连接失败

- 检查模拟服务是否启动：`node mock-server.js`
- 确认端口8000未被占用
- 查看浏览器控制台错误信息

### 样式异常

- 确认Element Plus CSS已正确导入
- 检查CSS类名冲突
- 验证浏览器兼容性

### 流式输出不工作

- 检查网络连接
- 验证后端服务流式响应格式
- 查看请求配置是否正确

## 扩展建议

## 许可证

MIT License
