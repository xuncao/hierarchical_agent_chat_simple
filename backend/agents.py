from langgraph.prebuilt import create_react_agent
from tools import tavily_tool, scrape_webpages, write_document, edit_document, read_document, create_outline, python_repl_tool
from llm import llm

# 搜索
search_agent = create_react_agent(llm, tools=[tavily_tool])


# 爬虫
web_scraper_agent = create_react_agent(llm, tools=[scrape_webpages])

# 写文档
doc_writer_agent = create_react_agent(
    llm,
    tools=[write_document, edit_document, read_document],
    prompt=(
        "你可以根据记录员的大纲读取、撰写和编辑文档。"
        "无需提出后续问题。"
    ),
)

# 写大纲
note_taking_agent = create_react_agent(
    llm,
    tools=[create_outline, read_document],
    prompt=(
        "你可以读取文档并为文档撰写者创建大纲。"
        "无需提出后续问题。"
    ),
)

# 生成图表python代码
chart_generating_agent = create_react_agent(
    llm, tools=[read_document, python_repl_tool]
)