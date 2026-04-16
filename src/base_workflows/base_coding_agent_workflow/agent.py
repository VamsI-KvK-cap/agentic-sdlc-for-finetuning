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

    Provides a reusable workflow for multi-step code generation:
    setup → planning → validation → optional reading → file processing.

    Subclasses are responsible for implementing language-specific logic
    (planner, coder, reviewer, static analysis), while common orchestration
    logic is handled here.

    CONCEPT: This class builds two layered graphs:
    1. File subgraph → handles per-file generation + review loop.
    2. Main graph → orchestrates full task execution across files.

    Attributes:
        config (dict): Runtime configuration for the agent.
        _file_subgraph: Cached compiled file-level workflow.
        _main_graph: Cached compiled main workflow.
    """

    def __init__(self, config: dict):
        """
        Initialize the agent with configuration.

        Args:
            config (dict): Arbitrary configuration used by nodes.
        """
        self.config = config
        self._file_subgraph = None
        self._main_graph = None

    # -- Abstract methods - MUST be overridden -----------

    @abstractmethod
    def planner_node(self, state: BaseAgentState) -> BaseAgentState:
        """
        Generate a high-level execution plan from the task.

        CONCEPT: This is the "thinking" phase where the agent decides:
        - What files to create/update
        - What steps are required

        Args:
            state (BaseAgentState): Current workflow state.

        Returns:
            BaseAgentState: Updated state with plan.
        """
        pass

    @abstractmethod
    def coder_node(self, state: BaseFileAgentState) -> BaseFileAgentState:
        """
        Generate or update code for a single file.

        CONCEPT: This runs inside the file subgraph and is responsible
        for producing the actual implementation.

        Args:
            state (BaseFileAgentState): File-level state.

        Returns:
            BaseFileAgentState: Updated state with generated code.
        """
        pass

    @abstractmethod
    def reviewer_node(self, state: BaseFileAgentState) -> BaseFileAgentState:
        """
        Review generated code and decide whether it is acceptable.

        CONCEPT: Acts as a quality gate before writing to disk.
        Can request revisions, approve, or abort.

        Args:
            state (BaseFileAgentState): File-level state.

        Returns:
            BaseFileAgentState: Updated state with review feedback.
        """

    @abstractmethod
    def static_check_node(self, state: BaseFileAgentState) -> BaseFileAgentState:
        """
        Run static analysis tools on generated code.

        CONCEPT: This simulates tools like linters or compilers
        (e.g., ruff, eslint, golangci-lint).

        Args:
            state (BaseFileAgentState): File-level state.

        Returns:
            BaseFileAgentState: Updated state with static check results.
        """
        pass

    # -- Overridable methods - CAN be overridden -------------

    def setup_node(self, state: BaseAgentState) -> BaseAgentState:
        """
        Prepare initial execution context.

        CONCEPT: Handles things like initializing working directory,
        execution metadata, and shared state.

        Args:
            state (BaseAgentState): Current workflow state.

        Returns:
            BaseAgentState: Updated state.
        """
        return setup_node(state)  # use generic by default

    def reader_node(self, state: BaseAgentState) -> BaseAgentState:
        """
        Read existing files from disk into state.

        CONCEPT: Enables incremental updates by giving the agent
        awareness of current project contents.

        Args:
            state (BaseAgentState): Current workflow state.

        Returns:
            BaseAgentState: Updated state with file contents.
        """
        return reader_node(state)  # use generic by default
        
    def writer_node(self, state: BaseFileAgentState) -> BaseFileAgentState:
        """
        Persist generated code to disk.

        CONCEPT: This is the only node that performs file writes,
        ensuring all changes go through review first.

        Args:
            state (BaseFileAgentState): File-level state.

        Returns:
            BaseFileAgentState: Updated state after write.
        """
        return writer_node(state)  # use generic by default
    
    def file_validator_node(self, state: BaseAgentState) -> BaseAgentState:
        """
        Validate planned file operations.

        CONCEPT: Ensures file paths, names, and structure are valid
        before proceeding to execution.

        Args:
            state (BaseAgentState): Current workflow state.

        Returns:
            BaseAgentState: Validated state.
        """
        return file_validator_node(state)  # use generic by default
    
    def should_read(self, state: BaseAgentState) -> str:
        """
        Decide whether existing files need to be read.

        CONCEPT: Conditional branching point in the graph:
        - "reader" → load existing files
        - "process_files" → skip directly to execution

        Args:
            state (BaseAgentState): Current workflow state.

        Returns:
            str: Next node key.
        """
        return should_read(state)  # use generic by default

    def review_decision(self, state: BaseFileAgentState) -> str:
        """
        Decide outcome of code review.

        CONCEPT: Controls loop between coder and reviewer:
        - "approve" → proceed to writer
        - "revise" → go back to coder
        - "abort" → stop but still write output

        Args:
            state (BaseFileAgentState): File-level state.

        Returns:
            str: Next node key.
        """
        return review_decision(state)  # use generic by default

    def static_check_decision(self, state: BaseFileAgentState) -> str:
        """
        Decide outcome of static analysis.

        CONCEPT: Determines whether code passes validation:
        - "pass" → finish
        - "retry" → re-run coder
        - "abort" → stop execution

        Args:
            state (BaseFileAgentState): File-level state.

        Returns:
            str: Next node key.
        """
        return static_check_decision(state)  # use generic by default
    
    # --- Graph builders ------------------------------------------

    def build_file_subgraph(self):
        """
        Build and cache the file-level workflow graph.

        CONCEPT: This graph operates on a single file and includes:
        coder → reviewer → (loop or write) → static check → (loop or end)

        The review and static check steps introduce feedback loops
        for iterative improvement.

        Returns:
            Compiled graph for file-level execution.
        """
        if self._file_subgraph:
            return self._file_subgraph  # reuse cached graph
        
        workflow = StateGraph(BaseFileAgentState)

        # Register nodes for file processing
        workflow.add_node("coder", self.coder_node)
        workflow.add_node("reviewer", self.reviewer_node)
        workflow.add_node("writer", self.writer_node)
        workflow.add_node("static_check", self.static_check_node)

        # Define execution flow
        workflow.set_entry_point("coder")
        workflow.add_edge("coder", "reviewer")

        # Conditional loop: reviewer decides next step
        workflow.add_conditional_edges(
            "reviewer", self.review_decision,
            {"approve": "writer", "abort": "writer", "revise": "coder"}
        )

        workflow.add_edge("writer", "static_check")

        # Conditional loop: static analysis feedback
        workflow.add_conditional_edges(
            "static_check", self.static_check_decision,
            {"pass": END, "abort": END, "retry": "coder"}
        )

        # Compile and cache
        self._file_subgraph = workflow.compile()
        return self._file_subgraph        


    def build_main_graph(self):
        """
        Build and cache the main execution workflow.

        CONCEPT: This graph orchestrates the full lifecycle:
        setup → structure → planning → validation → optional read → file processing

        It integrates the file subgraph for handling individual files.

        Returns:
            Compiled graph for full task execution.
        """
        if self._main_graph:
            return self._main_graph  # reuse cached graph

        # Build file-level subgraph and wrap it into a node
        file_subgraph = self.build_file_subgraph()
        self.process_files_node = make_process_files_node(file_subgraph)

        workflow = StateGraph(BaseAgentState)

        # Register main workflow nodes
        workflow.add_node("setup", self.setup_node)
        workflow.add_node("file_structure", file_structure_node)
        workflow.add_node(
            "planner",
            self.planner_node,
            retry_policy=RetryPolicy(max_attempts=3)  # retry planning if it fails
        )
        workflow.add_node("file_validator", self.file_validator_node)
        workflow.add_node("reader", self.reader_node)
        workflow.add_node("process_files", self.process_files_node)

        # Define execution flow
        workflow.set_entry_point("setup")
        workflow.add_edge("setup", "file_structure")
        workflow.add_edge("file_structure", "planner")
        workflow.add_edge("planner", "file_validator")

        # Conditional branching: read existing files or proceed
        workflow.add_conditional_edges(
            "file_validator", self.should_read,
            {"reader": "reader", "process_files": "process_files"}
        )

        workflow.add_edge("reader", "process_files")
        workflow.add_edge("process_files", END)

        # Compile and cache
        self._main_graph = workflow.compile()
        return self._main_graph


    def run(self, task: str, work_dir: str, execution_id: int = None) -> BaseAgentState:
        """
        Execute the full agent workflow for a given task.

        CONCEPT: This is the entry point that initializes state and
        invokes the compiled graph. The graph handles all orchestration.

        Args:
            task (str): High-level instruction for the agent.
            work_dir (str): Directory where files will be read/written.
            execution_id (int, optional): Identifier for tracking execution.

        Returns:
            BaseAgentState: Final state after workflow completes.
        """
        # Build (or reuse) compiled workflow
        graph = self.build_main_graph()

        # Limit recursion to prevent infinite loops in retry cycles
        config = {"recursion_limit": 50}

        # Invoke graph with initial state
        return graph.invoke(
            {
                "task": task,
                "execution_id": execution_id,  # used by setup_node
                "work_dir": work_dir,          # used by setup_node
                "file_structure": "",
                "existing_files": {},
                "retry_count": {},
            },
            config=config
        )