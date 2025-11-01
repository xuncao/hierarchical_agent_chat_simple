const express = require('express')
const cors = require('cors')

const app = express()
const PORT = 3001

app.use(cors())
app.use(express.json())

// 模拟AI回复数据
const mockResponses = [
  "您好！我是智能助手，很高兴为您服务。",
  "这是一个基于Vue 3和Element Plus构建的智能对话界面。",
  "我可以回答各种问题，请随时向我提问。",
  "流式输出功能可以模拟真实的AI对话体验。",
  "您可以通过输入框发送消息，我会逐字回复您。"
]

// 聊天接口
app.post('/chat', async (req, res) => {
  const { message, stream = false } = req.body
  
  console.log('收到消息:', message)
  
  if (stream) {
    // 流式响应
    res.writeHead(200, {
      'Content-Type': 'text/plain; charset=utf-8',
      'Transfer-Encoding': 'chunked',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive'
    })
    
    // 随机选择一个回复
    const response = mockResponses[Math.floor(Math.random() * mockResponses.length)]
    
    // 模拟流式输出
    for (let i = 0; i < response.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 50))
      res.write(response[i])
    }
    
    res.end()
  } else {
    // 普通响应
    const response = mockResponses[Math.floor(Math.random() * mockResponses.length)]
    res.json({
      success: true,
      data: response
    })
  }
})

// 健康检查
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() })
})

app.listen(PORT, () => {
  console.log(`Mock server running on http://localhost:${PORT}`)
  console.log('Available endpoints:')
  console.log('  POST /chat - 聊天接口')
  console.log('  GET  /health - 健康检查')
})