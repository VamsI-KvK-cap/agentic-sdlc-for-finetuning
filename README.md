# Agentic SDLC

An AI-powered software development lifecycle system. LangGraph-based coding agents autonomously plan, write, review, and lint code from natural language task descriptions. Triggered via a REST API, tracked in PostgreSQL, and monitored through a Next.js dashboard.

---

## How It Works

1. Open the **Agents** page in the UI, select an agent, describe your task, and click Generate
2. The API creates an execution record in PostgreSQL and responds immediately (`202 Accepted`)
3. In the background, the orchestrator picks the right coding agent and runs it
4. The agent goes through a **plan → code → review → write → lint** loop via LangGraph
5. The **Execution Detail** page streams live status updates via SSE until completion

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
├── output/                             # Agent-generated code output
├── Taskfile.yml                        # Dev task shortcuts
├── .env.example
├── docker-compose.yml
└── pyproject.toml
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

---

## Prerequisites

- **Python** 3.11+
- **Node.js** 18+ and npm
- **PostgreSQL** 14+
- **uv** — `pip install uv`
- **Task** (optional) — `sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b ~/.local/bin`

---

## Full Setup Guide

### 1. Clone the repo

```bash
git clone https://github.com/WahajSayyed/agentic-sdlc.git
cd agentic-sdlc
```

### 2. Python environment

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install all Python dependencies from lockfile
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
```

### 4. Set up PostgreSQL

```bash
# Start PostgreSQL
sudo service postgresql start

# Create the database
sudo -u postgres psql -c "CREATE DATABASE agentic_sdlc;"

# Set postgres user password if needed
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'your_password';"
```

### 5. Run database migrations

```bash
cd web
python -m alembic upgrade head
cd ..
```

### 6. Start the backend API

```bash
# Bind to 0.0.0.0 so the frontend can reach it (important for WSL2)
python -m uvicorn web.main:app --reload --host 0.0.0.0
```

API is now running at `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### 7. Set up the frontend

```bash
cd ui
npm install
```

Configure the API URL in `ui/.env.local`:
```env
# Use 127.0.0.1 or your WSL2 IP if running on Windows + WSL2
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

> **WSL2 users:** If `127.0.0.1` doesn't work, find your WSL2 IP with:
> ```bash
> ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1
> ```
> Use that IP in `ui/.env.local` and add it to `allow_origins` in `web/main.py`.
> Also fix DNS if npm install times out:
> ```bash
> echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
> ```

### 8. Start the frontend

```bash
cd ui
npm run dev
```

UI is now running at `http://localhost:3000`

---

## Running Both Servers

Open two terminals:

```bash
# Terminal 1 — Backend
source .venv/bin/activate
python -m uvicorn web.main:app --reload --host 0.0.0.0

# Terminal 2 — Frontend
cd ui
npm run dev
```

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

## Taskfile Shortcuts

```bash
task serve          # Start FastAPI backend
task db:migrate     # Run Alembic migrations
task db:rollback    # Rollback last migration
task db:reset       # Drop and recreate database (destructive)
task db:clean       # Truncate executions table, reset ID counter
task clean:output   # Delete all files under output/
task clean:all      # Truncate DB + delete output files
task clean:logs     # Delete log files
task setup          # First-time setup: create DB + run migrations
task test           # Run pytest
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

## Roadmap

- [x] LangGraph coding agent (Python)
- [x] FastAPI execution tracking with PostgreSQL
- [x] SSE live execution stream
- [x] Next.js dashboard UI (all pages)
- [ ] JavaScript / Go agents
- [ ] Chat interface with RAG
- [ ] LangGraph long-term memory for chat sessions
- [ ] Settings persistence to database
- [ ] Docker Compose full-stack setup
- [ ] CI/CD pipeline
