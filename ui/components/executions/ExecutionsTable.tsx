'use client'

import { ArrowRight, AlertCircle } from 'lucide-react'
import type { Execution } from '@/lib/types'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDistanceToNow, formatDateTime, formatDuration } from '@/lib/time'
import { cn } from '@/lib/utils'

interface Props {
  executions: Execution[]
  loading: boolean
  onRowClick: (id: number) => void
}

const COLUMNS = ['ID', 'Agent', 'Task', 'Status', 'Duration', 'Started', '']

export function ExecutionsTable({ executions, loading, onRowClick }: Props) {
  return (
    <div className="card p-0 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              {COLUMNS.map(col => (
                <th
                  key={col}
                  className="text-left text-muted-fg uppercase tracking-widest px-4 py-3 font-medium whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i} className="border-b border-border/50">
                  {Array.from({ length: 7 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div
                        className="h-3 bg-muted rounded animate-pulse"
                        style={{ width: `${[32, 64, 180, 72, 48, 80, 16][j]}px` }}
                      />
                    </td>
                  ))}
                </tr>
              ))
            ) : executions.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-16 text-center">
                  <div className="flex flex-col items-center gap-2 text-muted-fg">
                    <AlertCircle className="w-6 h-6 opacity-40" />
                    <p>No executions match your filters</p>
                  </div>
                </td>
              </tr>
            ) : (
              executions.map(ex => (
                <tr
                  key={ex.id}
                  onClick={() => onRowClick(ex.id)}
                  className={cn(
                    'border-b border-border/50 cursor-pointer group',
                    'hover:bg-muted/40 transition-colors duration-100',
                    ex.status === 'running' && 'bg-accent-dim/10'
                  )}
                >
                  {/* ID */}
                  <td className="px-4 py-3 text-muted-fg whitespace-nowrap">
                    #{ex.id}
                  </td>

                  {/* Agent */}
                  <td className="px-4 py-3">
                    <span className="text-accent font-medium">{ex.agent_name}</span>
                  </td>

                  {/* Task */}
                  <td className="px-4 py-3 max-w-xs">
                    <span className="text-foreground truncate block">
                      {ex.task.slice(0, 70)}{ex.task.length > 70 ? '…' : ''}
                    </span>
                    {ex.error_message && (
                      <span className="text-danger text-[11px] truncate block mt-0.5">
                        ↳ {ex.error_message.slice(0, 60)}
                      </span>
                    )}
                  </td>

                  {/* Status */}
                  <td className="px-4 py-3 whitespace-nowrap">
                    <StatusBadge status={ex.status} />
                  </td>

                  {/* Duration */}
                  <td className="px-4 py-3 text-muted-fg whitespace-nowrap">
                    {formatDuration(ex.created_at, ex.completed_at)}
                  </td>

                  {/* Started */}
                  <td className="px-4 py-3 text-muted-fg whitespace-nowrap">
                    <span title={formatDateTime(ex.created_at)}>
                      {formatDistanceToNow(ex.created_at)}
                    </span>
                  </td>

                  {/* Arrow */}
                  <td className="px-4 py-3">
                    <ArrowRight className="w-3.5 h-3.5 text-muted-fg opacity-0 group-hover:opacity-100 transition-opacity" />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
