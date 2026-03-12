`models.py` defines the **database schema (ORM models)** for your application using **modern SQLAlchemy 2.0 typed ORM style** from SQLAlchemy.

It contains two main things:

1️⃣ An **Enum for execution status**
2️⃣ An **ORM model representing the `executions` table**

Let’s go step-by-step and also show the **actual SQL table that this creates**.

---

# 1️⃣ Imports

```python
import enum
from datetime import datetime, timezone
```

* `enum` → used to create a **status enumeration**
* `datetime` → used for timestamps
* `timezone.utc` → ensures timestamps are **UTC**

Using UTC avoids timezone bugs in distributed systems.

---

Next imports:

```python
from sqlalchemy import Integer, String, Enum, DateTime, Text
```

These represent **database column types**.

| SQLAlchemy Type | SQL Equivalent |
| --------------- | -------------- |
| `Integer`       | INTEGER        |
| `String(100)`   | VARCHAR(100)   |
| `Text`          | TEXT           |
| `DateTime`      | TIMESTAMP      |
| `Enum`          | ENUM           |

---

Next:

```python
from sqlalchemy.orm import Mapped, mapped_column
```

These are **SQLAlchemy 2.0 typed ORM features**.

They allow type-safe models like:

```python
id: Mapped[int]
```

Instead of the old style:

```python
id = Column(Integer)
```

---

Last import:

```python
from web.database import Base
```

`Base` is the root ORM class defined in `database.py`.

Your model must inherit from it:

```python
class Execution(Base)
```

This registers the table in:

```
Base.metadata
```

which allows:

```
create_all()
Alembic migrations
```

---

# 2️⃣ ExecutionStatus Enum

```python
class ExecutionStatus(str, enum.Enum):
```

This defines **allowed execution states**.

Values:

```python
PENDING = "pending"
RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
```

Meaning:

| Status    | Meaning                     |
| --------- | --------------------------- |
| PENDING   | job created but not started |
| RUNNING   | agent currently executing   |
| COMPLETED | finished successfully       |
| FAILED    | execution failed            |

---

Why inherit from **`str` + `Enum`**?

```python
class ExecutionStatus(str, enum.Enum)
```

This makes values behave like **strings**.

Example:

```python
ExecutionStatus.RUNNING == "running"
```

This is useful for:

* JSON responses
* Pydantic serialization
* database storage

---

In the database, this becomes:

```sql
status ENUM ('pending','running','completed','failed')
```

---

# 3️⃣ Execution ORM Model

```python
class Execution(Base):
```

This defines a **database table**.

---

### Table name

```python
__tablename__ = "executions"
```

SQL table:

```sql
executions
```

---

# 4️⃣ Primary key

```python
id: Mapped[int] = mapped_column(
    Integer,
    primary_key=True,
    autoincrement=True
)
```

This creates:

```sql
id INTEGER PRIMARY KEY
```

Auto increment means:

```
1
2
3
4
```

generated automatically.

---

# 5️⃣ Agent name

```python
agent_name: Mapped[str] = mapped_column(
    String(100),
    nullable=False,
    index=True
)
```

Database column:

```sql
agent_name VARCHAR(100) NOT NULL
```

`index=True` creates a database index:

```sql
CREATE INDEX idx_agent_name
```

This improves performance for queries like:

```
WHERE agent_name = 'coding-agent'
```

---

# 6️⃣ Execution status

```python
status: Mapped[ExecutionStatus] = mapped_column(
    Enum(ExecutionStatus),
    nullable=False,
    default=ExecutionStatus.PENDING
)
```

Column type:

```sql
status ENUM('pending','running','completed','failed')
```

Default value:

```
PENDING
```

Meaning when a row is created:

```
status = pending
```

unless specified otherwise.

---

# 7️⃣ Task column

```python
task: Mapped[str] = mapped_column(Text, nullable=False)
```

Database column:

```sql
task TEXT NOT NULL
```

This stores the **agent instruction**.

Example value:

```
"Refactor authentication module and add tests"
```

`Text` is used instead of `String` because tasks may be long.

---

# 8️⃣ Error message

```python
error_message: Mapped[str | None] = mapped_column(
    Text,
    nullable=True
)
```

Database column:

```sql
error_message TEXT NULL
```

This stores failure details.

Example:

```
"Git clone failed: repository not found"
```

`str | None` means:

```
Optional string
```

---

# 9️⃣ created_at timestamp

```python
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    default=lambda: datetime.now(timezone.utc),
)
```

Database column:

```sql
created_at TIMESTAMP WITH TIME ZONE
```

Default value:

```
current UTC timestamp
```

Example:

```
2026-03-11 14:21:03 UTC
```

The `lambda` ensures the value is generated **when the row is inserted**, not when the code loads.

---

# 🔟 updated_at timestamp

```python
updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    default=lambda: datetime.now(timezone.utc),
    onupdate=lambda: datetime.now(timezone.utc),
)
```

Two behaviors:

### Default

Set on insert.

### onupdate

Automatically update when row changes.

Example lifecycle:

```
created_at = 10:00
updated_at = 10:00
```

Status changes:

```
updated_at = 10:05
```

---

# 11️⃣ completed_at timestamp

```python
completed_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True
)
```

Database column:

```sql
completed_at TIMESTAMP WITH TIME ZONE NULL
```

This records when execution finishes.

Example:

```
created_at = 10:00
completed_at = 10:08
```

If execution still running:

```
completed_at = NULL
```

---

# 12️⃣ Final database table

This model creates a table roughly like this:

```sql
CREATE TABLE executions (
    id INTEGER PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    status ENUM('pending','running','completed','failed') NOT NULL,
    task TEXT NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE
);
```

Plus an index:

```sql
CREATE INDEX ix_executions_agent_name
ON executions(agent_name);
```

---

# 13️⃣ Example row

Example execution record:

| id | agent_name   | status  | task            | created_at |
| -- | ------------ | ------- | --------------- | ---------- |
| 1  | coding-agent | RUNNING | "Fix login bug" | 2026-03-11 |

After completion:

| id | status    | completed_at     |
| -- | --------- | ---------------- |
| 1  | COMPLETED | 2026-03-11 10:08 |

---

# 14️⃣ How this model is used

Flow across your project:

```
Router
   ↓
CRUD
   ↓
Execution model
   ↓
Database row
```

Example:

```
crud.create_execution()
```

creates:

```
Execution(...)
```

which becomes a row in the `executions` table.

---

# 15️⃣ Why this model design is good

This model supports **agent orchestration tracking**.

It allows you to track:

✔ execution lifecycle
✔ agent used
✔ task instructions
✔ failure reasons
✔ timestamps

Which is perfect for **AI workflow orchestration systems**.

---

✅ **Summary**

This file defines:

1️⃣ `ExecutionStatus` → allowed job states
2️⃣ `Execution` → database table for agent executions

Columns store:

```
agent name
task description
execution status
timestamps
error messages
```

---

💡 One **important improvement many production systems add** to this model:

They introduce an **execution log table** to store step-by-step agent actions (planner steps, tool calls, etc.), which becomes extremely useful when debugging AI agents.

We can explore **what the full database schema of a production AI agent platform usually looks like** (it's very interesting and goes beyond just executions).
