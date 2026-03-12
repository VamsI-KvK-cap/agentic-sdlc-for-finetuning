from abc import ABC, abstractmethod
from langgraph.graph import StateGraph, END
from langgraph.types import RetryPolicy
from .state import BaseAgentState, BaseFileAgentState
from .nodes.reader import reader_node
from .nodes.writer import writer_node
from .nodes.setup import setup_node
from .nodes.file_structure import file_structure_node
from .nodes.file_validator import file_validator_node
from .nodes.process_files import make_process_files_node
from .decisions.review_decision import review_decision
from .decisions.should_read import should_read
from .decisions.static_check_decision import static_check_decision

class BaseCodingAgent(ABC):
    """
    Abstract base class for all coding agents.
    Subclasses must implement language-specific nodes and prompts.
    Generic noes (setup, writer, reader, process_files) are inherited as-is
    """

    def __init__(self, config: dict):
        self.config = config
        self._file_subgraph = None
        self._main_graph = None

    # -- Abstract methods - MUST be overridden -----------

    @abstractmethod
    def planner_node(self, state: BaseAgentState) -> BaseAgentState:
        """Language-specific planning logic."""
        pass

    @abstractmethod
    def coder_node(self, state: BaseFileAgentState) -> BaseFileAgentState:
        """Language-specific code revie logic."""
        pass

    @abstractmethod
    def reviewer_node(self, state: BaseFileAgentState) -> BaseFileAgentState:
        """Language-specific code review logic."""

    @abstractmethod
    def static_check_node(self, state: BaseFileAgentState) -> BaseFileAgentState:
        """Language-specific static analysis (ruff, eslint, golangci etc.)"""
        pass

    # -- Overridable methods - CAN be overridden -------------

    def setup_node(self, state: BaseAgentState) -> BaseAgentState:
        return setup_node(state)                # use generic by default

    def reader_node(self, state: BaseAgentState) -> BaseAgentState:
        return reader_node(state)               # use generic by default
        
    def writer_node(self, state: BaseFileAgentState) -> BaseFileAgentState:
        return writer_node(state)               # use generic by default
    
    # def process_files_node(self, state: BaseAgentState) -> BaseAgentState:
    #     return make_process_files_node(state)               # use generic by default

    def file_validator_node(self, state: BaseAgentState) -> BaseAgentState:
        return file_validator_node(state)      # use generic by default
    
    def should_read(self, state: BaseAgentState) -> str:
        return should_read(state)                   # use generic by default

    def review_decision(self, state: BaseFileAgentState) -> str:
        return review_decision(state)               # use generic by default

    def static_check_decision(self, state: BaseFileAgentState) -> str:
        return static_check_decision(state)         # use generic by default
    
    # --- Graph builders ------------------------------------------

    def build_file_subgraph(self):
        if self._file_subgraph:
            return self._file_subgraph          # cache it
        
        workflow = StateGraph(BaseFileAgentState)
        workflow.add_node("coder", self.coder_node)
        workflow.add_node("reviewer", self.reviewer_node)
        workflow.add_node("writer", self.writer_node)
        workflow.add_node("static_check", self.static_check_node)

        workflow.set_entry_point("coder")
        workflow.add_edge("coder", "reviewer")
        workflow.add_conditional_edges(
            "reviewer", self.review_decision,
            {"approve": "writer", "abort": "writer", "revise": "coder"}
        )
        workflow.add_edge("writer", "static_check")
        workflow.add_conditional_edges(
            "static_check", self.static_check_decision,
            {"pass": END, "abort": END, "retry": "coder"}
        )

        self._file_subgraph = workflow.compile()
        return self._file_subgraph        


    def build_main_graph(self):
        if self._main_graph:
            return self._main_graph                 # cache it

        file_subgraph = self.build_file_subgraph()
        self.process_files_node = make_process_files_node(file_subgraph)

        workflow = StateGraph(BaseAgentState)
        workflow.add_node("setup", self.setup_node)
        workflow.add_node("file_structure", file_structure_node)
        workflow.add_node("planner", self.planner_node, retry_policy=RetryPolicy(max_attempts=3))
        workflow.add_node("file_validator", self.file_validator_node)
        workflow.add_node("reader", self.reader_node)
        workflow.add_node("process_files", self.process_files_node)

        workflow.set_entry_point("setup")
        workflow.add_edge("setup", "file_structure")
        workflow.add_edge("file_structure", "planner")
        workflow.add_edge("planner", "file_validator")
        workflow.add_conditional_edges(
            "file_validator", self.should_read,
            {"reader": "reader", "process_files": "process_files"}
        )
        workflow.add_edge("reader", "process_files")
        workflow.add_edge("process_files", END)

        self._main_graph = workflow.compile()
        return self._main_graph


    def run(self, task:str, work_dir: str, execution_id: int = None) -> BaseAgentState:
    # def run(self, task:str, work_dir: str) -> BaseAgentState:
        graph = self.build_main_graph()
        config = {"recursion_limit": 50}
        return graph.invoke(
            {
                "task": task,                
                "execution_id": execution_id,  # currently setup_node is handling it
                "work_dir": work_dir,  # currently setup_node is handling it
                "file_structure": "",
                "existing_files": {},
                "retry_count": {},
            },
                config=config
            )