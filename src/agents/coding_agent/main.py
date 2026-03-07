import asyncio
from langchain_core.messages import HumanMessage
from .graph import build_graph
from .lsp_tools import init_lsp, lsp_client
import src.agents.coding_agent.lsp_tools  as lsp_tools# import module, not just the variable

async def run_agent(request: str, working_dir: str):
    init_lsp(working_dir)
    app = build_graph(working_dir)
    try:
        result = await app.ainvoke({
            "messages": [HumanMessage(content=request)],
            "working_dir": working_dir,
            "plan": None,
            "file_changes": [],
            "review_status": "pending",
            "review_feedback": "",
            "revision_count": 0
        })

        print("=== PLAN ===")
        print(result["plan"])
        print("\n=== REVIEW STATUS ===")
        print(result["review_status"])
        print(result["review_feedback"])

    finally:
        # Access via module so you get the updated reference, not the None snapshot
        """use lsp_tools.lsp_client instead of lsp_client — when you do from lsp_tools import lsp_client you get a snapshot of None at import time.
        Accessing it via the module always gives you the current value after init_lsp() has set it."""
        if lsp_tools.lsp_client is not None:
            lsp_tools.lsp_client.shutdown()
        

asyncio.run(run_agent(
    # request="Add input validation to the login function in auth/login.py",
    request="List all functions in llm_endpoint.py",
    working_dir="/home/wahaj/study/agentic-sdlc/output/3"
))