'use client'

import type { Execution } from '@/lib/types'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDistanceToNow } from '@/lib/time'

export function ActivityFeed({
  executions,
  loading,
}: {
  executions: Execution[]
  loading: boolean
}) {
  const recent = executions.slice(0, 8)

  return (
    <div className="card h-full flex flex-col gap-4">
      <div>
        <p className="text-xs font-mono text-muted-fg uppercase tracking-widest">Activity</p>
        <p className="text-sm font-semibold font-sans text-foreground mt-0.5">Recent Events</p>
      </div>

      {loading ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-muted animate-pulse flex-shrink-0" />
              <div className="flex-1 h-4 bg-muted rounded animate-pulse" />
              <div className="w-16 h-4 bg-muted rounded animate-pulse" />
            </div>
          ))}
        </div>
      ) : recent.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-muted-fg text-sm font-mono">No executions yet</p>
        </div>
      ) : (
        <div className="flex flex-col divide-y divide-border">
          {recent.map(ex => (
            <div key={ex.id} className="flex items-center gap-3 py-2.5 group">
              {/* Timeline dot */}
              <div className="flex flex-col items-center self-stretch pt-1">
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                  ex.status === 'completed' ? 'bg-success' :
                  ex.status === 'failed'    ? 'bg-danger' :
                  ex.status === 'running'   ? 'bg-accent animate-pulse-dot' :
                  'bg-muted-fg'
                }`} />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-mono text-foreground truncate">
                  <span className="text-muted-fg">#{ex.id}</span>
                  {' · '}
                  <span className="text-accent">{ex.agent_name}</span>
                </p>
                <p className="text-[11px] font-mono text-muted-fg truncate mt-0.5">
                  {ex.task.slice(0, 60)}{ex.task.length > 60 ? '…' : ''}
                </p>
              </div>

              {/* Right side */}
              <div className="flex flex-col items-end gap-1 flex-shrink-0">
                <StatusBadge status={ex.status} />
                <p className="text-[10px] font-mono text-muted-fg">
                  {formatDistanceToNow(ex.created_at)}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
