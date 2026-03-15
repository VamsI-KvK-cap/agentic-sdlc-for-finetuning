# web/executions/source.py
#
# Service layer for brownfield source ingestion.
# Handles zip extraction and git cloning into output/{execution_id}/

import io
import os
import shutil
import subprocess
import zipfile
from fastapi import UploadFile

# Directories and files to strip after cloning/extracting.
# The agent only needs source code — not git metadata, IDE configs,
# dependency caches, or build artifacts.
_STRIP_DIRS = {
    ".git",           # git internals — history, hooks, pack files
    ".github",        # CI/CD workflows — not relevant to code changes
    "__pycache__",    # Python bytecode cache
    "node_modules",   # JS dependencies — huge, not source code
    ".next",          # Next.js build output
    "dist",           # build output
    "build",          # build output
    ".venv",          # Python virtual environment
    "venv",
    ".idea",          # JetBrains IDE config
    ".vscode",        # VS Code config
}

_STRIP_FILES = {
    ".DS_Store",      # macOS metadata
    "Thumbs.db",      # Windows thumbnail cache
}


# ── Zip extraction ─────────────────────────────────────────────────────────

async def extract_zip(upload: UploadFile, work_dir: str) -> int:
    """
    Extract an uploaded zip file into work_dir, then strip noise directories.

    Security: validates each member path against directory traversal attacks.
    Cleanup: removes .git/, node_modules/, __pycache__/ etc after extraction.

    Returns:
        int: Number of source files extracted (after cleanup).

    Raises:
        ValueError: If not a valid zip, empty, or contains path traversal.
        RuntimeError: If extraction fails due to a system error.
    """
    raw = await upload.read()

    if not raw:
        raise ValueError("Uploaded file is empty")

    if not zipfile.is_zipfile(io.BytesIO(raw)):
        raise ValueError("Uploaded file is not a valid zip archive")

    extracted = 0

    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
            members = zf.infolist()

            if not members:
                raise ValueError("Zip archive contains no files")

            for member in members:
                if member.filename.endswith("/"):
                    continue

                safe_name = os.path.normpath(member.filename).lstrip(os.sep)
                target_path = os.path.realpath(os.path.join(work_dir, safe_name))
                real_work_dir = os.path.realpath(work_dir)

                if not target_path.startswith(real_work_dir + os.sep):
                    raise ValueError(f"Zip contains unsafe path: {member.filename}")

                os.makedirs(os.path.dirname(target_path), exist_ok=True)

                with zf.open(member) as src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)

                extracted += 1

    except zipfile.BadZipFile as e:
        raise ValueError(f"Corrupted zip archive: {e}")
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Extraction failed: {e}") from e

    _flatten_single_root(work_dir)
    _strip_noise(work_dir)         # ← remove .git, node_modules etc

    return _count_files(work_dir)  # return count after cleanup


# ── Git cloning ────────────────────────────────────────────────────────────

def clone_git(git_url: str, work_dir: str) -> None:
    """
    Shallow-clone a public Git repository into work_dir, then strip .git/.

    --depth=1 fetches only the latest commit — no history needed.
    After cloning, .git/ and other noise directories are removed so
    the agent's planner only sees clean source files.

    Raises:
        ValueError: If URL is not HTTPS or repo not accessible.
        RuntimeError: If git not installed or clone fails.
    """
    if not git_url.startswith(("https://", "http://")):
        raise ValueError(
            "Only HTTPS Git URLs are supported "
            "(e.g. https://github.com/user/repo)"
        )

    if not shutil.which("git"):
        raise RuntimeError(
            "git is not installed in this environment. "
            "Add 'git' to your Dockerfile."
        )

    try:
        result = subprocess.run(
            [
                "git", "clone",
                "--depth=1",
                "--single-branch",
                git_url,
                work_dir,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Git clone timed out after 120 seconds.")
    except FileNotFoundError:
        raise RuntimeError("git binary not found — install git in your environment")

    if result.returncode != 0:
        err = result.stderr.strip()
        if "Repository not found" in err or "not found" in err.lower():
            raise ValueError(f"Repository not found or not accessible: {git_url}")
        if "Authentication failed" in err:
            raise ValueError("Authentication failed — only public repositories are supported")
        raise RuntimeError(f"Git clone failed: {err}")

    _flatten_single_root(work_dir)
    _strip_noise(work_dir)         # ← removes .git/, node_modules/ etc


# ── Helpers ────────────────────────────────────────────────────────────────

def _flatten_single_root(work_dir: str) -> None:
    """
    If work_dir contains exactly one subdirectory and no files,
    move its contents up into work_dir.

    Handles GitHub's default zip structure: repo-main/src/... → src/...
    """
    entries = os.listdir(work_dir)
    if len(entries) != 1:
        return
    single = os.path.join(work_dir, entries[0])
    if not os.path.isdir(single):
        return
    for item in os.listdir(single):
        shutil.move(os.path.join(single, item), os.path.join(work_dir, item))
    os.rmdir(single)


def _strip_noise(work_dir: str) -> None:
    """
    Recursively remove directories and files that are irrelevant to
    the agent's planning (git metadata, caches, build artifacts, IDE configs).

    CONCEPT: We walk bottom-up (topdown=False) so that when we delete
    a parent directory like node_modules/, we don't try to recurse into
    its children — they're already gone.
    """
    for root, dirs, files in os.walk(work_dir, topdown=False):

        # Remove noise files
        for filename in files:
            if filename in _STRIP_FILES:
                os.remove(os.path.join(root, filename))

        # Remove noise directories
        for dirname in dirs:
            if dirname in _STRIP_DIRS:
                full_path = os.path.join(root, dirname)
                shutil.rmtree(full_path, ignore_errors=True)


def _count_files(work_dir: str) -> int:
    """Count all files remaining in work_dir after cleanup."""
    count = 0
    for _, _, files in os.walk(work_dir):
        count += len(files)
    return count