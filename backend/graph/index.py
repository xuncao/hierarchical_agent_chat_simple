from llm import llm
from langgraph.graph import StateGraph, START
from .notes import State, teams_supervisor_node
from .teams import call_research_team, call_paper_writing_team

# 构建顶层协调状态图
super_builder = StateGraph(State)
super_builder.add_node("supervisor", teams_supervisor_node)  # 顶层监督者节点
super_builder.add_node("research_team", call_research_team)  # 研究团队调用节点
super_builder.add_node("writing_team", call_paper_writing_team)  # 写作团队调用节点
super_builder.add_edge(START, "supervisor")  # 起始节点为顶层监督者
super_graph = super_builder.compile()  # 编译顶层图