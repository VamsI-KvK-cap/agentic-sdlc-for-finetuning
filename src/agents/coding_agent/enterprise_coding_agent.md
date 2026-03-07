```
User Request
     │
     ▼
┌─────────────┐
│   PLANNER   │  ← Understands request, explores codebase,
│    Agent    │    creates a structured plan (what files, what changes)
└──────┬──────┘
       │  plan
       ▼
┌─────────────┐
│  EXECUTOR   │  ← Takes plan, reads files, makes actual edits
│    Agent    │    one task at a time
└──────┬──────┘
       │  changes made
       ▼
┌─────────────┐
│  REVIEWER   │  ← Reviews all changes, checks for bugs,
│    Agent    │    consistency, security issues
└──────┬──────┘
       │
       ▼
  Approve / Request Revision
```

## LSP Integration
What LSP gives you that file-reading doesn't:

Find all usages of a function across the entire codebase instantly
Jump to definition without knowing which file it's in
Get all symbols in a file (functions, classes, variables)
Understand imports and dependencies without reading every file

The planner becomes dramatically smarter — instead of guessing which files to read, it knows exactly where every symbol is defined and used.

```
Your Agent                    LSP Server (pylsp)
     │                              │
     │  "where is login() defined?" │
     │ ────────────────────────────>│
     │                              │ scans codebase
     │  "auth/login.py line 42"     │
     │ <────────────────────────────│
     │                              │
     │  "who calls login()?"        │
     │ ────────────────────────────>│
     │  "api/routes.py:15,          │
     │   tests/test_auth.py:8"      │
     │ <────────────────────────────│
```
