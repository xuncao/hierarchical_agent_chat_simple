import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 加载.env文件中的环境变量
load_dotenv()

# 检查必要的环境变量
required_env_vars = ["DEEPSEEK_API_KEY", "TAVILY_API_KEY", "DEEPSEEK_BASE_URL"]
for var in required_env_vars:
    if not os.environ.get(var):
        raise ValueError(f"Missing required environment variable: {var}")

llm = ChatOpenAI(
    model="deepseek-chat",  # DeepSeek对话模型
    temperature=0,
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url=os.environ["DEEPSEEK_BASE_URL"],
)