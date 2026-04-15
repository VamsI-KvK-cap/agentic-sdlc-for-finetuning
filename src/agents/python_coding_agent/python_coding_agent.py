"""Minimal example harness for the Python coding agent.

This module demonstrates a tiny :class:`StateGraph` that formats the
``Python_Coding_Prompt`` and invokes a local LLM. It is intended for
experimentation and examples rather than production use.
"""

from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from .prompt.python_coding_agent_prompt import Python_Coding_Prompt
from typing import Dict
from typing_extensions import TypedDict

# Lightweight local LLM instance used for demonstration purposes only.
llm = ChatOpenAI(
        base_url="http://localhost:8080/v1",
        model="Qwen2.5-7B-Instruct.Q4_0.gguf",
        api_key="not_needed",
        # callbacks=[SimpleLogger()]
)


class OverAllState(TypedDict):
        """Typed shape for the minimal StateGraph used in this example.

        Attributes:
                task (str): The user's task/instruction.
                output (str): The agent's textual response.
        """

        task: str
        output: str  # the agent's textual response


def coding_assistance(state: OverAllState):
        """Format the prompt and call the configured LLM.

        Args:
                state (OverAllState): Input mapping containing the `task` key.

        Returns:
                dict: Mapping with the LLM output under the `output` key.
        """

        task = state["task"]
        prompt = Python_Coding_Prompt(task)
        messages = [SystemMessage(content=prompt.python_coding_agent_prompt)]
        response = llm.invoke(messages)

        return {"output": response.content}


build = StateGraph(OverAllState)
build.add_node("assistant", coding_assistance)

# Connect start -> assistant -> end
build.add_edge(START, "assistant")
build.add_edge("assistant", END)

graph = build.compile()

if __name__ == "__main__":
        # Example invocation that prints the assistant output.
        result = graph.invoke({"task": "Write a hello world program"})
        print(result)