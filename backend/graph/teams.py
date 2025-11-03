from typing import Literal
from langgraph.types import Command
from graph.state import State
from .research_graph import research_graph
from .paper_writing_graph import paper_writing_graph
from utils import call_team

async def call_research_team(state: State) -> Command[Literal["supervisor"]]:
    """调用研究团队"""
    return await call_team(research_graph, state, "research_team", "🔬 研究团队")

async def call_paper_writing_team(state: State) -> Command[Literal["supervisor"]]:
    """调用写作团队"""
    return await call_team(paper_writing_graph, state, "writing_team", "📝 写作团队")