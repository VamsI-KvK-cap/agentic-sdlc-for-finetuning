import os
from langchain_openai import ChatOpenAI
from src.config.logging_config import logger
from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("BASE_URL")
MODEL = os.getenv("MODEL")
API_KEY = os.getenv("OPENAI_API_KEY")

# logger.info(f"LLM CONFIG: \nBASE_URL : {BASE_URL} \nMODEL : {MODEL}")
# llm = ChatOpenAI(
#     base_url="http://localhost:8080/v1",
#     # model="Qwen2.5-7B-Instruct.Q4_0.gguf",
#     model="Qwen2.5-Coder-7B-Instruct.Q4_0.gguf",
#     api_key="not_needed", # API_KEY 
#     # callbacks=[SimpleLogger()]
# )

llm= ChatOpenAI(
    base_url=BASE_URL,
    model=MODEL,
    api_key=API_KEY, # API_KEY 
    # callbacks=[SimpleLogger()]
)

from langchain_google_genai import ChatGoogleGenerativeAI

lllm_disabled = ChatGoogleGenerativeAI(
    # model="gemini-3.1-pro-preview",
    model="gemini-2.5-flash",
    temperature=0.2,  # Gemini 3.0+ defaults to 1.0
    # max_tokens=None,
    # timeout=None,
    # max_retries=2,
    # other params...
)

logger.info(f"LLM CONFIG: {llm}")
