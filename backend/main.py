
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Literal, Optional 
from graph import super_graph as app
import requests
import json
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from llm import llm

# FastAPI 应用
api_app = FastAPI(title="Chat API", version="1.0.0")

# CORS 配置
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求/响应模型
class QuestionRequest(BaseModel):
    question: str

class QuestionResponse(BaseModel):
    answer: str
    status: str

# 流式响应模型
class StreamResponse(BaseModel):
    content: str  # 流式输出内容（工具日志或回答片段）
    status: Literal["streaming", "tool_start", "tool_end", "info", "success", "error"]  # 状态标识
    is_final: bool = False  # 是否为最终回答片段
    tool_name: Optional[str] = None  # 工具/团队名称（状态为tool_start/tool_end时有效）

@api_app.get("/api")
async def root():
    return {"message": "Chat API is running"}

@api_app.post("/api/stream")
async def chat_stream(request: QuestionRequest):
    async def generate():
        # 构建消息
        messages = [
            SystemMessage(content="你是助手"),  # 系统提示
            HumanMessage(content=request.question)  # 用户问题
        ]
        
        final_content = ""
        async for chunk in llm.astream(messages):
            # 获取chunk内容
            if hasattr(chunk, 'content') and chunk.content:
                content = chunk.content
                final_content += content
                
                # 构建响应对象
                stream_data = StreamResponse(
                    content=content,
                    status="streaming",
                    is_final=False  # 流式过程中都不是最终块
                )
                
                yield f"data: {json.dumps(stream_data.model_dump(), ensure_ascii=False)}\n\n"
        
        # 发送最终完成信号
        final_data = StreamResponse(
            content="",  # 最终块可以空内容，或者发送统计信息
            status="success", 
            is_final=True
        )
        yield f"data: {json.dumps(final_data.model_dump(), ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

# 工具节点状态映射字典
TOOL_NODE_MAPPING = {
    # 监督决策类
    "supervisor": "分析",

    # 信息检索类
    "search": "搜索",
    "web_scraper": "网页抓取",
    
    # 文档写作类
    "doc_writer": "文档写作",
    "note_taker": "笔记整理", 
    "chart_generator": "图表生成",
    
    # 团队节点
    "research_team": "调研团队",
    "writing_team": "写作团队",
}

def get_tool_status(event_type: str, node_name: str) -> dict:
    """
    根据事件类型和节点名称获取工具状态信息
    
    Args:
        event_type: 事件类型 ('on_chain_stream', 'on_chain_end' 等)
        node_name: 节点名称
    
    Returns:
        dict: 包含状态信息的字典
    """
    # 获取节点中文名称
    chinese_name = TOOL_NODE_MAPPING.get(node_name, '思考')
    
    # 根据事件类型确定状态
    if event_type == 'on_chain_stream':
        status = "streaming"
        content = f"{chinese_name}中..."
    elif event_type == 'on_chain_start':
        status = "tool_start" 
        content = f"开始{chinese_name}"
    elif event_type == 'on_chain_end':
        status = "tool_end"
        content = f"完成{chinese_name}"
    else:
        status = "info"
        content = f"{chinese_name}处理中"
    
    return {
        "content": content,
        "status": status,
        "tool_name": node_name,
        "chinese_name": chinese_name,
        "is_final": False
    }

# 在 main.py 中使用示例
@api_app.post("/api/chat")
async def chatting(request: QuestionRequest):
    async def generate_stream():
        try:
            inputs = {"messages": [HumanMessage(content=request.question)]}
            
            async for event in app.astream_events(
                inputs,
                version="v1", 
                config={"recursion_limit": 150}
            ):
                event_type = event['event']
                node_name = event.get('name', '')
                
                print(f"事件类型: {event_type}, 节点名称: {node_name}")
                
                # 处理监督者的流式输出
                if (event_type == 'on_chain_stream' and 
                    event.get('name') == 'supervisor'):
                    # print("event['data']", event['data'])
                    
                    chunk = event['data']['chunk']
                    
                    if hasattr(chunk, 'update') and chunk.update:
                        update_data = chunk.update
                        is_top_level = update_data.get("is_top_level", False)
                        
                        if is_top_level and "messages" in update_data and update_data["messages"]:
                            messages = update_data["messages"]
                            
                            for msg in messages:
                                if isinstance(msg, AIMessage) and msg.content:
                                    print(f"📤 发送AI消息: '{msg.content}'")
                                    
                                    chunk_data = StreamResponse(
                                        content=msg.content,
                                        status="streaming", 
                                        is_final=False
                                    )
                                    yield f"data: {json.dumps(chunk_data.model_dump(), ensure_ascii=False)}\n\n"
                
                # 处理其他节点的状态通知
                elif event_type in ['on_chain_start', 'on_chain_stream', 'on_chain_end']:
                    # 获取工具状态信息
                    tool_status = get_tool_status(event_type, node_name)
                    
                    # 发送工具状态到前端
                    status_data = StreamResponse(
                        content=tool_status["content"],
                        status=tool_status["status"],
                        tool_name=tool_status["chinese_name"],
                        is_final=tool_status["is_final"]
                    )
                    yield f"data: {json.dumps(status_data.model_dump(), ensure_ascii=False)}\n\n"
            
            # 最终完成
            final_data = StreamResponse(content="", status="success", is_final=True)
            yield f"data: {json.dumps(final_data.model_dump(), ensure_ascii=False)}\n\n"
            
        except Exception as e:
            error_data = StreamResponse(content=f"错误: {str(e)}", status="error", is_final=True)
            yield f"data: {json.dumps(error_data.model_dump(), ensure_ascii=False)}\n\n"
    
    return StreamingResponse(generate_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api_app, host="0.0.0.0", port=8000)