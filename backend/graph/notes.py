from llm import llm
from typing import List, Literal
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import MessagesState, END
from langgraph.types import Command
from langchain_core.messages import HumanMessage, SystemMessage
from agents import search_agent, web_scraper_agent, doc_writer_agent, note_taking_agent, chart_generating_agent

class State(MessagesState):
    next: str

# 创建监督节点
# def make_supervisor_node(llm: BaseChatModel, members: list[str]) -> str:
#     options = ["FINISH"] + members
#     # 优化提示词：明确任务终止条件和决策逻辑
#     system_prompt = (
#         "你是监督者，负责管理工具协作以完成用户任务。\n"
#         "工作原则：\n"
#         "1. 分析当前信息是否足够回答用户问题：\n"
#         "   - 若信息模糊、不完整或仅为概览，必须调用更擅长深入解析的工具；\n"
#         "   - 若信息已具体、充分，返回FINISH。\n"
#         "2. 工具选择逻辑：\n"
#         "   - 若当前结果包含可深入解析的线索（如链接、文档引用），优先选择能处理这类线索的工具；\n"
#         "   - 避免重复调用同一类功能的工具（例如连续用概览类工具）。\n"
#         "3. 必须从可用工具[{members}]中选择，或返回FINISH。\n"
#         "输出格式：仅返回JSON {{\"next\": \"工具名或FINISH\"}}，无其他内容。"
#     ).format(members=", ".join(members))

#     def supervisor_node(state: State) -> Command[Literal[*members, "__end__"]]:
#         # 提取历史消息中最后一个工具的输出（用于判断是否重复调用）
#         last_node = None
#         if state["messages"]:
#             last_msg = state["messages"][-1]
#             if hasattr(last_msg, "name"):
#                 last_node = last_msg.name  # 获取上一个执行的节点名
                
#         # 构建消息
#         messages = [
#             SystemMessage(content=system_prompt),
#             *state["messages"]  # 传入历史消息
#         ]
#         # 调用Deepseek（无结构化输出，直接获取文本）
#         response = llm.invoke(messages).content.strip()

#         # 手动解析JSON（关键适配步骤）
#         try:
#             import json
#             result = json.loads(response)
#             goto = result["next"]

#             # 避免连续调用同一节点（关键优化）
#             if goto == last_node and goto in members:
#                 # 若重复调用，切换到下一个可用节点
#                 next_idx = members.index(goto) + 1
#                 goto = members[next_idx] if next_idx < len(members) else "FINISH"
#         except:
#             # 解析失败时，若上一个是search则切换到web_scraper，否则用第一个节点
#             goto = members[1] if (last_node == members[0] and len(members)>=2) else members[0] if members else "FINISH"

#         if goto == "FINISH":
#             goto = END
#         return Command(goto=goto, update={"next": goto})

#     return supervisor_node

def make_supervisor_node(llm: BaseChatModel, members: list[str]) -> str:
    options = ["FINISH"] + members
    # 优化提示词：明确任务终止条件和决策逻辑
    system_prompt = (
        "你是监督者，负责管理工具协作以完成用户任务。\n"
        "工作原则：\n"
        "1. 分析当前信息是否足够回答用户问题：\n"
        "   - 若信息模糊、不完整或仅为概览，必须调用更擅长深入解析的工具；\n"
        "   - 若信息已具体、充分，返回FINISH。\n"
        "2. 工具选择逻辑：\n"
        "   - 若当前结果包含可深入解析的线索（如链接、文档引用），优先选择能处理这类线索的工具；\n"
        "   - 避免重复调用同一类功能的工具（例如连续用概览类工具）。\n"
        "3. 必须从可用工具[{members}]中选择，或返回FINISH。\n"
        "输出格式：仅返回JSON {{\"next\": \"工具名或FINISH\"}}，无其他内容。"
    ).format(members=", ".join(members))

    def supervisor_node(state: State) -> Command[Literal[*members, "__end__"]]:
        # 提取历史消息中最后一个工具的输出（用于判断是否重复调用）
        last_node = None
        if state["messages"]:
            last_msg = state["messages"][-1]
            if hasattr(last_msg, "name"):
                last_node = last_msg.name  # 获取上一个执行的节点名
                
        # 构建消息
        messages = [
            SystemMessage(content=system_prompt),
            *state["messages"]  # 传入历史消息
        ]
        # 调用LLM
        response = llm.invoke(messages).content.strip()

        # 手动解析JSON
        try:
            import json
            result = json.loads(response)
            goto = result["next"]

            # 避免连续调用同一节点
            if goto == last_node and goto in members:
                next_idx = members.index(goto) + 1
                goto = members[next_idx] if next_idx < len(members) else "FINISH"
        except:
            # 解析失败时的 fallback 逻辑
            goto = members[1] if (last_node == members[0] and len(members)>=2) else members[0] if members else "FINISH"

        # 准备步骤提示消息
        step_message = f"当前步骤：{'开始' if last_node is None else f'完成 {last_node}'}，即将执行 {goto if goto != END else '最终处理'}"
        
        # 处理结束状态
        if goto == "FINISH":
            goto = END
            step_message = "所有处理已完成，正在整理最终结果..."

        # 构建要更新的消息列表（包含步骤提示）
        update_messages = [
            HumanMessage(content=step_message, name="supervisor")  # 步骤提示消息
        ]
        
        # 如果有后续节点，添加节点说明
        if goto != END:
            node_desc = {
                "search": "正在进行网络搜索获取相关信息...",
                "web_scraper": "正在抓取网页内容...",
                "doc_writer": "正在撰写文档...",
                "note_taker": "正在创建内容大纲...",
                "chart_generator": "正在生成图表代码...",
                "research_team": "正在执行调研任务（包含搜索和网页抓取）...",
                "writing_team": "正在执行写作任务（包含文档撰写、大纲创建和图表生成）...",
            }.get(goto, f"正在执行 {goto} 处理...")
            update_messages.append(HumanMessage(content=node_desc, name="supervisor"))

        return Command(
            goto=goto, 
            update={
                "messages": update_messages,
                "next": goto,
            }
        )

    return supervisor_node

# 搜索节点
def search_node(state: State) -> Command[Literal["supervisor"]]:
    result = search_agent.invoke(state)
    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="search")
            ]
        },
        # 工作智能体完成任务后，需始终向管理者汇报
        goto="supervisor",
    )

# 爬虫节点
def web_scraper_node(state: State) -> Command[Literal["supervisor"]]:
    result = web_scraper_agent.invoke(state)
    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="web_scraper")
            ]
        },
        # 工作智能体完成任务后，需始终向管理者汇报
        goto="supervisor",
    )

# 调研监督节点
research_supervisor_node = make_supervisor_node(llm, ["search", "web_scraper"])

# 写作节点
def doc_writing_node(state: State) -> Command[Literal["supervisor"]]:
    result = doc_writer_agent.invoke(state)
    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="doc_writer")
            ]
        },
        # 工作智能体完成任务后，需始终向管理者汇报
        goto="supervisor",
    )

# 写大纲节点
def note_taking_node(state: State) -> Command[Literal["supervisor"]]:
    result = note_taking_agent.invoke(state)
    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="note_taker")
            ]
        },
        # 工作智能体完成任务后，需始终向管理者汇报
        goto="supervisor",
    )

# 写图表代码节点
def chart_generating_node(state: State) -> Command[Literal["supervisor"]]:
    result = chart_generating_agent.invoke(state)
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=result["messages"][-1].content, name="chart_generator"
                )
            ]
        },
        # 工作智能体完成任务后，需始终向管理者汇报
        goto="supervisor",
    )

# 写作监督节点
doc_writing_supervisor_node = make_supervisor_node(llm, ["doc_writer", "note_taker", "chart_generator"])

# 创建顶层监督者节点：管理 research_team 和 writing_team 两个子团队
teams_supervisor_node = make_supervisor_node(llm, ["research_team", "writing_team"])
