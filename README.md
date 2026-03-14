# Agentic SDLC

An AI-powered software development lifecycle system. LangGraph-based coding agents autonomously plan, write, review, and lint code from natural language task descriptions. Triggered via a REST API, tracked in PostgreSQL, and monitored through a Next.js dashboard.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Option A — Local Development Setup](#option-a--local-development-setup)
- [Option B — Docker Setup (Recommended)](#option-b--docker-setup-recommended)
- [Running Locally (All Services)](#running-locally-all-services)
- [UI Pages](#ui-pages)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [Taskfile Reference](#taskfile-reference)
- [Adding a New Language Agent](#adding-a-new-language-agent)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

---

## How It Works

1. Open the **Agents** page in the UI, select an agent, describe your task, and click Generate
2. The API creates an execution record in PostgreSQL and responds immediately (`202 Accepted`)
3. The API sends a message to **Redis** via Celery — FastAPI's job is done
4. The **Celery worker** (separate process) picks up the message and runs the agent
5. The agent goes through a **plan → code → review → write → lint** loop via LangGraph
6. The **Execution Detail** page streams live status updates via SSE until completion
7. Monitor worker activity in real time via **Flower** at `http://localhost:5555`

---

## Architecture

```
agentic-sdlc/
├── src/                                # Agent framework
│   ├── agents/
│   │   ├── coding_agent/               # Base agent interfaces
│   │   ├── orchestrator_agent/         # Routes tasks to the right language agent
│   │   │   └── orchestrator_agent.py
│   │   └── python_coding_agent/        # Concrete Python agent implementation
│   ├── base_workflows/
│   │   └── base_coding_agent_workflow/ # Abstract LangGraph workflow (BaseCodingAgent)
│   │       ├── agent.py                # Abstract base class
│   │       ├── state.py                # BaseAgentState, BaseFileAgentState
│   │       ├── nodes/                  # setup, reader, writer, process_files
│   │       └── decisions/              # should_read, review_decision, static_check_decision
│   ├── config/                         # LLM and language config
│   ├── tools/                          # Shared agent tools
│   └── utils/                          # Logger and helpers
│
├── web/                                # FastAPI backend
│   ├── main.py                         # App entry point, CORS, router registration
│   ├── database.py                     # SQLAlchemy async engine and session
│   ├── executions/                     # Executions feature module
│   │   ├── models.py                   # Execution ORM model
│   │   ├── schemas.py                  # Pydantic request/response schemas
│   │   ├── crud.py                     # DB operations
│   │   └── router.py                   # REST endpoints + SSE stream
│   ├── agents/                         # Agents feature module
│   │   └── router.py                   # GET /api/v1/agents endpoint
│   ├── worker/                         # Celery async execution layer
│   │   ├── __init__.py
│   │   ├── celery_app.py               # Celery instance + configuration
│   │   └── tasks.py                    # Agent execution task definition
│   └── alembic/                        # Database migrations
│       ├── alembic.ini
│       ├── env.py
│       └── versions/
│           └── 0001_create_executions_table.py
│
├── ui/                                 # Next.js frontend
│   ├── app/                            # Next.js App Router pages
│   │   ├── dashboard/                  # Stats, charts, activity feed
│   │   ├── agents/                     # Trigger agent executions
│   │   ├── executions/                 # Execution list + detail with live SSE
│   │   ├── chat/                       # Chat interface (skeleton)
│   │   └── settings/                   # API keys, models, agents config
│   ├── components/                     # React components
│   └── lib/                            # API client, types, hooks, utilities
│
├── tests/
├── output/                             # Agent-generated code output (persistent)
├── logs/                               # Application logs (persistent)
├── data/                               # Shared data directory (persistent)
├── Taskfile.yml                        # Dev task shortcuts (local + Docker)
├── docker-compose.yml                  # Full stack container orchestration
├── Dockerfile.api                      # FastAPI + Celery worker image
├── Dockerfile.ui                       # Next.js container image
├── .env.example                        # Local environment template
├── .env.docker.example                 # Docker environment template
└── pyproject.toml
```

### Request Flow (Phase 2 — Celery)

```
Browser
  │
  ▼
Next.js UI (port 3000)
  │  POST /api/v1/executions
  ▼
FastAPI (port 8000)
  │  creates DB row (PENDING)
  │  run_agent_task.delay()
  ▼
Redis (port 6379)          ◄── Flower monitors this (port 5555)
  │  task queue
  ▼
Celery Worker
  │  PENDING → RUNNING → COMPLETED/FAILED
  ▼
PostgreSQL (port 5433)
```

### LangGraph Agent Workflow

**Main Graph:**
```
setup → file_structure → planner → [reader] → process_files → END
```

**File Subgraph** (runs per file):
```
coder → reviewer → writer → static_check → END
         ↑____revise____|        |
                              retry → coder
```

---

## Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Agent framework | [LangGraph](https://langchain-ai.github.io/langgraph/) |
| LLM provider | [Anthropic Claude](https://docs.anthropic.com) |
| API | [FastAPI](https://fastapi.tiangolo.com) |
| Database | [PostgreSQL](https://www.postgresql.org) |
| ORM | [SQLAlchemy 2.0 async](https://www.sqlalchemy.org) |
| Migrations | [Alembic](https://alembic.sqlalchemy.org) |
| Validation | [Pydantic v2](https://docs.pydantic.dev) |
| Package manager | [uv](https://docs.astral.sh/uv) |

### Frontend
| Layer | Technology |
|---|---|
| Framework | [Next.js 14](https://nextjs.org) (App Router) |
| Language | TypeScript |
| Styling | [Tailwind CSS](https://tailwindcss.com) |
| Charts | [Recharts](https://recharts.org) |
| Icons | [Lucide React](https://lucide.dev) |
| Real-time | SSE (Server-Sent Events) |

### Infrastructure
| Layer | Technology |
|---|---|
| Containerisation | [Docker](https://www.docker.com) + [Docker Compose](https://docs.docker.com/compose/) |
| Task queue | [Celery](https://docs.celeryq.dev) |
| Message broker | [Redis 7](https://redis.io) |
| Worker monitoring | [Flower](https://flower.readthedocs.io) (open source) |
| Task runner | [Task](https://taskfile.dev) |

---

## Prerequisites

### Local Development
- **Python** 3.12+
- **Node.js** 18+ and npm
- **PostgreSQL** 14+
- **Redis** — `sudo apt install redis-server`
- **uv** — `pip install uv`
- **Task** (optional) — `sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin`

### Docker Setup
- **Docker** 24+ — [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose** v2+ (included with Docker Desktop)
- No Python, Node, PostgreSQL, or Redis needed on your host machine

---

## Option A — Local Development Setup

### 1. Clone the repo

```bash
git clone https://github.com/WahajSayyed/agentic-sdlc.git
cd agentic-sdlc
```

### 2. Python environment

```bash
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/agentic_sdlc
ANTHROPIC_API_KEY=sk-ant-...
REDIS_URL=redis://localhost:6379/0
WORKING_DIR=./output
```

### 4. Set up PostgreSQL

```bash
sudo service postgresql start
sudo -u postgres psql -c "CREATE DATABASE agentic_sdlc;"
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'your_password';"
```

### 5. Start Redis

```bash
sudo service redis-server start
```

### 6. Run database migrations

```bash
cd web && python -m alembic upgrade head && cd ..
```

### 7. Start the backend

```bash
python -m uvicorn web.main:app --reload --host 0.0.0.0
```

API running at `http://localhost:8000` — Swagger UI at `http://localhost:8000/docs`

### 8. Start the Celery worker

```bash
# In a new terminal (with venv activated)
celery -A web.worker.celery_app worker --loglevel=info --queues=agent_tasks --concurrency=2
```

### 9. Start Flower (optional — worker monitoring)

```bash
# In a new terminal (with venv activated)
celery -A web.worker.celery_app flower --port=5555
```

Flower UI at `http://localhost:5555`

### 10. Set up and start the frontend

```bash
cd ui && npm install
```

Create `ui/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

```bash
npm run dev
```

UI running at `http://localhost:3000`

> **WSL2 users:** If `127.0.0.1` doesn't work, use your WSL2 IP instead:
> ```bash
> ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1
> ```
> Use that IP in `ui/.env.local` and add it to `allow_origins` in `web/main.py`.
> If `npm install` times out, fix DNS first:
> ```bash
> echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
> ```

---

## Running Locally (All Services)

You need four terminals:

```bash
# Terminal 1 — Backend API
source .venv/bin/activate
python -m uvicorn web.main:app --reload --host 0.0.0.0

# Terminal 2 — Celery Worker
source .venv/bin/activate
celery -A web.worker.celery_app worker --loglevel=info --queues=agent_tasks --concurrency=2

# Terminal 3 — Flower (optional)
source .venv/bin/activate
celery -A web.worker.celery_app flower --port=5555

# Terminal 4 — Frontend
cd ui && npm run dev
```

Or use Task shortcuts:
```bash
task serve          # terminal 1
task serve:worker   # terminal 2
task serve:flower   # terminal 3
task serve:ui       # terminal 4
```

---
## Option B — Docker Setup (Recommended)

Runs the full stack in containers — no local Python, Node, PostgreSQL, or Redis required.

### 1. Clone the repo

```bash
git clone https://github.com/WahajSayyed/agentic-sdlc.git
cd agentic-sdlc
```

### 2. Configure Docker environment

```bash
cp .env.docker.example .env.docker
```

Edit `.env.docker` — key values to set:
```env
ANTHROPIC_API_KEY=sk-ant-...
NEXT_PUBLIC_API_URL=http://<YOUR_WSL2_IP>:8000
REDIS_URL=redis://redis:6379/0
PYTHONPATH=/app
```

> **WSL2 users:** The browser runs on Windows so `localhost` doesn't reach WSL2.
> Find your WSL2 IP:
> ```bash
> ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1
> ```
> Use that IP for `NEXT_PUBLIC_API_URL` and add it to `allow_origins` in `web/main.py`.
>
> **Permanent fix** — enable mirrored networking in `C:\Users\<you>\.wslconfig`:
> ```ini
> [wsl2]
> networkingMode=mirrored
> ```
> Then `wsl --shutdown` and restart. After this `localhost` works everywhere.

### 3. Start all containers

```bash
task docker:up:d
```

Or without Task:
```bash
docker compose --env-file .env.docker up --build -d
```

This starts 6 services: **PostgreSQL** · **Redis** · **FastAPI** · **Celery Worker** · **Flower** · **Next.js**

### 4. Run database migrations

```bash
task docker:db:migrate
```

Or:
```bash
docker compose exec api python -m alembic upgrade head
```

### 5. Open the services

| Service | URL |
|---|---|
| UI | `http://localhost:3000` |
| API | `http://localhost:8000` |
| API Docs | `http://localhost:8000/docs` |
| Flower (worker monitor) | `http://localhost:5555` |

---

## UI Pages

| Route | Description |
|---|---|
| `/dashboard` | Execution stats, pie chart, activity feed, recent runs table |
| `/agents` | Trigger an agent — select agent, enter task via text/file/git, add instructions |
| `/executions` | Filterable, paginated table of all execution runs |
| `/executions/[id]` | Live execution detail — SSE status stream, task, metadata, error details |
| `/chat` | Multi-session chat interface — RAG + LangGraph memory (coming soon) |
| `/settings` | API keys, model config, agent settings, database info |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/agents` | List available agents |
| `POST` | `/api/v1/executions` | Trigger an agent execution (202 Accepted) |
| `GET` | `/api/v1/executions` | List executions (filterable by agent, status) |
| `GET` | `/api/v1/executions/{id}` | Get single execution |
| `GET` | `/api/v1/executions/{id}/stream` | SSE live status stream |

### Trigger an execution

```bash
curl -X POST http://localhost:8000/api/v1/executions \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "python",
    "task": "As a store manager, I want to add a new product to the inventory so that I can track its availability."
  }'
```

### Watch live stream

```bash
curl -N http://localhost:8000/api/v1/executions/1/stream
```

---

## Database Schema

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL PK | Auto-incremented execution ID |
| `agent_name` | VARCHAR(100) | Agent used (e.g. `python`) |
| `status` | ENUM | `pending / running / completed / failed` |
| `task` | TEXT | Task description |
| `error_message` | TEXT (nullable) | Populated on failure |
| `created_at` | TIMESTAMPTZ | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | Last update timestamp |
| `completed_at` | TIMESTAMPTZ (nullable) | Completion timestamp |

---

## Taskfile Reference

### Local Dev Tasks

```bash
task serve              # Start FastAPI backend locally
task serve:ui           # Start Next.js frontend locally
task serve:worker       # Start Celery worker locally
task serve:flower       # Start Flower monitoring UI locally
task db:migrate         # Run Alembic migrations (local DB)
task db:rollback        # Rollback last migration (local DB)
task db:reset           # Drop and recreate local DB (destructive)
task db:clean           # Truncate executions table (local DB)
task clean:output       # Delete all files under output/
task clean:logs         # Delete log files
task clean:all          # Clean output + truncate DB
task test               # Run pytest
task install            # Install Python dependencies via uv sync
task setup              # First-time setup: create DB + run migrations
```

### Docker Tasks

```bash
# Lifecycle
task docker:up          # Build images and start all containers (foreground)
task docker:up:d        # Build images and start all containers (background)
task docker:start       # Start containers without rebuilding
task docker:stop        # Stop all containers (keeps data)
task docker:down        # Stop containers and delete all volumes (destructive)
task docker:restart     # Restart all containers

# Building
task docker:build       # Build all images
task docker:build:api   # Rebuild API image only
task docker:build:ui    # Rebuild UI image only
task docker:build:worker # Rebuild worker image only

# Database
task docker:db:migrate  # Run migrations inside api container
task docker:db:rollback # Rollback last migration
task docker:db:clean    # Truncate executions table
task docker:db:reset    # Drop and recreate DB (destructive)
task docker:db:shell    # Open psql shell in db container

# Celery worker
task docker:worker:restart    # Restart worker container only
task docker:celery:inspect    # List active tasks being processed
task docker:celery:stats      # Show worker stats
task docker:celery:purge      # Purge all pending tasks (WARNING — irreversible)

# Logs
task docker:logs        # Stream logs from all containers
task docker:logs:api    # Stream API logs only
task docker:logs:ui     # Stream UI logs only
task docker:logs:db     # Stream DB logs only
task docker:logs:worker # Stream Celery worker logs only
task docker:logs:flower # Stream Flower logs only

# Shell access
task docker:shell:api    # bash inside api container
task docker:shell:worker # bash inside worker container
task docker:shell:ui     # sh inside ui container
task docker:shell:db     # psql shell inside db container

# Status
task docker:ps          # Show container status
task docker:stats       # Live CPU/memory usage

# Cleanup
task docker:clean:all   # Stop containers + clean output + clean logs
task docker:prune       # Remove unused Docker images and networks
```

---

## Adding a New Language Agent

1. Create `src/agents/{language}_coding_agent/` following the `python_coding_agent` structure
2. Implement the 4 abstract nodes: `planner_node`, `coder_node`, `reviewer_node`, `static_check_node`
3. Register in `src/agents/orchestrator_agent/orchestrator_agent.py`:

```python
from src.agents.go_coding_agent.agent import GoCodingAgent

AGENTS = {
    "python": PythonCodingAgent,
    "go": GoCodingAgent,    # ← add this
}
```

The agent automatically appears in the UI dropdown and `GET /api/v1/agents` — no other changes needed.

---

## Troubleshooting

### `celery: executable file not found in $PATH`
Celery isn't installed to the system PATH in the container. Ensure `Dockerfile.api` uses `uv pip install --system` (not `uv sync`) so binaries land in `/usr/local/bin`.

### `ModuleNotFoundError: No module named 'src'`
The project root isn't on Python's path inside the container. Add to the worker and api services in `docker-compose.yml`:
```yaml
environment:
  PYTHONPATH: /app
```

### `Future attached to a different loop`
SQLAlchemy's async engine was bound to a different event loop. Ensure `web/worker/tasks.py` uses a single `asyncio.run()` for the entire task lifecycle and creates a fresh engine inside `_run_agent_async()`.

### `npm install` times out (WSL2)
DNS resolution is broken. Fix with:
```bash
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
```

### UI shows "Could not reach API"
The browser (Windows) can't reach `localhost` inside WSL2. Use your WSL2 IP in `NEXT_PUBLIC_API_URL`:
```bash
ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1
```
Or enable mirrored networking permanently — see the Docker setup section.

---

## Roadmap

- [x] LangGraph coding agent (Python)
- [x] FastAPI execution tracking with PostgreSQL
- [x] SSE live execution stream
- [x] Next.js dashboard UI (all pages)
- [x] Docker Compose full-stack setup
- [x] Celery + Redis task queue (Phase 2)
- [ ] Langfuse tracing — self-hosted (Phase 3)
- [ ] Prometheus + Grafana metrics (Phase 3)
- [ ] JavaScript / Go agents
- [ ] Chat interface with RAG
- [ ] LangGraph long-term memory for chat sessions
- [ ] Settings persistence to database
- [ ] CI/CD pipeline with GitHub Actions
