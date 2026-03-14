# from src.agents.python_coding_agent.agent import PythonCodingAgent
# # from src.agents.javascript_agent.agent import JavaScriptCodingAgent

# AGENTS = {
#     "python": PythonCodingAgent,
#     # "javascript": JavaScriptCodingAgent,
# }

# # def run(task: str, work_dir: str, language: str = "python", execution_id: int = 4):
# def run(task: str, language: str = "python"):    
#     agent_cls = AGENTS.get(language)
#     if not agent_cls:
#         raise ValueError(f"Unsupported language: {language}. Choose from {list(AGENTS.keys())}")

#     agent = agent_cls(config={})
#     return agent.run(task=task)
#     # return agent.run(task=task, work_dir=work_dir, execution_id=execution_id)

# if __name__ == "__main__":
#     # input_state = "Write a detailed FastAPI endpoint for CRUD ops for a llm application that can take user input in text of file format"
#     input_state = """As a store manager, I want to add a new product to the inventory so that I can track its availability and manage its stock levels.
# As a store manager, I want to remove a product from the inventory so that I can discontinue its sale and update its availability status.
# As a store manager, I want to edit the details of an existing product in the inventory so that I can update its information or correct any errors.
# """
#     run(task=input_state)
#     # run(task="Write fibonacci series", work_dir="output/1", language="python")