# Agentic SDLC

An AI-powered software development lifecycle system that uses LangGraph-based coding agents to autonomously generate, review, and lint code from natural language task descriptions. Agents are triggered via a FastAPI REST API and tracked in PostgreSQL.

---

## How It Works

1. You send a POST request with a task description and agent name (e.g. `"python"`)
2. The API creates an execution record in PostgreSQL and responds immediately with `202 Accepted`
3. In the background, the orchestrator picks the right coding agent and runs it
4. The agent goes through a **plan → code → review → write → lint** loop via LangGraph
5. You poll `GET /executions/{id}` to check the status (`pending → running → completed/failed`)

---

## Architecture

```
agentic-sdlc/
├── src/
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
├── web/                                # FastAPI application
│   ├── main.py                         # App entry point, lifespan, router registration
│   ├── database.py                     # SQLAlchemy async engine and session
│   ├── executions/                     # Executions feature module
│   │   ├── models.py                   # Execution ORM model
│   │   ├── schemas.py                  # Pydantic request/response schemas
│   │   ├── crud.py                     # DB operations
│   │   └── router.py                   # REST endpoints
│   └── alembic/                        # Database migrations
│       ├── env.py
│       └── versions/
│           └── 0001_create_executions_table.py
├── tests/
├── output/                             # Agent-generated code output
├── .env.example
├── docker-compose.yml
└── pyproject.toml
```

### LangGraph Agent Workflow

Each coding agent runs two nested LangGraph graphs:

**Main Graph**
```
setup → file_structure → planner → [reader] → process_files → END
```

**File Subgraph** (runs per file in the plan)
```
coder → reviewer → writer → static_check → END
         ↑____revise____|        |
                              retry → coder
```

---

## Tech Stack

- **[LangGraph](https://github.com/langchain-ai/langgraph)** — agent workflow orchestration
- **[FastAPI](https://fastapi.tiangolo.com/)** — REST API
- **[PostgreSQL](https://www.postgresql.org/)** — execution tracking
- **[SQLAlchemy 2.0](https://www.sqlalchemy.org/)** — async ORM
- **[Alembic](https://alembic.sqlalchemy.org/)** — database migrations
- **[Pydantic v2](https://docs.pydantic.dev/)** — request/response validation
- **[uv](https://github.com/astral-sh/uv)** — package management

---

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- [uv](https://github.com/astral-sh/uv) — `pip install uv`

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-username/agentic-sdlc.git
cd agentic-sdlc
```

### 2. Create and activate virtual environment

```bash
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
uv add fastapi uvicorn sqlalchemy asyncpg alembic pydantic python-dotenv langgraph
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/agentic_sdlc
```

### 5. Set up PostgreSQL

```bash
# Create the database
sudo -u postgres psql -c "CREATE DATABASE agentic_sdlc;"

# If you need to set/reset the postgres password
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'your_password';"
```

### 6. Run database migrations

```bash
cd web
python -m alembic upgrade head
cd ..
```

### 7. Start the API server

```bash
python -m uvicorn web.main:app --reload
```

The API is now running at `http://localhost:8000`.

---

## API Usage

### Trigger an agent execution

```bash
curl -X POST http://localhost:8000/api/v1/executions \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "python",
    "task": "As a store manager, I want to add a new product to the inventory so that I can track its availability."
  }'
```

Response (`202 Accepted`):
```json
{
  "id": 1,
  "agent_name": "python",
  "status": "pending",
  "task": "...",
  "created_at": "2026-03-13T00:00:00Z",
  "updated_at": "2026-03-13T00:00:00Z",
  "completed_at": null,
  "error_message": null
}
```

### Poll execution status

```bash
curl http://localhost:8000/api/v1/executions/1
```

Status progresses: `pending → running → completed` (or `failed`)

### List executions

```bash
# All executions
curl http://localhost:8000/api/v1/executions

# Filter by agent and status
curl "http://localhost:8000/api/v1/executions?agent_name=python&status=completed"
```

### Health check

```bash
curl http://localhost:8000/health
```

---

## Execution Table Schema

| Column          | Type                                     | Description                        |
|-----------------|------------------------------------------|------------------------------------|
| `id`            | SERIAL PK                                | Auto-incremented execution ID      |
| `agent_name`    | VARCHAR(100)                             | Agent used (e.g. `python`)         |
| `status`        | ENUM                                     | `pending/running/completed/failed` |
| `task`          | TEXT                                     | Task description                   |
| `error_message` | TEXT (nullable)                          | Populated on failure               |
| `created_at`    | TIMESTAMPTZ                              | Creation timestamp                 |
| `updated_at`    | TIMESTAMPTZ                              | Last update timestamp              |
| `completed_at`  | TIMESTAMPTZ (nullable)                   | Completion timestamp               |

---

## Adding a New Language Agent

1. Create `src/agents/{language}_coding_agent/` following the `python_coding_agent` structure
2. Implement the 4 abstract nodes: `planner_node`, `coder_node`, `reviewer_node`, `static_check_node`
3. Register it in `orchestrator_agent.py`:
```python
from src.agents.go_coding_agent.agent import GoCodingAgent

AGENTS = {
    "python": PythonCodingAgent,
    "go": GoCodingAgent,
}
```

---

## Interactive API Docs

FastAPI auto-generates documentation at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
