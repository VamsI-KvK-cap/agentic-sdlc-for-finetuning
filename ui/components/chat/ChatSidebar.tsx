'use client'

import { Plus, MessageSquare, Trash2, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatDistanceToNow } from '@/lib/time'
import type { Session } from '@/lib/chat-types'

interface Props {
  sessions: Session[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
}

export function ChatSidebar({ sessions, activeId, onSelect, onNew, onDelete }: Props) {
  return (
    <aside className="w-56 flex-shrink-0 flex flex-col border-r border-border bg-surface">

      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3 border-b border-border">
        <p className="text-[10px] font-mono text-muted-fg uppercase tracking-widest">
          Sessions
        </p>
        <button
          onClick={onNew}
          className="w-6 h-6 rounded flex items-center justify-center text-muted-fg hover:text-accent hover:bg-accent-dim transition-all duration-150"
          title="New session"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto py-2">
        {sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-24 gap-2 text-muted-fg">
            <MessageSquare className="w-5 h-5 opacity-30" />
            <p className="text-[11px] font-mono">No sessions yet</p>
          </div>
        ) : (
          sessions.map(session => (
            <SessionItem
              key={session.id}
              session={session}
              active={session.id === activeId}
              onSelect={() => onSelect(session.id)}
              onDelete={() => onDelete(session.id)}
            />
          ))
        )}
      </div>

      {/* Footer note */}
      <div className="px-3 py-2.5 border-t border-border">
        <p className="text-[10px] font-mono text-muted-fg leading-relaxed">
          Sessions persist via LangGraph long-term memory
          <span className="ml-1 text-warning">— coming soon</span>
        </p>
      </div>
    </aside>
  )
}

function SessionItem({
  session,
  active,
  onSelect,
  onDelete,
}: {
  session: Session
  active: boolean
  onSelect: () => void
  onDelete: () => void
}) {
  return (
    <div
      onClick={onSelect}
      className={cn(
        'group flex items-start gap-2 px-3 py-2.5 mx-1 rounded-md cursor-pointer transition-all duration-150',
        active
          ? 'bg-accent-dim text-foreground'
          : 'text-muted-fg hover:bg-muted hover:text-foreground'
      )}
    >
      <MessageSquare className={cn(
        'w-3.5 h-3.5 flex-shrink-0 mt-0.5',
        active ? 'text-accent' : 'text-muted-fg'
      )} />

      <div className="flex-1 min-w-0">
        <p className={cn(
          'text-xs font-mono truncate',
          active ? 'text-foreground' : 'text-muted-fg group-hover:text-foreground'
        )}>
          {session.title}
        </p>
        <div className="flex items-center gap-1 mt-0.5">
          <Clock className="w-2.5 h-2.5 text-muted-fg/60" />
          <p className="text-[10px] font-mono text-muted-fg/60">
            {formatDistanceToNow(session.createdAt)}
          </p>
        </div>
      </div>

      {/* Delete button — visible on hover */}
      <button
        onClick={e => { e.stopPropagation(); onDelete(session.id) }}
        className="opacity-0 group-hover:opacity-100 text-muted-fg hover:text-danger transition-all duration-150 flex-shrink-0"
      >
        <Trash2 className="w-3 h-3" />
      </button>
    </div>
  )
}
