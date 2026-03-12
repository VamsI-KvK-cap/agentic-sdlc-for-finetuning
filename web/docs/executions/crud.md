`crud.py` file implements the **database access layer** for the `executions` feature. It contains functions that interact with the database using **async SQLAlchemy ORM**.

It follows the **CRUD pattern** (Create, Read, Update, Delete), although this file only implements:

* **Create**
* **Read**
* **Update**

It uses **SQLAlchemy** with async sessions.

I'll explain:

1️⃣ The role of this file in the architecture
2️⃣ Each function step-by-step
3️⃣ The SQL queries generated
4️⃣ The runtime flow when used by the API

---

# 1️⃣ Role of `crud.py`

Your architecture likely looks like this:

```
Router
   ↓
CRUD layer
   ↓
Database
```

Example flow:

```
POST /executions
      ↓
router.create_execution()
      ↓
crud.create_execution()
      ↓
database insert
```

So **routers don't directly write SQL** — they call CRUD functions.

Benefits:

* cleaner routers
* reusable DB logic
* easier testing

---

# 2️⃣ Imports

```python
from datetime import datetime, timezone
```

Used to store timestamps in **UTC**.

Example:

```
updated_at
completed_at
```

Using `timezone.utc` avoids timezone bugs.

---

Next imports:

```python
from sqlalchemy import select, func
```

SQLAlchemy query builders.

Examples:

```
select(Execution)
func.count()
```

Equivalent SQL:

```
SELECT * FROM executions
SELECT COUNT(id)
```

---

Next:

```python
from sqlalchemy.ext.asyncio import AsyncSession
```

The async database session used for queries.

---

Next:

```python
from web.models import Execution, ExecutionStatus
```

These are ORM models.

Example model might look like:

```python
class Execution(Base):
    id: int
    agent_name: str
    task: str
    status: ExecutionStatus
```

---

Next:

```python
from web.schemas import ExecutionCreate
```

This is the **input schema** for creating executions.

Example request:

```json
{
  "agent_name": "coding-agent",
  "task": "Refactor login service"
}
```

---

# 3️⃣ `create_execution`

```python
async def create_execution(db: AsyncSession, payload: ExecutionCreate) -> Execution:
```

Creates a new execution record.

---

### Step 1 — create ORM object

```python
execution = Execution(
    agent_name=payload.agent_name,
    task=payload.task,
    status=ExecutionStatus.PENDING,
)
```

This creates a Python ORM object.

Nothing is written to the DB yet.

Equivalent conceptual SQL:

```
INSERT INTO executions (...)
```

---

### Step 2 — add to session

```python
db.add(execution)
```

This tells SQLAlchemy:

```
track this object
```

Still **not committed yet**.

---

### Step 3 — commit

```python
await db.commit()
```

This actually writes the row to the database.

Equivalent SQL:

```
INSERT INTO executions (agent_name, task, status)
VALUES (...)
```

---

### Step 4 — refresh object

```python
await db.refresh(execution)
```

Why?

Because the DB may generate fields:

```
id
created_at
timestamps
```

Example:

Before refresh:

```
execution.id = None
```

After refresh:

```
execution.id = 12
```

---

### Step 5 — return execution

Returns the ORM object.

The router will convert it to a response schema.

---

# 4️⃣ `get_execution`

```python
async def get_execution(db: AsyncSession, execution_id: int)
```

Fetch a single execution.

---

### Query

```python
select(Execution).where(Execution.id == execution_id)
```

Equivalent SQL:

```
SELECT *
FROM executions
WHERE id = ?
```

---

### Execute query

```python
result = await db.execute(...)
```

This returns a **Result object**.

---

### Extract row

```python
result.scalar_one_or_none()
```

Meaning:

| Case       | Result                  |
| ---------- | ----------------------- |
| row exists | return Execution object |
| no row     | return None             |

This avoids raising exceptions.

---

# 5️⃣ `list_executions`

This function implements **pagination + filtering**.

Signature:

```python
async def list_executions(
    db,
    skip=0,
    limit=20,
    agent_name=None,
    status=None
)
```

---

### Base queries

```python
query = select(Execution)
count_query = select(func.count(Execution.id))
```

Two queries are built:

1️⃣ fetch rows
2️⃣ count total rows

This supports pagination.

---

### Optional filtering

Agent filter:

```python
query = query.where(Execution.agent_name == agent_name)
```

SQL:

```
WHERE agent_name = ?
```

Status filter:

```python
query = query.where(Execution.status == status)
```

SQL:

```
WHERE status = 'RUNNING'
```

---

### Get total rows

```python
total = (await db.execute(count_query)).scalar_one()
```

SQL:

```
SELECT COUNT(id)
FROM executions
```

Returns total matching rows.

---

### Fetch paginated results

```python
query.offset(skip).limit(limit).order_by(Execution.id.desc())
```

SQL equivalent:

```
SELECT *
FROM executions
ORDER BY id DESC
LIMIT 20
OFFSET 0
```

---

### Extract ORM objects

```python
.scalars().all()
```

Result becomes:

```
list[Execution]
```

---

### Return result

Function returns:

```python
tuple[int, list[Execution]]
```

Example:

```
(100, [Execution(...), Execution(...)])
```

Meaning:

```
total rows = 100
returned rows = 20
```

---

# 6️⃣ `update_execution_status`

This function updates the execution state.

Used by background tasks when the agent runs.

Signature:

```python
update_execution_status(db, execution, status)
```

---

### Update status

```python
execution.status = status
```

Example:

```
PENDING → RUNNING
```

---

### Update timestamp

```python
execution.updated_at = datetime.now(timezone.utc)
```

This records when the execution changed.

---

### Completion logic

```python
if status in (COMPLETED, FAILED):
    execution.completed_at = now
```

This marks when execution finished.

---

### Error handling

```python
if error_message:
    execution.error_message = error_message
```

Example:

```
Git clone failed
```

Useful for debugging failed executions.

---

### Commit changes

```python
await db.commit()
```

Equivalent SQL:

```
UPDATE executions
SET status = 'RUNNING'
WHERE id = ?
```

---

### Refresh object

```python
await db.refresh(execution)
```

Ensures the returned object reflects DB state.

---

# 7️⃣ Real system execution flow

When a client starts an execution:

```
POST /executions
```

Flow:

```
router.create_execution()
      ↓
crud.create_execution()
      ↓
DB row inserted
      ↓
background task started
```

Then background agent updates status:

```
update_execution_status()
```

Transitions:

```
PENDING
   ↓
RUNNING
   ↓
COMPLETED / FAILED
```

---

# 8️⃣ Example database table lifecycle

| id | agent_name   | status  | updated_at |
| -- | ------------ | ------- | ---------- |
| 1  | coding-agent | PENDING | null       |

Agent starts:

| id | status  |
| -- | ------- |
| 1  | RUNNING |

Agent finishes:

| id | status    |
| -- | --------- |
| 1  | COMPLETED |

---

# 9️⃣ Why this CRUD design is good

Benefits:

✔ isolates database logic
✔ reusable functions
✔ easier testing
✔ clean routers
✔ consistent transaction handling

---

# ✅ Summary

This file implements database operations for executions:

| Function                  | Purpose                      |
| ------------------------- | ---------------------------- |
| `create_execution`        | insert new execution         |
| `get_execution`           | fetch one execution          |
| `list_executions`         | paginated list with filters  |
| `update_execution_status` | update status and timestamps |

It acts as the **database interface layer** between your API and the database.

---

💡 One **important improvement many production systems add** later:

Instead of manually calling `commit()` inside CRUD functions, they implement a **Unit of Work pattern** so that multiple operations can be committed together safely.

We can explore **how to refactor this CRUD file into a cleaner repository pattern**, which is common in larger FastAPI systems.
