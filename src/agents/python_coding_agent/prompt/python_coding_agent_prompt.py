class Python_Coding_Prompt:
    """
    Prompt builder class for generating Python code using an LLM.

    This class encapsulates a reusable prompt template that instructs
    the model to generate Python code along with the corresponding filename.

    Attributes:
        task (str):
            The user-provided task description.

        python_coding_agent_prompt (str):
            Fully formatted prompt string containing instructions
            and the injected task.

    Behavior:
        - Stores the task during initialization
        - Constructs a prompt string using f-string interpolation
        - Provides a consistent format for LLM code generation

    Notes:
        - Designed for simple code generation (single-file use case)
        - Output format is fixed (Filename + Code)
        - Could be extended to structured output (JSON/Pydantic) in future
    """

    def __init__(self, task):
        """
        Initialize the Python_Coding_Prompt instance.

        Parameters:
            task (str):
                Description of the coding task to be performed.

        Behavior:
            - Saves the task to instance variable
            - Constructs the prompt string dynamically using the task
        """

        # Store user-provided task
        self.task = task

        # Build prompt string with embedded task
        self.python_coding_agent_prompt = f"""You are senior python developer. 
    Based on the given task you need to generate the code and the python filename for which the code has been generated.
    
    Task: {task}

    Generate the output in below format:
    Filename:
    Code:
    """