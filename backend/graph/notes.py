from llm import llm
from typing import List, Literal, AsyncGenerator
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END
from langgraph.types import Command
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from agents import search_agent, web_scraper_agent, doc_writer_agent, note_taking_agent, chart_generating_agent
from utils import execute_agent_node
from graph.state import State

# 创建监督节点
def make_supervisor_node(
    llm: BaseChatModel, 
    members: list[str], 
    is_top_level: bool = False  # 标记是否为顶层监督者
) -> str:
    options = ["FINISH"] + members

    # 系统提示词差异化：子监督者FINISH后返回上级，顶层监督者FINISH后生成最终答案
    system_prompt = (
        "你是监督者，负责管理以下工作智能体工具或团队之间的协作：{members}。\n"
        "工作原则：\n"
        "1. 分析当前信息是否足够完成当前任务：\n"
        "   - 若信息模糊、不完整，必须调用更匹配的智能体/团队；\n"
        "   - 若信息已充分，返回FINISH。\n"
        "2. 选择逻辑：优先匹配能力最匹配的成员，避免重复调用同一成员，无需调用所有成员。\n"
        "3. 必须从可用列表[{members}]中选择，或返回FINISH。\n"
        "4. 输出格式：仅返回JSON {{\"next\": \"成员名或FINISH\"}}，无其他内容。\n"
        "{finish_note}"  # FINISH行为说明（根据层级差异化）
    ).format(
        members=", ".join(members),
        # 子监督者FINISH后返回上级监督者，顶层监督者FINISH后生成最终答案
        finish_note="若返回FINISH，你需要生成最终答案并结束流程。" if is_top_level 
        else "若返回FINISH，代表当前团队任务已完成，请将结果返回给上级监督者。"
    )

    async def supervisor_node(state: State) -> Command[Literal[*members, "__end__"]]:
        history = state["messages"]
        full_response = []
        last_node = None

        if history:
            last_msg = history[-1]
            if hasattr(last_msg, "name"):
                last_node = last_msg.name
                
        messages = [SystemMessage(content=system_prompt), *history]
        
        async for chunk in llm.astream(messages):
            if chunk.content:
                full_response.append(chunk.content)

        response = ''.join(full_response).strip()
        print('监督者响应:', response)

        try:
            import json
            result = json.loads(response)
            goto = result["next"]
            
            # 验证工具名是否在可用列表中
            if goto not in members and goto != "FINISH":
                print(f"⚠️ 工具名 '{goto}' 不在可用列表中，使用默认工具")
                goto = members[0] if members else "FINISH"
                
            # 避免重复调用同一节点
            if goto == last_node and goto in members:
                next_idx = members.index(goto) + 1
                goto = members[next_idx] if next_idx < len(members) else "FINISH"
                
        except Exception as e:
            print(f"JSON解析失败: {e}, 使用默认工具")
            goto = members[0] if members else "FINISH"

        if goto == "FINISH":
            print(f"🎯 监督者决定{('生成最终回答' if is_top_level else '结束当前团队任务')}")
            if is_top_level:
                print("🎯 进入顶层监督者的FINISH分支 - 使用消息流式更新")
                
                final_answer = ""
                
                # 先创建一个初始消息
                initial_update = {
                    "messages": [*history, AIMessage(content="")],
                    "final_answer": ""
                }
                yield Command(goto=None, update=initial_update)
                
                print("🔴 开始真正的流式生成...")
                
                # 流式更新消息内容
                async for chunk in generate_final_answer_stream(llm, history):
                    print(f"🟢 实时chunk: '{chunk}'")
                    final_answer += chunk
                    
                    # 实时更新最后一个消息的内容
                    yield Command(
                        goto=None,
                        update={
                            "messages": [*history, AIMessage(content=chunk)],
                            "final_answer": final_answer,
                            "is_top_level": True,
                        }
                    )
                
                # 完成后跳转
                yield Command(
                    goto=END,
                    update={
                        "messages": [*history, AIMessage(content='')],
                        "final_answer": final_answer,
                        "is_top_level": True
                    }
                )
            else:
                final_answer = await generate_final_answer(llm, history)
                yield Command(
                    goto=END,
                    update={
                        "messages": [*history, AIMessage(content=final_answer)],
                        "final_answer": final_answer,
                        "is_top_level": False
                    }
                )
            return
        else:
            print(f"✅ 监督者决定下一步: {goto}")
            yield Command(goto=goto, update={"next": goto})

    return supervisor_node

def _build_answer_prompt(history: list) -> str:
    """构建回答提示词"""
    user_question = ""
    for msg in history:
        if isinstance(msg, HumanMessage) and not hasattr(msg, 'name'):
            user_question = msg.content
            break
    
    return f"""
        基于以下对话历史，请直接、完整地回答用户的原始问题。
        用户原始问题：{user_question}
        对话历史：
        {chr(10).join([f"- {type(msg).__name__}: {msg.content}" for msg in history if hasattr(msg, 'content')])}
        请提供完整、准确的最终答案：
    """

async def generate_final_answer(llm: BaseChatModel, history: list) -> str:
    """生成最终回答并返回内容"""
    answer_prompt = _build_answer_prompt(history)
    messages = [HumanMessage(content=answer_prompt)]

    response = ""
    
    print("🤖 生成最终回答...")
    async for chunk in llm.astream(messages):
        if chunk.content:
            response += chunk.content
            print(chunk.content, end="", flush=True)
    
    print("\n✅ 最终回答生成完成")
    return response.strip()
    
async def generate_final_answer_stream(
    llm: BaseChatModel,
    history: list
) -> AsyncGenerator[str, None]:
    answer_prompt = _build_answer_prompt(history)
    messages = [HumanMessage(content=answer_prompt)]

    print("🤖 生成最终回答...")
    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content

# async def search_node(state: State) -> Command[Literal["supervisor"]]:
#     """搜索节点"""
#     async for cmd in execute_agent_node(search_agent, state, "search", "🔍 联网搜索"):
#         yield cmd

async def search_node(state: State) -> Command[Literal["supervisor"]]:
    """搜索节点"""
    return await execute_agent_node(search_agent, state, "search", "🔍 搜索节点")

async def web_scraper_node(state: State) -> Command[Literal["supervisor"]]:
    """网页抓取节点"""
    return await execute_agent_node(web_scraper_agent, state, "web_scraper", "🌐 网页抓取节点")

# 调研监督节点
research_supervisor_node = make_supervisor_node(llm, ["search", "web_scraper"], is_top_level=False)

async def doc_writing_node(state: State) -> Command[Literal["supervisor"]]:
    """写文档节点"""
    return await execute_agent_node(doc_writer_agent, state, "doc_writer", "📁 写文档节点")

async def note_taking_node(state: State) -> Command[Literal["supervisor"]]:
    """写大纲节点"""
    return await execute_agent_node(note_taking_agent, state, "note_taker", "📄 写大纲节点")

async def chart_generating_node(state: State) -> Command[Literal["supervisor"]]:
    """写图表代码节点"""
    return await execute_agent_node(chart_generating_agent, state, "chart_generator", "📈 写图表代码节点")

# 写作监督节点
doc_writing_supervisor_node = make_supervisor_node(llm, ["doc_writer", "note_taker", "chart_generator"], is_top_level=False)

# 创建顶层监督者节点：管理 research_team 和 writing_team 两个子团队
teams_supervisor_node = make_supervisor_node(llm, ["research_team", "writing_team"], is_top_level=True)
