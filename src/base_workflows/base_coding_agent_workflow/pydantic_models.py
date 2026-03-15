from typing_extensions import List, Literal
from pydantic import BaseModel, Field


class FilePlan(BaseModel):
    # path: str = Field(description="This is an absolute path of file where work_dir is the parent directory.")
    path: str = Field(description="This is the relative path of a file.")
    action: Literal["create", "update"]
    reason: str
    instructions: str = Field(description="""
        Precise, self-contained implementation instructions for this specific file only.
        The coder will see ONLY this field + the file content — not the global task.
        Include: what to implement, key functions/classes, inputs/outputs, 
        dependencies to import from other planned files.
    """)

class Plan(BaseModel):
    summary: str
    files: List[FilePlan]

class CodeChange(BaseModel):
    # path: str = Field(description="This is an absolute path of file  where work_dir is the parent directory.")
    path: str = Field(description="This is the relative path of file.")
    action: Literal["create", "update"]
    content: str # full new content(safe v1 design)  | In v2, you can move to diff/patch mode.

class CodeOutput(BaseModel):
    summary: str
    changes: List[CodeChange]

class SingleFileOutput(BaseModel):
    summary:str
    change: CodeChange

class ReviewResult(BaseModel):
    status: Literal["approved", "needs_revision"]
    issues: List[str]
    suggestion: List[str]
    confidence: float = Field(description="The value must be between 0.0 - 1.0")
