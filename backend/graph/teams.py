from typing import Literal
from langgraph.types import Command
from langchain_core.messages import HumanMessage
from .notes import State
from .research_graph import research_graph
from .paper_writing_graph import paper_writing_graph

# 定义调用研究团队的节点逻辑
def call_research_team(state: State) -> Command[Literal["supervisor"]]:
    # 调用研究团队的状态图，传入最新消息
    response = research_graph.invoke({"messages": state["messages"][-1]})
    # 返回命令：更新消息（添加研究结果），路由回顶层监督者
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=response["messages"][-1].content, name="research_team"
                )
            ]
        },
        goto="supervisor",
    )

# 定义调用文档写作团队的节点逻辑
def call_paper_writing_team(state: State) -> Command[Literal["supervisor"]]:
    # 调用文档写作团队的状态图，传入最新消息
    response = paper_writing_graph.invoke({"messages": state["messages"][-1]})
    # 返回命令：更新消息（添加写作结果），路由回顶层监督者
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=response["messages"][-1].content, name="writing_team"
                )
            ]
        },
        goto="supervisor",
    )