`schemas.py` file defines the **API data models** used by your FastAPI application for **request validation and response serialization**.

These schemas are built using **Pydantic**, which is tightly integrated with **FastAPI**.

Important concept:

```
SQLAlchemy models → database structure
Pydantic schemas → API input/output structure
```

Your file defines **three schemas**:

1. `ExecutionCreate` → request body for creating executions
2. `ExecutionResponse` → response returned by API
3. `ExecutionListResponse` → paginated list response

---

# 1️⃣ Imports

```python
from datetime import datetime
from pydantic import BaseModel, Field
from web.models import ExecutionStatus
```

### `BaseModel`

All Pydantic schemas inherit from `BaseModel`.

This gives features like:

* data validation
* JSON serialization
* automatic API documentation

---

### `Field`

Used to add metadata such as:

* descriptions
* examples
* constraints

These appear in **OpenAPI docs** (`/docs`).

---

### `ExecutionStatus`

This imports the Enum defined in `models.py`.

So responses can return values like:

```
pending
running
completed
failed
```

---

# 2️⃣ `ExecutionCreate` schema

```python
class ExecutionCreate(BaseModel):
```

This schema defines the **input body for POST /executions**.

---

### Fields

```python
agent_name: str = Field(..., description="Name of the agent to run (e.g. 'python')")
```

`...` means **required field**.

So request must include it.

Example valid request:

```json
{
  "agent_name": "python",
  "task": "Fix failing unit tests"
}
```

---

Second field:

```python
task: str = Field(..., description="Task description for the agent")
```

This describes what the agent should do.

Example:

```
"Refactor authentication module and add tests"
```

---

### Validation behavior

If request is missing fields:

```
POST /executions
{
   "task": "Fix login bug"
}
```

FastAPI returns:

```json
{
  "detail": "agent_name field required"
}
```

Pydantic automatically validates this.

---

# 3️⃣ `ExecutionResponse`

```python
class ExecutionResponse(BaseModel):
```

This defines **what the API returns when sending execution data**.

---

### Fields

```python
id: int
```

Database primary key.

---

```python
agent_name: str
```

Which agent ran the task.

Example:

```
python-agent
coding-agent
analysis-agent
```

---

```python
status: ExecutionStatus
```

Enum field.

Possible values:

```
pending
running
completed
failed
```

Example response:

```json
"status": "running"
```

---

```python
task: str
```

The task given to the agent.

---

```python
error_message: str | None = None
```

Optional field.

Only populated when execution fails.

Example:

```json
"error_message": "Repository clone failed"
```

---

### Timestamps

```python
created_at: datetime
updated_at: datetime
completed_at: datetime | None
```

These track execution lifecycle.

Example response:

```json
{
  "created_at": "2026-03-11T10:00:00Z",
  "updated_at": "2026-03-11T10:01:12Z",
  "completed_at": "2026-03-11T10:04:03Z"
}
```

---

# 4️⃣ Important line: `model_config`

```python
model_config = {"from_attributes": True}
```

This is **very important when using SQLAlchemy ORM**.

It tells Pydantic:

```
This schema can be created from ORM objects
```

Example:

Your CRUD returns:

```
Execution (SQLAlchemy model)
```

But FastAPI expects:

```
ExecutionResponse (Pydantic model)
```

With `from_attributes=True`, Pydantic automatically converts.

Example conversion:

```
Execution ORM object
       ↓
ExecutionResponse schema
       ↓
JSON response
```

Without this setting, FastAPI would raise errors like:

```
Object is not JSON serializable
```

---

# 5️⃣ `ExecutionListResponse`

```python
class ExecutionListResponse(BaseModel):
```

This schema is used for **list endpoints**.

Example endpoint:

```
GET /executions
```

---

### Fields

```python
total: int
```

Total number of executions in database.

Used for pagination.

---

```python
executions: list[ExecutionResponse]
```

List of execution objects.

Example response:

```json
{
  "total": 42,
  "executions": [
    {
      "id": 1,
      "agent_name": "python",
      "status": "completed",
      "task": "Fix tests",
      "created_at": "2026-03-11T10:00:00Z",
      "updated_at": "2026-03-11T10:04:00Z",
      "completed_at": "2026-03-11T10:04:00Z"
    }
  ]
}
```

---

# 6️⃣ Full request-response flow

Example API call:

```
POST /executions
```

---

### Step 1 — request validation

Request body validated using:

```
ExecutionCreate
```

Example:

```json
{
  "agent_name": "coding-agent",
  "task": "Refactor login module"
}
```

---

### Step 2 — database insert

Router calls:

```
crud.create_execution()
```

Which creates:

```
Execution ORM object
```

---

### Step 3 — response serialization

FastAPI converts ORM object into:

```
ExecutionResponse
```

Using:

```
model_config = {"from_attributes": True}
```

---

### Step 4 — final JSON response

Example:

```json
{
  "id": 15,
  "agent_name": "coding-agent",
  "status": "pending",
  "task": "Refactor login module",
  "error_message": null,
  "created_at": "2026-03-11T10:00:00Z",
  "updated_at": "2026-03-11T10:00:00Z",
  "completed_at": null
}
```

---

# 7️⃣ Why separate schemas from models

This separation is important.

```
models.py  → database schema
schemas.py → API schema
```

Benefits:

| Benefit       | Reason                           |
| ------------- | -------------------------------- |
| security      | hide internal fields             |
| flexibility   | API structure can differ from DB |
| validation    | Pydantic validates input         |
| documentation | FastAPI auto-generates API docs  |

Example:

Database may contain:

```
internal_token
agent_config
```

But API should **not expose them**.

Schemas control what the API returns.

---

# 8️⃣ Architecture placement

Your project structure likely looks like:

```
web/
   models.py
   schemas.py
   crud.py
   router.py
```

Interaction flow:

```
Client
   ↓
Router
   ↓
Schema validation
   ↓
CRUD
   ↓
Model
   ↓
Database
   ↓
Response schema
   ↓
JSON response
```

---

✅ **Summary**

This file defines API data models:

| Schema                  | Purpose                              |
| ----------------------- | ------------------------------------ |
| `ExecutionCreate`       | request body for creating executions |
| `ExecutionResponse`     | single execution response            |
| `ExecutionListResponse` | paginated list response              |

They validate incoming data and format outgoing responses using **Pydantic**.

---

💡 **One useful production improvement** many systems add:

Separate schemas into **request vs response models** like:

```
schemas/
   execution_create.py
   execution_update.py
   execution_response.py
```

This becomes very useful when APIs grow large.
