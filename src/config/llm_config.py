"""LLM configuration helpers.

This module centralises construction of LLM client instances using
environment variables. Tests and local development can monkeypatch
environment values to control which backend used by the agents.
"""

import os
from langchain_openai import ChatOpenAI
from src.config.logging_config import logger
from dotenv import load_dotenv

load_dotenv()

# Read configuration from the environment. Keep these values simple so
# orchestration layers (docker-compose / k8s) can inject them.
BASE_URL = os.getenv("BASE_URL")
MODEL = os.getenv("MODEL")
API_KEY = os.getenv("OPENAI_API_KEY")


# Primary LLM client used by the agents. In production prefer wiring
# through a dedicated config management approach. This is intentionally
# simple so the rest of the codebase can import `llm` directly.
llm = ChatOpenAI(
    base_url=BASE_URL,
    model=MODEL,
    api_key=API_KEY,
)


# An example alternative client that is currently disabled in most
# environments. Keep this around for exploratory work but don't rely on it.
from langchain_google_genai import ChatGoogleGenerativeAI

lllm_disabled = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.2,
)

logger.info(f"LLM CONFIG: {llm}")