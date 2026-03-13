'use client'

import { usePathname } from 'next/navigation'
import { Activity } from 'lucide-react'

const PAGE_TITLES: Record<string, { title: string; description: string }> = {
  '/dashboard':  { title: 'Dashboard',   description: 'Overview of agent executions' },
  '/agents':     { title: 'Agents',      description: 'Trigger a coding agent' },
  '/executions': { title: 'Executions',  description: 'All execution runs' },
  '/chat':       { title: 'Chat',        description: 'RAG-powered assistant' },
  '/settings':   { title: 'Settings',    description: 'Configuration' },
}

export function Topbar() {
  const pathname = usePathname()

  // Match /executions/[id] pattern
  const isExecutionDetail = /^\/executions\/\d+/.test(pathname)
  const meta = isExecutionDetail
    ? { title: 'Execution Detail', description: 'Live execution status' }
    : PAGE_TITLES[pathname] ?? { title: 'Agentic SDLC', description: '' }

  return (
    <header className="h-14 flex items-center justify-between px-6 border-b border-border bg-surface flex-shrink-0">
      <div>
        <h1 className="text-sm font-bold font-sans text-foreground">{meta.title}</h1>
        {meta.description && (
          <p className="text-[11px] font-mono text-muted-fg">{meta.description}</p>
        )}
      </div>

      {/* Live indicator */}
      <div className="flex items-center gap-2 text-xs font-mono text-muted-fg">
        <Activity className="w-3.5 h-3.5" />
        <span>API: localhost:8000</span>
        <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse-dot" />
      </div>
    </header>
  )
}
