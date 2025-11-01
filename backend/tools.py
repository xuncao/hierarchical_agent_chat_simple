from typing import Annotated, List
from langchain_community.document_loaders import WebBaseLoader
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Optional
from langchain_experimental.utilities import PythonREPL

tavily_tool = TavilySearch(max_results=5)

@tool
def scrape_webpages(urls: List[str]) -> str:
    """使用 requests 和 bs4 爬取指定网页，获取详细信息。"""
    loader = WebBaseLoader(urls)
    docs = loader.load()
    return "\n\n".join(
        [
            f'<Document name="{doc.metadata.get("title", "")}">\n{doc.page_content}\n</Document>'
            for doc in docs
        ]
    )

# 系统自动创建临时目录
_TEMP_DIRECTORY = TemporaryDirectory()
# 临时目录路径
WORKING_DIRECTORY = Path(_TEMP_DIRECTORY.name)

@tool
def create_outline(
    points: Annotated[List[str], "主要要点或章节列表。"],
    file_name: Annotated[str, "用于保存大纲的文件路径。"],
) -> Annotated[str, "保存的大纲文件路径。"]:
    """创建并保存大纲。"""
    with (WORKING_DIRECTORY / file_name).open("w") as file:
        for i, point in enumerate(points):
            file.write(f"{i + 1}. {point}\n")
    return f"大纲已保存至 {file_name}"

@tool
def read_document(
    file_name: Annotated[str, "待读取文档的文件路径。"],
    start: Annotated[Optional[int], "起始行，默认值为 0"] = None,
    end: Annotated[Optional[int], "结束行，默认值为 None"] = None,
) -> str:
    """读取指定文档。"""
    with (WORKING_DIRECTORY / file_name).open("r") as file:
        lines = file.readlines()
        if start is None:
            start = 0
        return "\n".join(lines[start:end])

@tool
def write_document(
    content: Annotated[str, "要写入文档的文本内容。"],
    file_name: Annotated[str, "用于保存文档的文件路径。"],
) -> Annotated[str, "保存的文档文件路径。"]:
    """创建并保存文本文档。"""
    with (WORKING_DIRECTORY / file_name).open("w") as file:
        file.write(content)
    return f"文档已保存至 {file_name}"

@tool
def edit_document(
    file_name: Annotated[str, "待编辑文档的路径。"],
    inserts: Annotated[
        Dict[int, str],
        "字典，键为行号（从 1 开始计数），值为要插入该行的文本。",
    ],
) -> Annotated[str, "编辑后的文档文件路径。"]:
    """通过在特定行号插入文本编辑文档。"""
    with (WORKING_DIRECTORY / file_name).open("r") as file:
        lines = file.readlines()
    sorted_inserts = sorted(inserts.items())
    for line_number, text in sorted_inserts:
        if 1 <= line_number <= len(lines) + 1:
            lines.insert(line_number - 1, text + "\n")
        else:
            return f"错误：行号 {line_number} 超出范围。"
    with (WORKING_DIRECTORY / file_name).open("w") as file:
        file.writelines(lines)
    return f"文档已编辑并保存至 {file_name}"

# 警告：此工具会在本地执行代码，若未进行沙箱隔离，可能存在安全风险
repl = PythonREPL()

@tool
def python_repl_tool(
    code: Annotated[str, "用于生成图表的 Python 代码。"],
):
    """使用此工具执行 Python 代码。若需查看某个值的输出，
    请使用 `print(...)` 打印该值。执行结果对用户可见。"""
    try:
        result = repl.run(code)
    except BaseException as e:
        return f"执行失败。错误信息：{repr(e)}"
    return f"执行成功：\n```python\n{code}\n```\n标准输出：{result}"