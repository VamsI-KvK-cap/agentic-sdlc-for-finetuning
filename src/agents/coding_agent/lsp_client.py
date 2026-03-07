import subprocess
import json
import threading
import time
from pathlib import Path

class LSPClient:
    def __init__(self, working_dir: str):
        self.working_dir = working_dir
        self.request_id = 0
        self.responses = {}
        self._lock = threading.Lock()

        # Start pylsp as subprocess
        self.process = subprocess.Popen(
            ["pylsp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        # Reader thread — LSP responses come async
        self._reader = threading.Thread(target=self._read_responses, daemon=True)
        self._reader.start()

        self._initialize()

    def _send(self, method: str, params: dict) -> int:
        self.request_id += 1
        rid = self.request_id
        message = {
            "jsonrpc": "2.0",
            "id": rid,
            "method": method,
            "params": params
        }
        body = json.dumps(message)
        header = f"Content-Length: {len(body)}\r\n\r\n"
        self.process.stdin.write((header + body).encode())
        self.process.stdin.flush()
        return rid

    def _notify(self, method: str, params: dict):
        """Send notification (no response expected)."""
        message = {"jsonrpc": "2.0", "method": method, "params": params}
        body = json.dumps(message)
        header = f"Content-Length: {len(body)}\r\n\r\n"
        self.process.stdin.write((header + body).encode())
        self.process.stdin.flush()

    def _read_responses(self):
        """Background thread reading LSP responses."""
        while True:
            header = b""
            while b"\r\n\r\n" not in header:
                header += self.process.stdout.read(1)
            length = int(header.decode().split("Content-Length: ")[1].split("\r\n")[0])
            body = self.process.stdout.read(length)
            response = json.loads(body)
            if "id" in response:
                with self._lock:
                    self.responses[response["id"]] = response

    def _wait(self, request_id: int, timeout=10) -> dict:
        """Block until response arrives."""
        start = time.time()
        while time.time() - start < timeout:
            with self._lock:
                if request_id in self.responses:
                    return self.responses.pop(request_id)
            time.sleep(0.05)
        return {}

    def _initialize(self):
        rid = self._send("initialize", {
            "rootUri": Path(self.working_dir).as_uri(),
            "capabilities": {}
        })
        self._wait(rid)
        self._notify("initialized", {})
        time.sleep(1)  # Let pylsp index the project

    def _resolve_path(self, path: str) -> str:
        """Always convert to absolute path."""
        p = Path(path)
        if not p.is_absolute():
            p = Path(self.working_dir) / p
        return str(p.resolve())

    def open_file(self, path: str):
        """LSP needs files 'opened' before querying them."""
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
        time.sleep(0.3)  # Let pylsp parse the file

    def get_definition(self, path: str, line: int, character: int) -> dict:
        """Find where a symbol is defined."""
        path = self._resolve_path(path)
        uri = Path(path).as_uri()
        self.open_file(path)
        rid = self._send("textDocument/definition", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character}
        })
        return self._wait(rid)

    def get_references(self, path: str, line: int, character: int) -> dict:
        """Find all usages of a symbol."""
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
        """Get all symbols (functions, classes) in a file."""
        path = self._resolve_path(path)
        uri = Path(path).as_uri()
        self.open_file(path)
        rid = self._send("textDocument/documentSymbol", {
            "textDocument": {"uri": uri}
        })
        return self._wait(rid)

    def shutdown(self):
        self._send("shutdown", {})
        self._notify("exit", {})
        self.process.terminate()