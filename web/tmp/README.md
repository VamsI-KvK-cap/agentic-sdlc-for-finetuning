# FastAPI + PostgreSQL Layer — Agentic SDLC

## Folder structure added

```
src/api/
├── main.py          ← FastAPI app entry point
├── database.py      ← SQLAlchemy async engine + session
├── models.py        ← Execution ORM model
├── schemas.py       ← Pydantic request/response schemas
├── crud.py          ← DB helpers (create, get, list, update)
└── routers/
    └── executions.py ← REST endpoints

alembic/
├── env.py                            ← async-aware Alembic env
└── versions/
    └── 0001_create_executions_table.py
```
```
POST /api/v1/executions
        │
        ▼
   main.py          ← routes to the executions router
        │
        ▼
   router.py        ← endpoint function receives the request
        │
        ├─ schemas.py   ← Pydantic validates the request body automatically
        ├─ database.py  ← session injected via Depends(get_db)
        │
        ▼
   crud.py          ← creates the Execution row, returns the ORM object
        │
        ▼
   schemas.py       ← Pydantic serializes the ORM object into JSON response
        │
        ▼
   BackgroundTask   ← agent runs async, updates status via crud.py

```

## Execution table schema

| Column         | Type                                          | Notes                        |
|----------------|-----------------------------------------------|------------------------------|
| id             | SERIAL PK                                     | auto-increment               |
| agent_name     | VARCHAR(100)                                  | e.g. "python", "go"          |
| status         | ENUM(pending/running/completed/failed)        | updated by background task   |
| task           | TEXT                                          | task description             |
| error_message  | TEXT (nullable)                               | populated on failure         |
| created_at     | TIMESTAMPTZ                                   |                              |
| updated_at     | TIMESTAMPTZ                                   |                              |
| completed_at   | TIMESTAMPTZ (nullable)                        |                              |

## Setup

```bash
# 1. Install postgres (Ubuntu)
sudo apt install postgresql postgresql-contrib
sudo service postgresql start
sudo -u postgres psql -c "CREATE DATABASE agentic_sdlc;"

# 2. Install Python deps
pip install -r requirements-api.txt

# 3. Configure env
cp .env.example .env   # edit DATABASE_URL if needed

# 4. Run migrations
alembic upgrade head

# 5. Start the API
uvicorn web.main:app --reload
```

## Endpoints

| Method | Path                        | Description                           |
|--------|-----------------------------|---------------------------------------|
| POST   | /api/v1/executions          | Trigger an agent (202 Accepted)       |
| GET    | /api/v1/executions          | List executions (filterable)          |
| GET    | /api/v1/executions/{id}     | Get single execution status           |
| GET    | /health                     | Health check                          |

### POST body example
```json
{
  "agent_name": "python",
  "task": "Write a FastAPI CRUD app for managing todos"
}
```

## Wiring the orchestrator (next step)

In `src/api/routers/executions.py`, the background task already imports and calls:

```python
from src.agents.orchestrator_agent.orchestrator_agent import OrchestratorAgent
agent = OrchestratorAgent(config={})
agent.run(task)
```

Adjust the import path to match your `orchestrator_agent.py` location.
The orchestrator's `run()` is called in a thread executor so the sync
LangGraph graph doesn't block the async event loop.
