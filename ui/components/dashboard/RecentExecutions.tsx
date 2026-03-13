'use client'

import Link from 'next/link'
import type { Execution } from '@/lib/types'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatDistanceToNow } from '@/lib/time'
import { ArrowRight } from 'lucide-react'

export function RecentExecutions({
  executions,
  loading,
}: {
  executions: Execution[]
  loading: boolean
}) {
  return (
    <div className="card flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-mono text-muted-fg uppercase tracking-widest">History</p>
          <p className="text-sm font-semibold font-sans text-foreground mt-0.5">Recent Executions</p>
        </div>
        <Link href="/executions" className="btn-ghost flex items-center gap-1.5 text-xs">
          View all <ArrowRight className="w-3 h-3" />
        </Link>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="border-b border-border">
              {['ID', 'Agent', 'Task', 'Status', 'Started', ''].map(h => (
                <th
                  key={h}
                  className="text-left text-muted-fg uppercase tracking-widest pb-2 pr-4 font-medium"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-border/50">
                  {Array.from({ length: 5 }).map((_, j) => (
                    <td key={j} className="py-3 pr-4">
                      <div className="h-3 bg-muted rounded animate-pulse w-full max-w-[120px]" />
                    </td>
                  ))}
                </tr>
              ))
            ) : executions.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-muted-fg">
                  No executions yet — trigger one from the Agents page
                </td>
              </tr>
            ) : (
              executions.map(ex => (
                <tr
                  key={ex.id}
                  className="border-b border-border/50 hover:bg-muted/40 transition-colors group"
                >
                  <td className="py-3 pr-4 text-muted-fg">#{ex.id}</td>
                  <td className="py-3 pr-4 text-accent">{ex.agent_name}</td>
                  <td className="py-3 pr-4 text-foreground max-w-xs">
                    <span className="truncate block">
                      {ex.task.slice(0, 55)}{ex.task.length > 55 ? '…' : ''}
                    </span>
                  </td>
                  <td className="py-3 pr-4">
                    <StatusBadge status={ex.status} />
                  </td>
                  <td className="py-3 pr-4 text-muted-fg">
                    {formatDistanceToNow(ex.created_at)}
                  </td>
                  <td className="py-3">
                    <Link
                      href={`/executions/${ex.id}`}
                      className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-fg hover:text-accent"
                    >
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
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
