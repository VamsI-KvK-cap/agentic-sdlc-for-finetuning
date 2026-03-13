# Agentic SDLC — UI

Next.js 14 frontend for the Agentic SDLC system. Built with shadcn-style components, Tailwind CSS, and a dark developer-tool aesthetic.

---

## Tech Stack

- **Next.js 14** — App Router, file-based routing
- **TypeScript** — strict mode
- **Tailwind CSS** — utility-first styling with custom design tokens
- **Recharts** — charts on the dashboard
- **Lucide React** — icons

---

## Setup

```bash
cd ui
npm install
npm run dev
# → http://localhost:3000  (auto-redirects to /dashboard)
```

Make sure the FastAPI backend is running on `http://localhost:8000`.
The API base URL is configured in `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Folder Structure

```
ui/
├── app/                          # Next.js App Router pages
│   ├── layout.tsx                # Root layout: sidebar + topbar
│   ├── globals.css               # Design tokens, fonts, base classes
│   ├── page.tsx                  # Redirects / → /dashboard
│   ├── dashboard/
│   │   └── page.tsx              # ✅ Built — stats, chart, activity feed, table
│   ├── agents/
│   │   └── page.tsx              # ✅ Built — agent selector, input tabs, generate
│   ├── executions/
│   │   ├── page.tsx              # ✅ Built — filterable table with pagination
│   │   └── [id]/
│   │       └── page.tsx          # ✅ Built — live SSE stream, meta, task, error
│   ├── chat/
│   │   └── page.tsx              # ✅ Built — chat skeleton, sessions, file upload UI
│   └── settings/
│   │   └── page.tsx              # ✅ Built — API keys, models, agents, DB, about
│
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx           # ✅ Nav with active state highlighting
│   │   └── Topbar.tsx            # ✅ Page title + API live indicator
│   ├── ui/
│   │   └── StatusBadge.tsx       # ✅ Shared status pill (pending/running/completed/failed)
│   ├── dashboard/
│   │   ├── StatsGrid.tsx         # ✅ 5 stat cards with skeleton loaders
│   │   ├── ExecutionPieChart.tsx # ✅ Donut chart via recharts
│   │   ├── ActivityFeed.tsx      # ✅ Live timeline of recent events
│   │   └── RecentExecutions.tsx  # ✅ Last 10 runs table with hover links
│   ├── agents/
│   │   ├── AgentSelector.tsx     # ✅ Custom dropdown — fetches from API
│   │   ├── InputTabs.tsx         # ✅ Text / File Upload / Git URL tabs
│   │   ├── InstructionsBox.tsx   # ✅ Optional instructions + quick-insert chips
│   │   └── GenerateButton.tsx    # ✅ Loading spinner, disabled state
│   └── executions/
│       ├── ExecutionsTable.tsx   # ✅ Full table with skeleton, error, empty states
│       ├── ExecutionsFilter.tsx  # ✅ Status pill filters + agent text filter
│       └── Pagination.tsx        # ✅ Smart page range with ellipsis
│   └── execution-detail/
│       ├── ExecutionHeader.tsx   # ✅ Back button, title, status badge, timing
│       ├── ExecutionMeta.tsx     # ✅ Metadata table: ID, agent, times, duration
│       ├── TaskCard.tsx          # ✅ Full task description display
│       ├── ErrorCard.tsx         # ✅ Error message panel (shown on failure)
│       └── LiveStatusStream.tsx  # ✅ SSE event log with auto-scroll + typing dots
│   └── chat/
│       ├── ChatSidebar.tsx       # ✅ Session list, new/delete, coming-soon note
│       ├── ChatWindow.tsx        # ✅ Message bubbles, empty states, feature pills
│       └── ChatInput.tsx         # ✅ Auto-grow textarea, file+image attach, send
│   └── settings/
│       ├── SettingsNav.tsx       # ✅ Vertical tab nav (API/Models/Agents/DB/About)
│       ├── SettingsPrimitives.tsx # ✅ Shared: card, field, secret input, toggle, select, save btn
│       ├── ApiSection.tsx        # ✅ Anthropic + OpenAI key fields, backend URL
│       ├── ModelsSection.tsx     # ✅ Model picker per role (planner/coder/reviewer)
│       ├── AgentsSection.tsx     # ✅ Per-agent enable toggle + retry config
│       ├── DatabaseSection.tsx   # ✅ Connection health check + migration commands
│       └── AboutSection.tsx      # ✅ Stack, roadmap, GitHub link
│
└── lib/
    ├── api.ts                    # ✅ All FastAPI fetch calls: executions, agents, settings, SSE
    ├── types.ts                  # ✅ All TypeScript types: executions, agents, settings, health
    ├── utils.ts                  # ✅ cn() Tailwind class merger
    ├── time.ts                   # ✅ formatDistanceToNow, formatDateTime, formatDuration
    └── hooks.ts                  # ✅ useExecutions, useExecution, useAgents, useDashboardStats
```

---

## Pages

| Route | Status | Description |
|---|---|---|
| `/dashboard` | ✅ Done | Stats cards, pie chart, activity feed, recent executions |
| `/agents` | ✅ Done | Trigger agent — dropdown, text/file/git input, instructions |
| `/executions` | ✅ Done | Filterable, paginated executions table |
| `/executions/[id]` | ✅ Done | Live SSE stream, status timeline, task, error details |
| `/chat` | ✅ Done | Multi-session sidebar, message bubbles, file+image upload UI, RAG stub |
| `/settings` | ✅ Done | API keys, model config, agents, DB health, about + roadmap |

---

## Backend: New Endpoint Required

The Agents page calls `GET /api/v1/agents` to populate the dropdown.
Add this router to `web/`:

**`web/agents/router.py`** — create this file (provided as `web_agents_router.py` in outputs):
```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class AgentInfo(BaseModel):
    name: str
    language: str
    description: str

@router.get("/agents", response_model=list[AgentInfo])
async def list_agents():
    from src.agents.orchestrator_agent.orchestrator_agent import AGENTS
    ...
```

Then register in `web/main.py`:
```python
from web.agents.router import router as agents_router
app.include_router(agents_router, prefix="/api/v1", tags=["agents"])
```

---

## Design System

All colors are CSS variables defined in `globals.css`:

| Token | Usage |
|---|---|
| `--background` | Page background |
| `--surface` | Cards, sidebar |
| `--border` | All borders |
| `--accent` | Teal highlight, active states, links |
| `--accent-dim` | Accent backgrounds |
| `--muted` | Input backgrounds, hover states |
| `--muted-fg` | Secondary text, placeholders |
| `--foreground` | Primary text |
| `--success` | Completed status |
| `--warning` | Pending status |
| `--danger` | Failed status, errors |

Fonts: **Syne** (headings/UI) + **JetBrains Mono** (data/code/labels)
