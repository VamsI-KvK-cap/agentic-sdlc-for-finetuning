from langchain_core.prompts import ChatPromptTemplate  # Used to construct structured LLM prompts


"""
Planner Prompt Definition

This prompt is used by the planner node to generate a structured implementation plan.

Purpose:
    - Break down a high-level task into file-level instructions
    - Ensure each file has self-contained implementation details
    - Enforce structured JSON output compatible with Pydantic models

Design Goals:
    - Each file can be implemented independently
    - Maintain modular and clean architecture
    - Provide enough detail for downstream coder node

Prompt Structure:
    - System message → defines role and strict rules
    - User message → provides task + repository context
"""


planner_prompt = ChatPromptTemplate.from_messages([

    # ---------------- SYSTEM MESSAGE ----------------
    (
        "system",
        """
You are a senior Python software architect.

Your job is to analyze a task and produce a precise implementation plan — one entry 
per file. Each file entry must include self-contained implementation instructions 
detailed enough that a coder working on ONLY that file can complete it correctly 
without seeing the global task.

## Rules
- Prefer `update` over `create` if an existing file is the right home.
- Order by import dependency — dependencies first.
- Every new package needs an `__init__.py`.
- Use `snake_case` for new filenames.
- Per-file `instructions` must specify: functions/classes to implement, 
  their signatures, inputs/outputs, edge cases, and imports from other planned files.
- Do not bleed concerns across files — each file's instructions are self-contained.
- Return structured JSON only.
"""
    ),

    # ---------------- USER MESSAGE ----------------
    (
        "user",
        """
## Task
{task}

## Working Directory
{work_dir}

## Repository File Structure
{file_structure}

## Existing File Contents
{existing_files}

{format_instructions}
"""
    )
])