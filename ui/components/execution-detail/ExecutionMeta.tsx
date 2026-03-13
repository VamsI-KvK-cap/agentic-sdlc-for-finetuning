'use client'

import type { Execution } from '@/lib/types'
import { formatDateTime, formatDuration } from '@/lib/time'
import { Clock, Timer, Bot, Hash } from 'lucide-react'

export function ExecutionMeta({ execution }: { execution: Execution }) {
  const rows = [
    {
      icon: <Hash className="w-3 h-3" />,
      label: 'Execution ID',
      value: `#${execution.id}`,
    },
    {
      icon: <Bot className="w-3 h-3" />,
      label: 'Agent',
      value: execution.agent_name,
    },
    {
      icon: <Clock className="w-3 h-3" />,
      label: 'Started',
      value: formatDateTime(execution.created_at),
    },
    {
      icon: <Clock className="w-3 h-3" />,
      label: 'Completed',
      value: execution.completed_at
        ? formatDateTime(execution.completed_at)
        : '—',
    },
    {
      icon: <Timer className="w-3 h-3" />,
      label: 'Duration',
      value: formatDuration(execution.created_at, execution.completed_at),
    },
  ]

  return (
    <div className="card space-y-0 p-0 overflow-hidden">
      <p className="text-[10px] font-mono text-muted-fg uppercase tracking-widest px-4 pt-4 pb-2">
        Metadata
      </p>
      {rows.map((row, i) => (
        <div
          key={row.label}
          className="flex items-center justify-between px-4 py-2.5 border-t border-border/50 first:border-0"
        >
          <div className="flex items-center gap-2 text-muted-fg">
            {row.icon}
            <span className="text-xs font-mono">{row.label}</span>
          </div>
          <span className="text-xs font-mono text-foreground">{row.value}</span>
        </div>
      ))}
    </div>
  )
}
