'use client'

import { Filter, X } from 'lucide-react'
import type { ExecutionStatus } from '@/lib/types'
import { cn } from '@/lib/utils'

const STATUSES: { value: ExecutionStatus | ''; label: string }[] = [
  { value: '',           label: 'All'       },
  { value: 'pending',    label: 'Pending'   },
  { value: 'running',    label: 'Running'   },
  { value: 'completed',  label: 'Completed' },
  { value: 'failed',     label: 'Failed'    },
]

const STATUS_COLORS: Record<string, string> = {
  pending:   'text-muted-fg border-border',
  running:   'text-accent border-accent/40 bg-accent-dim/40',
  completed: 'text-green-400 border-green-800 bg-green-950/40',
  failed:    'text-red-400 border-red-800 bg-red-950/40',
}

interface Props {
  agentFilter: string
  statusFilter: ExecutionStatus | ''
  onAgentChange: (v: string) => void
  onStatusChange: (v: ExecutionStatus | '') => void
  onClear: () => void
}

export function ExecutionsFilter({
  agentFilter,
  statusFilter,
  onAgentChange,
  onStatusChange,
  onClear,
}: Props) {
  const hasFilter = agentFilter || statusFilter

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-1.5 text-xs font-mono text-muted-fg">
        <Filter className="w-3 h-3" />
        Filter:
      </div>

      {/* Status pills */}
      <div className="flex gap-1.5 flex-wrap">
        {STATUSES.map(s => (
          <button
            key={s.value}
            type="button"
            onClick={() => onStatusChange(s.value as ExecutionStatus | '')}
            className={cn(
              'badge cursor-pointer border transition-all duration-150',
              statusFilter === s.value
                ? s.value
                  ? STATUS_COLORS[s.value]
                  : 'text-foreground border-accent/50 bg-accent-dim/40'
                : 'text-muted-fg border-border hover:border-border/80 hover:text-foreground'
            )}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Agent search */}
      <input
        type="text"
        value={agentFilter}
        onChange={e => onAgentChange(e.target.value)}
        placeholder="Filter by agent…"
        className="input w-40 py-1 text-xs"
      />

      {/* Clear */}
      {hasFilter && (
        <button
          type="button"
          onClick={onClear}
          className="btn-ghost flex items-center gap-1.5 text-xs py-1"
        >
          <X className="w-3 h-3" />
          Clear
        </button>
      )}
    </div>
  )
}
