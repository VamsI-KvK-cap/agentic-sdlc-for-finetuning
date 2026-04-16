# Module docstring explaining the purpose of this module
"""
LSP Tools Module.

This module provides Language Server Protocol (LSP) utilities for coding agents.
It enables interaction with language servers to perform code intelligence operations
such as finding definitions, references, and symbols in source code files.

The module supports:
- Symbol definition lookup
- Symbol reference finding
- File symbol enumeration
- Integration with LangChain tool framework for agent use

It uses a global LSP client instance that must be initialized with a working directory
before use.
"""

# Import re module for regular expressions (not used in this version)
import re

# Import Path from pathlib for file path operations
from pathlib import Path

# Import tool decorator from langchain_core for creating tools
from langchain_core.tools import tool

# Import LSPClient from local lsp_client module
from .lsp_client import LSPClient

# Import _safe_path utility from local tools module
from .tools import _safe_path

# Global LSP client instance — initialized once per session
lsp_client: LSPClient | None = None

def init_lsp(working_dir: str) -> None:
    # Function docstring
    """
    Initialize the global LSP client with a working directory.

    This function sets up the Language Server Protocol client for the specified
    working directory. The client is stored globally and used by all LSP tools.
    Must be called before using any LSP functionality.

    Args:
        working_dir (str): The root directory path for the LSP client.
            Should be an absolute path to the project root.

    Returns:
        None: This function does not return a value.

    Raises:
        Any exceptions raised by LSPClient initialization.

    Example:
        >>> init_lsp("/path/to/project")
        >>> # LSP client is now ready for use
    """
    # Declare global variable to modify it
    global lsp_client
    # Initialize the LSP client with the working directory
    lsp_client = LSPClient(working_dir)

def _uri_to_path(uri: str) -> str:
    # Function docstring
    """
    Convert a file URI to a local file system path.

    This helper function strips the 'file://' prefix from URIs to obtain
    the corresponding file system path.

    Args:
        uri (str): The URI string, typically starting with 'file://'.

    Returns:
        str: The file system path without the URI prefix.

    Example:
        >>> path = _uri_to_path("file:///home/user/file.py")
        >>> print(path)  # "/home/user/file.py"
    """
    # Remove the 'file://' prefix from the URI to get the path
    return uri.replace("file://", "")

def _find_symbol_position(file_path: str, symbol_name: str) -> tuple[int, int] | None:
    # Function docstring
    """
    Find the line and character position of a symbol in a file.

    This function searches for the first occurrence of a symbol name in a file
    and returns its position as (line, character) coordinates. Line numbers are
    0-based, character positions are 0-based.

    Args:
        file_path (str): Path to the file to search. Can be relative or absolute.
        symbol_name (str): The symbol name to find in the file.

    Returns:
        tuple[int, int] | None: A tuple of (line_number, character_position) if found,
            or None if the symbol is not found. Line numbers start from 0.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If there are issues reading the file.

    Example:
        >>> pos = _find_symbol_position("example.py", "my_function")
        >>> if pos:
        ...     print(f"Found at line {pos[0]}, column {pos[1]}")
    """
    # Resolve to absolute path before opening
    if not Path(file_path).is_absolute():
        # Convert relative path to absolute using working directory
        file_path = str((Path(lsp_client.working_dir) / file_path).resolve())

    # Open the file and search for the symbol
    with open(file_path, "r") as f:
        # Iterate through each line with line numbers
        for line_no, line in enumerate(f):
            # Find the symbol in the current line
            col = line.find(symbol_name)
            # If found, return the position
            if col != -1:
                return (line_no, col)
    # Return None if symbol not found
    return None

def make_lsp_tools(working_dir: str) -> list:
    # Function docstring
    """
    Create pre-configured LSP tools bound to a specific working directory.

    This factory function creates LangChain tool instances that are pre-bound to a
    working directory, preventing the LLM from accidentally modifying the intended
    repository path. The tools provide LSP operations that agents can use during
    their planning and review loops.

    Args:
        working_dir (str): The repository directory path to bind the tools to.
            All LSP operations will be executed in this directory.

    Returns:
        list: A list of LangChain tool objects that can be used by agents.
            Includes tools for finding definitions, references, and file symbols.

    Example:
        >>> tools = make_lsp_tools("/path/to/repo")
        >>> # tools can now be passed to LangChain agents
    """
    # Define inner helper function to resolve paths safely
    def _resolve(path: str) -> str:
        # Resolve and sanitize the path using the safe_path utility
        return _safe_path(path, working_dir)

    # Create lsp_find_definition tool with working directory pre-bound
    @tool
    def lsp_find_definition(symbol_name: str, file_path: str) -> str:
        # Function docstring
        """
        Find where a symbol (function/class/variable) is defined.

        This tool uses the Language Server Protocol to locate the definition
        of a symbol in the codebase, helping agents understand code structure
        and dependencies.

        Args:
            symbol_name (str): The name of the symbol to find the definition for.
            file_path (str): Relative path to the file where the symbol is used.

        Returns:
            str: A string describing where the symbol is defined, or an error message
                if not found.
        """
        # Resolve and sanitize the file path
        safe = _resolve(file_path)
        # Find the position of the symbol in the file
        pos = _find_symbol_position(safe, symbol_name)
        # If symbol not found, return error message
        if not pos:
            return f"Symbol '{symbol_name}' not found in {file_path}"

        # Request definition from LSP client
        result = lsp_client.get_definition(safe, pos[0], pos[1])
        # Extract locations from the result
        locations = result.get("result", [])
        # If no locations found, return error message
        if not locations:
            return f"No definition found for '{symbol_name}'"

        # Get the first location (or the location if not a list)
        loc = locations[0] if isinstance(locations, list) else locations
        # Extract file path from URI
        path = loc["uri"].replace("file://", "")
        # Extract line number (1-based)
        line = loc["range"]["start"]["line"] + 1
        # Return formatted definition location
        return f"'{symbol_name}' defined in {path} at line {line}"

    # Create lsp_find_references tool with working directory pre-bound
    @tool
    def lsp_find_references(symbol_name: str, file_path: str) -> str:
        # Function docstring
        """
        Find all files and lines that use a symbol.

        This tool uses the Language Server Protocol to find all references
        to a symbol across the codebase, helping agents understand usage
        patterns and dependencies.

        Args:
            symbol_name (str): The name of the symbol to find references for.
            file_path (str): Relative path to a file where the symbol is used.

        Returns:
            str: A formatted string listing all references, or an error message
                if not found.
        """
        # Resolve and sanitize the file path
        safe = _resolve(file_path)
        # Find the position of the symbol in the file
        pos = _find_symbol_position(safe, symbol_name)
        # If symbol not found, return error message
        if not pos:
            return f"Symbol '{symbol_name}' not found in {file_path}"

        # Request references from LSP client
        result = lsp_client.get_references(safe, pos[0], pos[1])
        # Extract locations from the result
        locations = result.get("result", [])
        # If no locations found, return error message
        if not locations:
            return f"No references found for '{symbol_name}'"

        # Build list of reference strings
        refs = []
        # Iterate through each location
        for loc in locations:
            # Extract file path from URI
            path = loc["uri"].replace("file://", "")
            # Extract line number (1-based)
            line = loc["range"]["start"]["line"] + 1
            # Format as "path:line"
            refs.append(f"  {path}:{line}")

        # Return formatted list of references
        return f"'{symbol_name}' used in {len(refs)} places:\n" + "\n".join(refs)

    # Create lsp_get_file_symbols tool with working directory pre-bound
    @tool
    def lsp_get_file_symbols(file_path: str) -> str:
        # Function docstring
        """
        List all functions, classes, and methods defined in a file.

        This tool uses the Language Server Protocol to enumerate all symbols
        (functions, classes, variables, etc.) defined in a specific file,
        providing an overview of the file's structure.

        Args:
            file_path (str): Relative path to the file to analyze.

        Returns:
            str: A formatted string listing all symbols in the file, or an error
                message if no symbols found.
        """
        # Resolve and sanitize the file path
        safe = _resolve(file_path)   # Path is sanitized and resolved
        # Request symbols from LSP client
        result = lsp_client.get_symbols(safe)
        # Extract symbols from the result
        symbols = result.get("result", [])

        # If no symbols found, return error message
        if not symbols:
            return f"No symbols found in {file_path}"

        # Build output list
        output = []
        # Iterate through each symbol
        for sym in symbols:
            # Map symbol kind numbers to readable names
            kind_map = {1: "File", 5: "Class", 6: "Function", 12: "Variable"}
            # Get the kind name, default to "Symbol"
            kind = kind_map.get(sym.get("kind", 0), "Symbol")
            # Get the symbol name
            name = sym["name"]
            # Get the line number (1-based)
            line = sym["location"]["range"]["start"]["line"] + 1
            # Format as "[Kind] name — line X"
            output.append(f"  [{kind}] {name} — line {line}")

        # Return formatted list of symbols
        return f"Symbols in {file_path}:\n" + "\n".join(output)

    # Return list of all created tools
    return [lsp_find_definition, lsp_find_references, lsp_get_file_symbols]