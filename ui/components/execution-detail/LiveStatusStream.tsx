'use client'

import { useEffect, useRef } from 'react'
import { Radio, CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react'
import type { Execution, SSEEvent } from '@/lib/types'
import { formatDistanceToNow } from '@/lib/time'
import { cn } from '@/lib/utils'

interface Props {
  execution: Execution
  events: SSEEvent[]
  streaming: boolean
}

const STATUS_ICONS = {
  pending:   <Clock className="w-3.5 h-3.5 text-muted-fg" />,
  running:   <Loader2 className="w-3.5 h-3.5 text-accent animate-spin" />,
  completed: <CheckCircle2 className="w-3.5 h-3.5 text-success" />,
  failed:    <XCircle className="w-3.5 h-3.5 text-danger" />,
}

const STATUS_MESSAGES: Record<string, string[]> = {
  pending:   ['Execution queued, waiting to start…'],
  running:   ['Agent initialising…', 'Analysing task…', 'Planning file structure…', 'Generating code…', 'Running static checks…'],
  completed: ['All files written successfully.', 'Static analysis passed.', 'Execution completed.'],
  failed:    ['Execution encountered an error.', 'See error details on the left.'],
}

export function LiveStatusStream({ execution, events, streaming }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  // Build a unified list of log lines from SSE events
  const logLines = buildLogLines(execution, events)

  return (
    <div className="card flex flex-col h-full min-h-[420px]">

      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Radio className="w-3.5 h-3.5 text-muted-fg" />
          <p className="text-[10px] font-mono text-muted-fg uppercase tracking-widest">
            Live Stream
          </p>
        </div>
        <div className="flex items-center gap-2">
          {streaming ? (
            <span className="flex items-center gap-1.5 text-[11px] font-mono text-accent">
              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-dot" />
              Streaming
            </span>
          ) : (
            <span className="text-[11px] font-mono text-muted-fg">
              {events.length > 0 ? 'Stream closed' : 'No stream'}
            </span>
          )}
        </div>
      </div>

      {/* Log window */}
      <div className="flex-1 overflow-y-auto mt-4 space-y-0 font-mono text-xs">

        {/* Static context line */}
        <LogLine
          time={execution.created_at}
          icon={<span className="w-3.5 h-3.5 flex items-center justify-center text-muted-fg text-[10px]">→</span>}
          message={`Execution #${execution.id} triggered · agent: ${execution.agent_name}`}
          dim
        />

        {/* Synthetic progress lines based on status transitions */}
        {logLines.map((line, i) => (
          <LogLine
            key={i}
            time={line.time}
            icon={STATUS_ICONS[line.status] ?? STATUS_ICONS.pending}
            message={line.message}
            status={line.status}
            isLatest={i === logLines.length - 1}
          />
        ))}

        {/* Live typing indicator while streaming */}
        {streaming && (
          <div className="flex items-center gap-3 py-2 px-1">
            <span className="w-3.5 h-3.5 flex items-center justify-center flex-shrink-0">
              <Loader2 className="w-3 h-3 text-accent animate-spin" />
            </span>
            <span className="text-muted-fg flex items-center gap-1">
              <TypingDots />
            </span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Footer */}
      <div className="pt-4 border-t border-border mt-4 flex items-center justify-between">
        <p className="text-[11px] font-mono text-muted-fg">
          {events.length} event{events.length !== 1 ? 's' : ''} received
        </p>
        <p className="text-[11px] font-mono text-muted-fg">
          Status: <span className={cn(
            execution.status === 'completed' && 'text-success',
            execution.status === 'failed'    && 'text-danger',
            execution.status === 'running'   && 'text-accent',
            execution.status === 'pending'   && 'text-muted-fg',
          )}>{execution.status}</span>
        </p>
      </div>
    </div>
  )
}

// ── Helpers ────────────────────────────────────────────────────────────────

interface LogEntry {
  time: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  message: string
}

function buildLogLines(execution: Execution, events: SSEEvent[]): LogEntry[] {
  if (events.length === 0) {
    // No SSE events yet — synthesise from current execution state
    const msgs = STATUS_MESSAGES[execution.status] ?? []
    return msgs.map(message => ({
      time: execution.updated_at,
      status: execution.status as LogEntry['status'],
      message,
    }))
  }

  const lines: LogEntry[] = []
  let lastStatus = ''

  for (const event of events) {
    if (event.status !== lastStatus) {
      const msgs = STATUS_MESSAGES[event.status] ?? [`Status: ${event.status}`]
      msgs.forEach(message => {
        lines.push({ time: event.updated_at, status: event.status as LogEntry['status'], message })
      })
      lastStatus = event.status
    }
  }

  return lines
}

// ── Sub-components ─────────────────────────────────────────────────────────

interface LogLineProps {
  time: string
  icon: React.ReactNode
  message: string
  status?: string
  dim?: boolean
  isLatest?: boolean
}

function LogLine({ time, icon, message, status, dim, isLatest }: LogLineProps) {
  return (
    <div className={cn(
      'flex items-start gap-3 py-1.5 px-1 rounded transition-colors',
      isLatest && 'bg-muted/30',
      dim && 'opacity-50'
    )}>
      <span className="w-3.5 h-3.5 flex items-center justify-center flex-shrink-0 mt-0.5">
        {icon}
      </span>
      <span className={cn(
        'flex-1',
        status === 'completed' && 'text-success',
        status === 'failed'    && 'text-danger',
        status === 'running'   && 'text-foreground',
        (!status || dim)       && 'text-muted-fg',
      )}>
        {message}
      </span>
      <span className="text-[10px] text-muted-fg/60 flex-shrink-0 mt-0.5 tabular-nums">
        {formatDistanceToNow(time)}
      </span>
    </div>
  )
}

function TypingDots() {
  return (
    <span className="flex gap-0.5 items-center h-3.5">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="w-1 h-1 rounded-full bg-accent animate-pulse-dot"
          style={{ animationDelay: `${i * 0.2}s` }}
        />
      ))}
    </span>
  )
}
