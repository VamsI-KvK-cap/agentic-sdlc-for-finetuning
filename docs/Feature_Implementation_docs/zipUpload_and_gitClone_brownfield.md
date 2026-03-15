The data model is clear. No DB schema change needed. The `task` field already carries the instruction, and `work_dir` is already passed to the agent. We just need to populate `output/{execution_id}/` with the repo contents **before** the Celery task starts the agent.

Here's the full design:

---

## Design

```
Current flow:
POST /executions  →  create DB row  →  .delay(execution_id, agent_name, task)
                                        ↓
                                   worker runs agent on empty work_dir

New flow:
POST /executions/from-zip   (multipart/form-data: zip file + agent_name + task)
POST /executions/from-git   (JSON: git_url + agent_name + task)
                ↓
         extract/clone → output/{execution_id}/
                ↓
         create DB row
                ↓
         .delay(execution_id, agent_name, task)
                ↓
         worker runs agent on pre-populated work_dir  ✓
```

**Why extract BEFORE creating the DB row?** If extraction fails (bad zip, invalid git URL) we want to return a clean 4xx error — no ghost `pending` rows in the DB.

**Schema change?** No. We add a `source_type` field to `ExecutionResponse` later (Phase N) for display purposes. For now the existing schema works fine.

**New endpoints:**
- `POST /api/v1/executions/from-zip` — multipart upload
- `POST /api/v1/executions/from-git` — JSON body

**New schemas:**
- `ExecutionFromZipCreate` — `agent_name` + `task` (zip comes as `UploadFile`)
- `ExecutionFromGitCreate` — `agent_name` + `task` + `git_url`

**New service layer** — `web/executions/source.py` handles extraction/cloning, keeping the router thin.

---

Let's build:

---

### File 1 — `web/executions/schemas.py` — add two new request schemas---

### File 2 — `web/executions/source.py` — extraction and cloning logic

This is the new service layer. Router stays thin — all the heavy lifting lives here.---

### File 3 — Updated `web/executions/router.py` — two new endpoints---

### File 4 — `Dockerfile.api` — add `git` to system packagesNow the UI — update `InputTabs.tsx` to wire up the existing zip/git UI to the new endpoints, and update `api.ts`:I can see the issue clearly — `handleGenerate` always calls `api.executions.create()` regardless of mode. Now I'll update `api.ts` and `agents/page.tsx`:Now add the new type and update `agents/page.tsx`:Also update `InputTabs.tsx` to accept `.zip` only for brownfield and update the placeholder:---

## Summary — Files to Update

```
web/executions/source.py          ← CREATE (new — zip extraction + git clone logic)
web/executions/router.py          ← REPLACE (adds /from-zip and /from-git endpoints)
web/executions/schemas.py         ← REPLACE (adds ExecutionFromGitCreate schema)
Dockerfile.api                    ← REPLACE (adds git + python-multipart)
ui/lib/api.ts                     ← REPLACE (adds createFromZip, createFromGit)
ui/lib/types.ts                   ← REPLACE (adds CreateExecutionFromGitPayload)
ui/app/agents/page.tsx            ← REPLACE (routes to correct endpoint per mode)
ui/components/agents/InputTabs.tsx ← REPLACE (zip only, better labels/hints)
```

---

## How It Works End-to-End

**Zip upload:**
1. User selects `.zip` in the File tab, writes the task in Step 3 instructions
2. Frontend sends `multipart/form-data` to `POST /api/v1/executions/from-zip`
3. Backend extracts zip into `output/{id}/`, flattens single root dir automatically
4. Celery worker picks up task — agent's planner reads the existing file structure first

**Git clone:**
1. User pastes `https://github.com/user/repo` in Git URL tab
2. Frontend sends JSON to `POST /api/v1/executions/from-git`
3. Backend runs `git clone --depth=1` into `output/{id}/` (shallow — fast)
4. Same flow from there

**After rebuild:**
```bash
task docker:build:api
task docker:build:worker
task docker:up:d
```