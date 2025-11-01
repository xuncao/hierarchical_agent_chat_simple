<template>
  <div class="chat-container">
    <!-- 对话历史区域 -->
    <div class="chat-history" ref="chatHistoryRef">
      <div
        v-for="(message, index) in messages"
        :key="index"
        class="message-container"
        :class="{
          'user-message': message.role === 'user',
          'ai-message': message.role === 'assistant',
        }"
      >
        <div class="message-bubble">
          <div class="message-content">
            <div
              class="message-text"
              v-html="formatMessage(message.content)"
            ></div>
          </div>
        </div>
      </div>

      <!-- 流式输出显示 -->
      <div v-if="isStreaming" class="message-container ai-message">
        <div class="message-bubble">
          <div class="message-content">
            <div class="message-text streaming">
              {{ streamingContent }}<span class="cursor">|</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <div class="input-container">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="2"
          :autosize="{ minRows: 2, maxRows: 4 }"
          placeholder="请输入您的问题..."
          @keydown.enter.exact.prevent="handleSend"
          :disabled="isStreaming"
        />
        <el-button
          type="primary"
          @click="handleSend"
          :loading="isStreaming"
          :disabled="!inputText.trim() || isStreaming"
          class="send-btn"
        >
          {{ isStreaming ? "" : "发送" }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from "vue";
import { ElMessage } from "element-plus";
import axios from "axios";

// 响应式数据
const messages = ref([
  {
    role: "assistant",
    content: "您好！我是您的智能助手，有什么可以帮助您的吗？",
  },
]);

const inputText = ref("");
const isStreaming = ref(false);
const streamingContent = ref("");
const chatHistoryRef = ref(null);

// 格式化消息内容（支持换行）
const formatMessage = (content) => {
  return content.replace(/\n/g, "<br>");
};

// 滚动到底部
const scrollToBottom = async () => {
  await nextTick();
  if (chatHistoryRef.value) {
    chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight;
  }
};

// 处理发送消息
const handleSend = async () => {
  const text = inputText.value.trim();
  if (!text || isStreaming.value) return;

  // 添加用户消息
  messages.value.push({
    role: "user",
    content: text,
  });

  inputText.value = "";
  await scrollToBottom();

  // 开始流式响应
  isStreaming.value = true;
  streamingContent.value = "";

  try {
    const response = await fetch("http://localhost:8000/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question: text,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("无法获取响应流读取器");
    }
    const decoder = new TextDecoder();

    let rawStreamingContent = ""; // 存储原始带Markdown的内容
    let plainStreamingContent = ""; // 存储转义后的纯文本
    const BATCH_SIZE = 20; // 每积累20字转义一次

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split("\n");

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.content) {
              // 1. 积累原始带Markdown的内容
              rawStreamingContent += data.content;

              // 2. 每积累够BATCH_SIZE字，进行一次转义（更新UI）
              if (rawStreamingContent.length >= BATCH_SIZE || data.is_final) {
                plainStreamingContent =
                  convertMarkdownToPlainText(rawStreamingContent);
                streamingContent.value = plainStreamingContent; // UI显示纯文本
                await scrollToBottom();
              }
            }

            if (data.is_final) {
              // 3. 最终统一转义一次（确保无残留Markdown）
              const finalPlainContent =
                convertMarkdownToPlainText(rawStreamingContent);
              // 添加到消息历史
              messages.value.push({
                role: "assistant",
                content: finalPlainContent,
              });
              isStreaming.value = false;
              streamingContent.value = "";
              rawStreamingContent = "";
              plainStreamingContent = "";
              await scrollToBottom();
              return;
            }
          } catch (parseError) {
            console.warn("解析流数据失败:", parseError);
          }
        }
      }
    }

    // 流结束后最终转义
    if (rawStreamingContent) {
      const finalPlainContent = convertMarkdownToPlainText(rawStreamingContent);
      messages.value.push({
        role: "assistant",
        content: finalPlainContent,
      });
    }
  } catch (error) {
    console.log("后端服务不可用，使用演示模式:", error.message);

    // 使用演示模式
    await simulateStreamResponse(text);
  } finally {
    isStreaming.value = false;
    streamingContent.value = "";
    await scrollToBottom();
  }
};

// 核心工具函数：将 Markdown 片段转为纯文本
const convertMarkdownToPlainText = (markdown) => {
  let plain = markdown;
  // 1. 移除标题（## 标题 → 标题）
  plain = plain.replace(/^#{1,6}\s+/gm, "");
  // 2. 移除粗体/斜体（**粗体**/*斜体* → 粗体/斜体）
  plain = plain.replace(/\*\*(.*?)\*\*/g, "$1");
  plain = plain.replace(/\*(.*?)\*/g, "$1");
  // 3. 移除链接（[文本](链接) → 文本）
  plain = plain.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");
  // 4. 移除列表标记（- 列表/* 列表/1. 列表 → 列表）
  plain = plain.replace(/^[\s-*]*\d*\.\s+/gm, "");
  // 5. 移除代码块（```代码```/`代码` → 代码）
  plain = plain.replace(/```[\s\S]*?```/g, "");
  plain = plain.replace(/`([^`]+)`/g, "$1");
  // 6. 移除引用（> 引用 → 引用）
  plain = plain.replace(/^>\s+/gm, "");
  // 7. 移除分割线（---/___ → 空）
  plain = plain.replace(/^-{3,}$/gm, "");
  plain = plain.replace(/^_{3,}$/gm, "");
  return plain.trim();
};

// 模拟流式响应（用于演示）
const simulateStreamResponse = async (userMessage) => {
  // 根据用户消息生成智能回复
  let responseText = "";

  if (userMessage.includes("你好") || userMessage.includes("您好")) {
    responseText =
      "您好！我是您的智能助手，很高兴为您服务。有什么我可以帮助您的吗？";
  } else if (userMessage.includes("功能") || userMessage.includes("做什么")) {
    responseText =
      "我可以回答各种问题，提供信息咨询，并进行智能对话。这个界面支持流式输出，让对话更加自然流畅。";
  } else if (userMessage.includes("技术") || userMessage.includes("实现")) {
    responseText =
      "这个对话界面使用 Vue 3 + Element Plus 构建，支持流式输出和实时交互。前端使用 Vite 作为构建工具，后端可以对接各种 AI 服务。";
  } else {
    responseText =
      "非常抱歉，服务器出现异常，请稍后重试！同时我也会将问题上报给技术团队，感谢您的支持！";
  }

  const words = responseText.split("");
  streamingContent.value = "";

  for (const word of words) {
    streamingContent.value += word;
    await new Promise((resolve) => setTimeout(resolve, 50));
    await scrollToBottom();
  }

  // 添加到消息历史
  messages.value.push({
    role: "assistant",
    content: responseText,
  });

  isStreaming.value = false;
  streamingContent.value = "";
  await scrollToBottom();
};

onMounted(() => {
  scrollToBottom();
});
</script>

<style scoped>
.chat-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.chat-history {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-container {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.message-container.user-message {
  justify-content: flex-end;
}

.message-container.ai-message {
  justify-content: flex-start;
}

.message-bubble {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  max-width: 70%;
}

.message-container.user-message .message-bubble {
  flex-direction: row-reverse;
}

.message-content {
  background: white;
  padding: 12px 16px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  max-width: 100%;
}

.message-container.user-message .message-content {
  background: #409eff;
  color: white;
}

.message-container.ai-message .message-content {
  background: white;
  color: #333;
}

.message-text {
  line-height: 1.5;
  word-wrap: break-word;
}

.message-text.streaming {
  min-height: 20px;
}

.cursor {
  animation: blink 1s infinite;
  color: #409eff;
}

@keyframes blink {
  0%,
  50% {
    opacity: 1;
  }
  51%,
  100% {
    opacity: 0;
  }
}

.input-area {
  padding: 20px;
  background: white;
  border-top: 1px solid #e0e0e0;
}

.input-container {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.input-container :deep(.el-textarea) {
  flex: 1;
}

.input-container :deep(.el-textarea .el-textarea__inner) {
  resize: none;
}

.send-btn {
  height: 56px;
  min-width: 80px;
}
</style>