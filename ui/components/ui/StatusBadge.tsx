import { cn } from '@/lib/utils'
import type { ExecutionStatus } from '@/lib/types'

const CONFIG: Record<ExecutionStatus, { label: string; dot: string; badge: string }> = {
  pending:   { label: 'Pending',   dot: 'bg-muted-fg',  badge: 'badge-pending' },
  running:   { label: 'Running',   dot: 'bg-accent animate-pulse-dot',    badge: 'badge-running' },
  completed: { label: 'Completed', dot: 'bg-success',   badge: 'badge-completed' },
  failed:    { label: 'Failed',    dot: 'bg-danger',     badge: 'badge-failed' },
}

export function StatusBadge({ status }: { status: ExecutionStatus }) {
  const c = CONFIG[status]
  return (
    <span className={cn('badge', c.badge)}>
      <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', c.dot)} />
      {c.label}
    </span>
  )
}
