import re
from pathlib import Path
from langchain_core.tools import tool
from .lsp_client import LSPClient

# Global LSP client — initialized once per session
lsp_client: LSPClient | None = None

def init_lsp(working_dir: str):
    global lsp_client
    lsp_client = LSPClient(working_dir)

def _uri_to_path(uri: str) -> str:
    return uri.replace("file://", "")

def _find_symbol_position(file_path: str, symbol_name: str) -> tuple[int, int] | None:
    """Find line/character of a symbol in a file."""
    # Resolve to absolute path before opening
    if not Path(file_path).is_absolute():
        file_path = str((Path(lsp_client.working_dir) / file_path).resolve())
        
    with open(file_path, "r") as f:
        for line_no, line in enumerate(f):
            col = line.find(symbol_name)
            if col != -1:
                return (line_no, col)
    return None

@tool
def lsp_find_definition(symbol_name: str, file_path: str) -> str:
    """Find where a symbol (function/class/variable) is defined."""
    pos = _find_symbol_position(file_path, symbol_name)
    if not pos:
        return f"Symbol '{symbol_name}' not found in {file_path}"

    result = lsp_client.get_definition(file_path, pos[0], pos[1])
    locations = result.get("result", [])

    if not locations:
        return f"No definition found for '{symbol_name}'"

    loc = locations[0] if isinstance(locations, list) else locations
    path = _uri_to_path(loc["uri"])
    line = loc["range"]["start"]["line"] + 1
    return f"'{symbol_name}' defined in {path} at line {line}"

@tool
def lsp_find_references(symbol_name: str, file_path: str) -> str:
    """Find all files and lines that use a symbol."""
    pos = _find_symbol_position(file_path, symbol_name)
    if not pos:
        return f"Symbol '{symbol_name}' not found in {file_path}"

    result = lsp_client.get_references(file_path, pos[0], pos[1])
    locations = result.get("result", [])

    if not locations:
        return f"No references found for '{symbol_name}'"

    refs = []
    for loc in locations:
        path = _uri_to_path(loc["uri"])
        line = loc["range"]["start"]["line"] + 1
        refs.append(f"  {path}:{line}")

    return f"'{symbol_name}' used in {len(refs)} places:\n" + "\n".join(refs)

@tool
def lsp_get_file_symbols(file_path: str) -> str:
    """List all functions, classes, and methods defined in a file."""
    result = lsp_client.get_symbols(file_path)
    symbols = result.get("result", [])

    if not symbols:
        return f"No symbols found in {file_path}"

    output = []
    for sym in symbols:
        kind_map = {1: "File", 5: "Class", 6: "Function", 12: "Variable"}
        kind = kind_map.get(sym.get("kind", 0), "Symbol")
        name = sym["name"]
        line = sym["location"]["range"]["start"]["line"] + 1
        output.append(f"  [{kind}] {name} — line {line}")

    return f"Symbols in {file_path}:\n" + "\n".join(output)