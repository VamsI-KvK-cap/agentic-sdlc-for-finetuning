# web/worker/celery_app.py
#
# Creates and configures the Celery application instance.
#
# CONCEPT: This file is the equivalent of FastAPI's `app = FastAPI(...)`.
# It defines HOW Celery behaves — broker, backend, serialisation, retries.
# It does NOT define what tasks do — that lives in tasks.py.
#
# Import pattern used everywhere:
#   from web.worker.celery_app import celery_app
#
# Start a worker from project root:
#   celery -A web.worker.celery_app worker --loglevel=info

import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# ── Broker and Result Backend ──────────────────────────────────────────────
#
# CONCEPT: Broker vs Result Backend — two different Redis roles:
#
#   BROKER  = the post office. FastAPI drops a message (task + args) into
#             Redis. The worker picks it up. One-way delivery queue.
#             Redis key pattern: celery (the default queue name)
#
#   BACKEND = the filing cabinet. After a task finishes, Celery stores
#             the result (success/failure/return value) back in Redis.
#             Lets you query task state from outside the worker via:
#             AsyncResult(task_id).state → "SUCCESS" | "FAILURE" | "PENDING"
#
#   We use the same Redis instance for both (different key namespaces).
#   In high-scale production you'd split them, but for our use case
#   one Redis is clean and sufficient.

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
#                                                            ^^^
#                                   Redis database index 0 (out of 16).
#                                   Using /0 for broker and /1 for backend
#                                   is a common pattern to keep keys separate,
#                                   but /0 for both works fine at our scale.

# ── Create the Celery instance ────────────────────────────────────────────
#
# First argument is the module name — used to auto-generate task names.
# Our tasks will be named: "web.worker.tasks.run_agent_task"
# This full dotted path is what gets serialised into the Redis message.

celery_app = Celery(
    "agentic_sdlc",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# ── Configuration ─────────────────────────────────────────────────────────
#
# CONCEPT: celery_app.conf.update() is the standard way to configure Celery.
# All config keys are documented at: https://docs.celeryq.dev/en/stable/userguide/configuration.html

celery_app.conf.update(

    # ── Serialisation ─────────────────────────────────────────────────────
    # CONCEPT: When Celery sends a task to Redis it must serialise the
    # function arguments into bytes. JSON is the safest choice:
    #   - Human readable (you can inspect Redis messages with redis-cli)
    #   - No security issues (pickle can execute arbitrary code on deserialise)
    #   - Sufficient for our args: execution_id (int), agent_name (str), task (str)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],            # reject any non-JSON messages (security)

    # ── Timezone ──────────────────────────────────────────────────────────
    timezone="UTC",
    enable_utc=True,

    # ── Task acknowledgement ──────────────────────────────────────────────
    # CONCEPT: "ack" = acknowledgement. When does Celery tell Redis
    # "I've received and am processing this task"?
    #
    # task_acks_late=True means: acknowledge AFTER the task completes,
    # not when it's picked up. This is safer — if the worker crashes
    # mid-execution, Redis still has the message and another worker
    # can pick it up.
    #
    # Default (acks_late=False) acknowledges on pickup — if the worker
    # crashes, the task is lost. Not acceptable for long agent runs.
    task_acks_late=True,

    # ── Worker prefetch ───────────────────────────────────────────────────
    # CONCEPT: prefetch_multiplier controls how many tasks a worker
    # reserves in advance from the queue per worker process.
    #
    # Default is 4 — the worker grabs 4 tasks at once even if it can
    # only run 1. This starves other workers and causes uneven load.
    #
    # Setting to 1 means: fetch one task, process it, then fetch the next.
    # This is the correct setting for long-running tasks like agent execution.
    worker_prefetch_multiplier=1,

    # ── Result expiry ─────────────────────────────────────────────────────
    # CONCEPT: Task results are stored in Redis. Without an expiry,
    # they accumulate forever. 24 hours is sufficient — we persist
    # the real execution state in PostgreSQL, so Redis results are
    # just a short-term status cache.
    result_expires=86400,               # 86400 seconds = 24 hours

    # ── Task routes ───────────────────────────────────────────────────────
    # CONCEPT: Routes let you send different task types to different queues.
    # We have one queue for now ("agent_tasks"), but defining it explicitly
    # makes it easy to add priority queues later (e.g. "fast_tasks" vs
    # "slow_tasks") without changing the task code.
    task_routes={
        "web.worker.tasks.run_agent_task": {"queue": "agent_tasks"},
    },

    # ── Default queue ─────────────────────────────────────────────────────
    # Workers listen on this queue by default.
    task_default_queue="agent_tasks",

    # ── Retry policy ──────────────────────────────────────────────────────
    # CONCEPT: If the broker (Redis) is temporarily unreachable when FastAPI
    # tries to send a task, Celery will retry the send up to 3 times with
    # 5 second intervals before raising an exception.
    # This is NOT the task retry (that's configured per-task in tasks.py).
    # This is just the message delivery retry.
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "max_retries": 3,
        "interval_start": 0,
        "interval_step": 5,
        "interval_max": 5,
    },
)

# ── Auto-discover tasks ───────────────────────────────────────────────────
# CONCEPT: autodiscover_tasks tells Celery to look for a tasks.py module
# inside each listed package. This is how Celery finds and registers
# all your @celery_app.task decorated functions at startup.
#
# Without this, you'd have to manually import every tasks.py file.
# With it, adding a new task module is automatic.
celery_app.autodiscover_tasks(["web.worker"])
