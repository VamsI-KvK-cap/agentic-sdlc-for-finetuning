## Concept: Why Replace BackgroundTasks with Celery?

### What FastAPI BackgroundTasks Actually Does

When you call `background_tasks.add_task(...)`, FastAPI runs that coroutine **in the same process, on the same event loop** as the web server. It's essentially this:

```
FastAPI process
├── Event loop
│   ├── handles HTTP requests
│   ├── handles SSE streams
│   └── ALSO runs _run_agent_task()   ← sharing the same loop
```

This works fine for quick tasks. But your agent runs for **minutes**, blocking a thread in the pool. The problems:

**Problem 1 — Job loss on restart.** If uvicorn crashes or you redeploy while an agent is running, the job is gone. No retry, no recovery. The execution row stays `running` forever in the DB — a "ghost execution."

**Problem 2 — No concurrency control.** If 10 users trigger agents simultaneously, 10 threads run in the same process. You can't limit this, scale it, or distribute it.

**Problem 3 — No retry on failure.** If the LLM API times out halfway through, the job fails permanently. You have to manually re-trigger.

**Problem 4 — No visibility.** You can't see what's queued, what's running, or inspect failed jobs without querying your DB.

---

### What Celery Solves

Celery introduces a **completely separate worker process** connected via a **message broker** (Redis):

```
Before (BackgroundTasks):
┌─────────────────────────────────┐
│ FastAPI process                 │
│  ├── handle HTTP requests       │
│  └── run agent (blocking!)      │
└─────────────────────────────────┘

After (Celery):
┌──────────────┐    ┌───────┐    ┌──────────────────────┐
│ FastAPI      │───►│ Redis │───►│ Celery Worker        │
│ process      │    │ queue │    │  ├── agent task 1    │
│ (just HTTP)  │    │       │    │  ├── agent task 2    │
└──────────────┘    └───────┘    │  └── agent task 3    │
                                 └──────────────────────┘
```

**FastAPI** only does one thing: accept HTTP requests and drop a message into Redis.

**Redis** holds the queue of pending jobs — durable, inspectable, survives restarts.

**Celery Worker** is a completely separate process that picks up jobs from Redis and executes them. You can run multiple workers, restart them independently, scale them horizontally.

---

### Key Concepts You'll Learn Here

**Task** — a Python function decorated with `@celery_app.task`. Celery serialises the arguments, sends them to Redis, and the worker deserialises and executes them.

**Broker** — Redis in our case. The middleman that holds the queue. Celery supports RabbitMQ too but Redis is simpler and you already have it.

**Result backend** — where Celery stores task results/state. We'll use Redis for this too. Without it, you can't check if a task succeeded or failed from outside the worker.

**Worker** — a separate process you start with `celery -A web.worker.celery_app worker`. It connects to Redis, watches for tasks, and executes them.

**Retry** — if a task raises an exception, Celery can automatically retry it with configurable backoff. `@celery_app.task(max_retries=3, default_retry_delay=60)`.

---

### What Changes in Our Code

```
Current flow:
POST /executions
  → create DB row (pending)
  → background_tasks.add_task(_run_agent_task)   ← runs in FastAPI process
  → return 202

New flow:
POST /executions
  → create DB row (pending)
  → run_agent_task.delay(execution_id, ...)      ← sends message to Redis
  → return 202                                   ← FastAPI is done immediately

Celery worker (separate process):
  → picks up message from Redis
  → marks DB row as running
  → runs agent
  → marks DB row as completed/failed
```

The router change is **one line** — `.delay()` instead of `background_tasks.add_task()`. The heavy lifting moves to `web/worker/tasks.py`.

---

### Files We'll Create / Modify

```
web/worker/
├── __init__.py          NEW — makes it a package
├── celery_app.py        NEW — Celery instance + configuration
└── tasks.py             NEW — the agent task (ported from _run_agent_task)

web/executions/
└── router.py            MODIFY — swap BackgroundTasks for task.delay()

web/main.py              MODIFY — remove BackgroundTasks import (no longer needed)
.env / .env.docker       MODIFY — add REDIS_URL
docker-compose.yml       MODIFY — uncomment worker service
Dockerfile.api           MODIFY — add celery to CMD options
pyproject.toml           MODIFY — add celery dependency
```

---


## Let's build it file by file.

---

### Step 1 — Add Celery to dependencies

```bash
uv add celery[redis]
```

This installs Celery with the Redis transport. The `[redis]` extra adds `redis-py` which Celery needs to talk to Redis as both broker and result backend.

---

### File 1 — `web/worker/__init__.py`

Simple package marker, but the comment explains why this folder exists architecturally.---

### File 2 — `web/worker/celery_app.py`

This is the Celery instance — the equivalent of FastAPI's `app = FastAPI(...)`. Everything configures here, nothing executes here.---

### File 3 — `web/worker/tasks.py`

This is where `_run_agent_task` from your router moves to. Same logic, but now it's a proper Celery task with retry support and full lifecycle management.---

### File 4 — Updated `web/executions/router.py`

This is the smallest change — one import removed, one line changed. Everything else stays identical.---

### File 5 — Updated `docker-compose.yml`

Uncomment the worker service and add a `Flower` monitoring UI — Flower is the open-source Celery dashboard that shows queued/running/completed tasks in real time.Now update the Taskfile and copy everything to outputs:---

## Summary — What Changed and Where to Put Each File

```
web/worker/__init__.py       ← CREATE (new folder + file)
web/worker/celery_app.py     ← CREATE
web/worker/tasks.py          ← CREATE
web/executions/router.py     ← REPLACE (swap BackgroundTasks → .delay())
docker-compose.yml           ← REPLACE (worker + flower uncommented)
Taskfile.yml                 ← REPLACE (added worker/flower/celery tasks)
```

---

## Steps to Run Phase 2

**1. Install Celery:**
```bash
uv add celery[redis]
```

**2. Add `REDIS_URL` to your `.env`** (for local dev):
```env
REDIS_URL=redis://localhost:6379/0
```

**3. Start with Docker:**
```bash
task docker:up:d
task docker:db:migrate
```

**4. You now have 6 services running:**
- `http://localhost:3000` — Next.js UI
- `http://localhost:8000` — FastAPI API
- `http://localhost:5555` — **Flower** (Celery dashboard — new!)
- PostgreSQL on `5433`
- Redis on `6379`
- Celery worker (no port — background process)

**5. Trigger an execution from the UI and watch Flower** at `http://localhost:5555` — you'll see the task appear in the queue, move to active, then complete. This is the visibility you didn't have with `BackgroundTasks`.

---

## The Key Learning from Phase 2

The router change was literally **4 lines**:
- Remove `BackgroundTasks` import
- Remove `background_tasks` parameter
- Remove `background_tasks.add_task(...)`
- Add `run_agent_task.delay(...)`

The complexity lives in `celery_app.py` (configuration) and `tasks.py` (execution) — completely separate from your HTTP layer. This separation is the core principle of message-driven architecture: **the producer (FastAPI) knows nothing about the consumer (worker) except the message format.**