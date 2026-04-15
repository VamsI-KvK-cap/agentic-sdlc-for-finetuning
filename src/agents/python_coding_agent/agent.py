# src/agents/python_agent/agent.py
"""Python-specific Coding Agent wiring.

This module adapts the generic :class:`BaseCodingAgent` workflow to
Python by providing language-specific node implementations (planner,
coder, reviewer and static checks). The class methods forward the
workflow calls to node functions contained in ``nodes/``.
"""

from src.base_workflows.base_coding_agent_workflow.agent import BaseCodingAgent
from src.base_workflows.base_coding_agent_workflow.state import BaseAgentState, BaseFileAgentState
from .nodes.planner import planner_node
from .nodes.coder import coder_node
from .nodes.reviewer import reviewer_node
from .nodes.static_check import static_check_node


class PythonCodingAgent(BaseCodingAgent):
    """
    Python-specific coding agent.
    Uses ruff for static analysis, Python-specific prompts.
    Only overrides language-specific nodes.
    """

    def planner_node(self, state: BaseAgentState) -> BaseAgentState:
        """Invoke the Python planner node.

        Args:
            state (BaseAgentState): The shared agent state used to build
                the high-level plan.

        Returns:
            BaseAgentState: A (possibly partial) mapping containing the
            planned steps.
        """
        return planner_node(state)          # python-specific planner

    def coder_node(self, state: BaseFileAgentState) -> BaseFileAgentState:
        """Invoke the coder node for a single file.

        Args:
            state (BaseFileAgentState): File-scoped state used by the coder.

        Returns:
            BaseFileAgentState: Updated state including generation output.
        """
        return coder_node(state)            # python-specific coder

    def reviewer_node(self, state: BaseFileAgentState) -> BaseFileAgentState:
        """Run reviewer checks for a generated file.

        Args:
            state (BaseFileAgentState): File-scoped state containing
                the generated change and context needed for review.

        Returns:
            BaseFileAgentState: State delta containing reviewer output
                and updated retry counters.
        """
        return reviewer_node(state)         # python-specific reviewer

    def static_check_node(self, state: BaseFileAgentState) -> BaseFileAgentState:
        """Run language-specific static analysis (ruff).

        Args:
            state (BaseFileAgentState): File-scoped state. Expected to
                include a ``written_files`` list of paths to check.

        Returns:
            BaseFileAgentState: State delta containing static check
                results and any feedback.

        Raises:
            RuntimeError: If the static analysis tool cannot be executed
                (e.g. tool missing), the underlying subprocess error may
                be propagated by callers.
        """
        return static_check_node(state)     # ruff-specifics