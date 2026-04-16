"""
Language Server Protocol client wrapper for coding agents.

This module implements a simple LSP client that communicates with pylsp via
stdin/stdout using the Language Server Protocol over JSON-RPC. It provides
methods to open files, resolve symbols, and query definitions, references,
and document symbols for Python source files.
"""

# Import subprocess for launching the pylsp process
import subprocess

# Import json for serializing LSP request and response payloads
import json

# Import threading for background response reading
import threading

# Import time for polling and startup delays
import time

# Import Path from pathlib for file path normalization
from pathlib import Path


class LSPClient:
    """
    Language Server Protocol client connection.

    The client launches pylsp as a subprocess, sends JSON-RPC requests and
    notifications, and reads responses asynchronously from stdout.
    """

    def __init__(self, working_dir: str):
        """
        Initialize the LSP client for the given working directory.

        Args:
            working_dir (str): The root directory for the project being analyzed.
                The client resolves relative file paths against this directory.
        """
        # Base working directory used by all path resolutions
        self.working_dir = working_dir
        # Incrementing JSON-RPC request identifier
        self.request_id = 0
        # Storage for responses received from the LSP server
        self.responses: dict[int, dict] = {}
        # Thread lock to synchronize access to responses
        self._lock = threading.Lock()

        # Start pylsp subprocess with stdin/stdout pipes
        self.process = subprocess.Popen(
            ["pylsp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        # Reader thread: responses arrive asynchronously on stdout
        self._reader = threading.Thread(target=self._read_responses, daemon=True)
        self._reader.start()

        # Initialize the LSP server session
        self._initialize()

    def _send(self, method: str, params: dict) -> int:
        """
        Send a JSON-RPC request to the LSP server.

        Args:
            method (str): The LSP method name to invoke.
            params (dict): The request parameters payload.

        Returns:
            int: The request identifier assigned to this JSON-RPC call.
        """
        # Increment request counter for unique JSON-RPC IDs
        self.request_id += 1
        rid = self.request_id
        # Build the JSON-RPC request body
        message = {
            "jsonrpc": "2.0",
            "id": rid,
            "method": method,
            "params": params
        }
        body = json.dumps(message)
        header = f"Content-Length: {len(body)}\r\n\r\n"
        # Write the request to pylsp stdin and flush immediately
        self.process.stdin.write((header + body).encode())
        self.process.stdin.flush()
        return rid

    def _notify(self, method: str, params: dict) -> None:
        """
        Send a JSON-RPC notification to the LSP server.

        Notifications do not expect a response.

        Args:
            method (str): The LSP notification method name.
            params (dict): The notification payload.
        """
        message = {"jsonrpc": "2.0", "method": method, "params": params}
        body = json.dumps(message)
        header = f"Content-Length: {len(body)}\r\n\r\n"
        self.process.stdin.write((header + body).encode())
        self.process.stdin.flush()

    def _read_responses(self) -> None:
        """
        Continuously read responses from the LSP server stdout.

        This method runs on a background thread and stores responses keyed by
        request id so callers can wait for the matching response.
        """
        while True:
            header = b""
            # Read header bytes until the end-of-header marker is found
            while b"\r\n\r\n" not in header:
                header += self.process.stdout.read(1)
            length = int(header.decode().split("Content-Length: ")[1].split("\r\n")[0])
            body = self.process.stdout.read(length)
            response = json.loads(body)
            if "id" in response:
                with self._lock:
                    self.responses[response["id"]] = response

    def _wait(self, request_id: int, timeout: int = 10) -> dict:
        """
        Wait for the response matching the specified request id.

        Args:
            request_id (int): The JSON-RPC request identifier to wait for.
            timeout (int): Maximum number of seconds to wait. Defaults to 10.

        Returns:
            dict: The response payload, or an empty dict if the timeout expires.
        """
        start = time.time()
        while time.time() - start < timeout:
            with self._lock:
                if request_id in self.responses:
                    return self.responses.pop(request_id)
            time.sleep(0.05)
        return {}

    def _initialize(self) -> None:
        """
        Initialize the LSP session and notify the server.

        Sends the initialize request and the initialized notification, then waits
        briefly for pylsp to index the project.
        """
        rid = self._send("initialize", {
            "rootUri": Path(self.working_dir).as_uri(),
            "capabilities": {}
        })
        self._wait(rid)
        self._notify("initialized", {})
        time.sleep(1)  # Allow pylsp time to index the project

    def _resolve_path(self, path: str) -> str:
        """
        Resolve a file path to an absolute path.

        Args:
            path (str): Relative or absolute file path.

        Returns:
            str: The resolved absolute file path.
        """
        p = Path(path)
        if not p.is_absolute():
            p = Path(self.working_dir) / p
        return str(p.resolve())

    def open_file(self, path: str) -> None:
        """
        Open a file in the LSP workspace.

        LSP servers generally require files to be opened before queries can be made.
        """
        path = self._resolve_path(path)
        uri = Path(path).as_uri()
        content = Path(path).read_text()
        self._notify("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": "python",
                "version": 1,
                "text": content
            }
        })
        time.sleep(0.3)  # Allow pylsp to parse the opened file

    def get_definition(self, path: str, line: int, character: int) -> dict:
        """
        Request the definition location for a symbol.

        Args:
            path (str): Path to the file containing the symbol.
            line (int): Line number of the symbol occurrence (0-based).
            character (int): Character offset of the symbol occurrence (0-based).

        Returns:
            dict: The LSP response payload containing definition locations.
        """
        path = self._resolve_path(path)
        uri = Path(path).as_uri()
        self.open_file(path)
        rid = self._send("textDocument/definition", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character}
        })
        return self._wait(rid)

    def get_references(self, path: str, line: int, character: int) -> dict:
        """
        Request references for a symbol in the workspace.

        Args:
            path (str): Path to the file containing the symbol.
            line (int): Line number of the symbol occurrence (0-based).
            character (int): Character offset of the symbol occurrence (0-based).

        Returns:
            dict: The LSP response payload containing reference locations.
        """
        path = self._resolve_path(path)
        uri = Path(path).as_uri()
        self.open_file(path)
        rid = self._send("textDocument/references", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
            "context": {"includeDeclaration": True}
        })
        return self._wait(rid)

    def get_symbols(self, path: str) -> dict:
        """
        Request document symbols for a file.

        Args:
            path (str): Path to the file to analyze.

        Returns:
            dict: The LSP response payload containing document symbols.
        """
        path = self._resolve_path(path)
        uri = Path(path).as_uri()
        self.open_file(path)
        rid = self._send("textDocument/documentSymbol", {
            "textDocument": {"uri": uri}
        })
        return self._wait(rid)

    def shutdown(self) -> None:
        """
        Shutdown the LSP server and terminate the subprocess.
        """
        self._send("shutdown", {})
        self._notify("exit", {})
        self.process.terminate()