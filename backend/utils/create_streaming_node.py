from typing import Callable, Literal, TypeVar
from langgraph.types import Command
from langchain_core.messages import HumanMessage
from graph.state import State

async def execute_agent_node(agent, state: State, node_name: str, node_display_name: str) -> Command[Literal["supervisor"]]:
    """针对您具体输出格式的专用版本"""
    full_content = ""
    print(f"\n{node_display_name} 开始工作...")
    
    try:
        async for chunk in agent.astream(state):
            # 针对您的具体输出格式提取
            content = extract_specific_format(chunk)
            if content:
                full_content += content + "\n"
                print(content, end="", flush=True)
    
    except Exception as e:
        error_msg = f"\n❌ {node_display_name} 出错: {e}"
        full_content += error_msg
        print(error_msg)
    
    print(f"\n✅ {node_display_name} 完成")
    
    return Command(
        update={
            "messages": [
                HumanMessage(content=full_content.strip(), name=node_name)
            ]
        },
        goto="supervisor",
    )

def extract_specific_format(chunk) -> str:
    """针对您具体输出格式的提取"""
    if isinstance(chunk, dict) and 'agent' in chunk:
        agent_data = chunk['agent']
        if 'messages' in agent_data and agent_data['messages']:
            message = agent_data['messages'][0]  # 取第一个消息
            if hasattr(message, 'content') and message.content:
                return message.content
    return ""

async def call_team(team_graph, state: State, team_name: str, team_display_name: str) -> Command[Literal["supervisor"]]:
    """调试版本：查看团队完整输出"""
    full_content = ""
    print(f"\n{team_display_name} 开始工作...")
    
    try:
        input_data = {"messages": state["messages"][-1]}
        all_outputs = []
        
        async for chunk in team_graph.astream(input_data):
            print(f"📦 {team_display_name} 块: {list(chunk.keys())}")
            
            # 详细记录每个块的内容
            chunk_info = {}
            for key, value in chunk.items():
                if isinstance(value, dict) and 'messages' in value:
                    messages_content = []
                    for msg in value['messages']:
                        if hasattr(msg, 'content') and msg.content:
                            messages_content.append(msg.content)
                    if messages_content:
                        chunk_info[key] = messages_content
            
            all_outputs.append(chunk_info)
            
            # 特别关注监督者的最终决策
            if 'supervisor' in chunk and isinstance(chunk['supervisor'], dict):
                supervisor_data = chunk['supervisor']
                print(f"🔍 监督者数据: {supervisor_data}")
                
                if supervisor_data.get('next') == '__end__':
                    print("🎯 找到最终决策点")
                    # 尝试各种方式提取内容
                    final_content = extract_final_content(supervisor_data)
                    if final_content:
                        full_content = final_content
                        break
        
        # 如果没有找到最终内容，输出调试信息
        if not full_content:
            debug_info = f"{team_display_name} 调试信息:\n"
            for i, output in enumerate(all_outputs):
                debug_info += f"块{i+1}: {output}\n"
            full_content = debug_info
    
    except Exception as e:
        error_msg = f"\n❌ {team_display_name} 出错: {e}"
        full_content = error_msg
        print(error_msg)
    
    print(f"\n✅ {team_display_name} 完成")
    
    return Command(
        update={
            "messages": [
                HumanMessage(content=full_content.strip(), name=team_name)
            ]
        },
        goto="supervisor",
    )

def extract_final_content(supervisor_data: dict) -> str:
    """调试版最终内容提取"""
    print("🔍 详细检查监督者数据:")
    print(f"  keys: {list(supervisor_data.keys())}")
    
    if 'update' in supervisor_data:
        update = supervisor_data['update']
        print(f"  update: {update}")
        if 'final_answer' in update:
            print(f"  final_answer: {update['final_answer']}")
            return update['final_answer']
        if 'messages' in update:
            print(f"  update messages: {update['messages']}")
    
    if 'messages' in supervisor_data:
        print(f"  messages: {supervisor_data['messages']}")
        for i, msg in enumerate(supervisor_data['messages']):
            print(f"    消息{i}: {type(msg)}, content: {getattr(msg, 'content', '无')}")
    
    return ""
