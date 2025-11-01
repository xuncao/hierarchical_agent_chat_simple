
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from graph import super_graph as app
import requests
import json

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
    content: str
    status: str = "streaming"
    is_final: bool = False

@api_app.get("/api")
async def root():
    return {"message": "Chat API is running"}

@api_app.post("/api/chat")
async def chatting(request: QuestionRequest):
    # 1. 定义文本拆分函数（放在接口函数内部或外部均可）
    def split_by_char(content: str, chunk_size: int = 1) -> list[str]:
        """将内容按固定长度拆分（默认1个字符，逐字输出）"""
        return [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
    
    async def generate_stream():
        try:
            inputs = {
                "messages": [("user", request.question)],
            }
            print(f"\n===== 收到新请求: {request.question} =====")
            
            final_content = ""
            step = 1
            current_node = "未知节点"
            
            try:
                for output in app.stream(inputs, {"recursion_limit": 150}):
                    print(f"\n----- 步骤 {step}: 执行节点 -----")
                    
                    for node_name, result in output.items():
                        current_node = node_name
                        print(f"\n----- {node_name} -----")
                        if "messages" in result and result["messages"]:
                            latest_message = result["messages"][-1]
                            message_content = latest_message.content
                            if message_content:
                                # 2. 调用拆分函数
                                chunks = split_by_char(message_content) 
                                
                                for i, chunk in enumerate(chunks):
                                    final_content += chunk
                                    is_final_chunk = (i == len(chunks) - 1)
                                    stream_data = StreamResponse(
                                        content=chunk,
                                        status="streaming" if not is_final_chunk else "success",
                                        is_final=is_final_chunk
                                    )
                                    yield f"data: {json.dumps(stream_data.model_dump(), ensure_ascii=False)}\n\n"
                                    await asyncio.sleep(0.05)  # 控制打字速度
                    
                    step += 1
                    
            except Exception as stream_err:
                error_msg = f"图流转失败（当前节点：{current_node}）: {str(stream_err)}"
                error_data = StreamResponse(
                    content=f"处理错误: {error_msg}",
                    status="error",
                    is_final=True
                )
                yield f"data: {json.dumps(error_data.model_dump(), ensure_ascii=False)}\n\n"
                return
            
            if not final_content:
                final_data = StreamResponse(
                    content="",
                    status="success",
                    is_final=True
                )
                yield f"data: {json.dumps(final_data.model_dump(), ensure_ascii=False)}\n\n"
            
        except Exception as e:
            error_data = StreamResponse(
                content=f"系统错误: {str(e)}",
                status="error",
                is_final=True
            )
            yield f"data: {json.dumps(error_data.model_dump(), ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

# 辅助函数：按字符拆分内容（或按标点/空格拆分）
def split_by_char(content: str, chunk_size: int = 1) -> list[str]:
    """将内容按固定长度拆分（默认1个字符，即逐字输出）"""
    return [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]

# 可选：按标点拆分（更自然，适合长句子）
def split_by_punctuation(content: str) -> list[str]:
    """按标点符号拆分，优先在逗号、句号处断句"""
    import re
    # 匹配中文标点和英文标点，作为拆分点
    split_points = re.findall(r'[^，。,.;!?]+[，。,.;!?]?', content)
    # 处理最后可能残留的内容
    if not split_points or split_points[-1] != content:
        split_points.append(content[len(''.join(split_points)):])
    return [p for p in split_points if p]  # 过滤空字符串

# @api_app.post("/api/chat")
# async def chatting(request: QuestionRequest):
#     async def generate_stream():
#         try:
#             inputs = {
#                 "messages": [
#                     ("user", request.question),
#                 ],
#             }
            
#             print(f"\n===== 收到新请求: {request.question} =====")
            
#             final_content = ""
#             step = 1
#             current_node = "未知节点"
            
#             try:
#                 for output in app.stream(inputs, {"recursion_limit": 150}):
#                     print(f"\n----- 步骤 {step}: 执行节点 -----")
                    
#                     for node_name, result in output.items():
#                         current_node = node_name
#                         if "messages" in result and result["messages"]:
#                             latest_message = result["messages"][-1]
#                             if latest_message.content:
#                                 # 发送流式数据块
#                                 stream_data = StreamResponse(
#                                     content=latest_message.content,
#                                     status="streaming",
#                                     is_final=False
#                                 )
#                                 yield f"data: {json.dumps(stream_data.model_dump(), ensure_ascii=False)}\n\n"
#                                 final_content = latest_message.content
                    
#                     step += 1
                    
#             except Exception as stream_err:
#                 error_msg = f"图流转失败（当前节点：{current_node}）: {str(stream_err)}"
#                 error_data = StreamResponse(
#                     content=f"处理错误: {error_msg}",
#                     status="error",
#                     is_final=True
#                 )
#                 yield f"data: {json.dumps(error_data.model_dump(), ensure_ascii=False)}\n\n"
#                 return
            
#             # 发送最终完成信号
#             final_data = StreamResponse(
#                 content=final_content,
#                 status="success",
#                 is_final=True
#             )
#             yield f"data: {json.dumps(final_data.model_dump(), ensure_ascii=False)}\n\n"
            
#         except Exception as e:
#             error_data = StreamResponse(
#                 content=f"系统错误: {str(e)}",
#                 status="error",
#                 is_final=True
#             )
#             yield f"data: {json.dumps(error_data.model_dump(), ensure_ascii=False)}\n\n"
    
#     return StreamingResponse(
#         generate_stream(),
#         media_type="text/event-stream",
#         headers={
#             "Cache-Control": "no-cache",
#             "Connection": "keep-alive",
#             "Access-Control-Allow-Origin": "*",
#             "Access-Control-Allow-Headers": "*",
#         }
#     )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api_app, host="0.0.0.0", port=8000)