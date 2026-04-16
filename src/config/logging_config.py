"""Project-wide logging configuration.

This module configures a named logger (``Agentic_SDLC``) with a
rotating file handler and a console handler. It reads ``LOG_DIR`` from
the environment and ensures the directory exists.

There are no functions exported; consumers should import ``logger``.
"""

import logging
from logging.handlers import RotatingFileHandler
import os
from dotenv import load_dotenv

load_dotenv()

# Get the directory to store logs in. If not provided, fall back to a
# sensible default inside the project workspace.
LOG_DIR = os.getenv("LOG_DIR") or os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# Create a named logger for the application. Consumers should import
# this logger rather than instantiating new ones for consistency.
logger = logging.getLogger("Agentic_SDLC")
logger.setLevel(logging.DEBUG)  # default log level for detailed tracing

# File handler (with rotation) to limit disk usage in long runs.
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
file_handler.setLevel(logging.DEBUG)

# Console handler used during development and for container logs.
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Common formatter applied to both handlers.
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Attach handlers if they are not already attached (safe idempotent init).
if not logger.handlers:
	logger.addHandler(file_handler)
	logger.addHandler(console_handler)