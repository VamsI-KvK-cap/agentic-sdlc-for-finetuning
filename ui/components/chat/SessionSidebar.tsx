'use client'

import { Plus, Trash2, MessageSquare } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatDistanceToNow } from '@/lib/time'
import type { Session } from '@/lib/chat-types'

interface Props {
  sessions: Session[]
  activeId: string
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
}

export function SessionSidebar({ sessions, activeId, onSelect, onNew, onDelete }: Props) {
  return (
    <aside className="w-56 flex-shrink-0 flex flex-col border-r border-border bg-surface overflow-hidden">

      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3 border-b border-border">
        <p className="text-[10px] font-mono text-muted-fg uppercase tracking-widest">Sessions</p>
        <button
          onClick={onNew}
          className="w-6 h-6 rounded flex items-center justify-center text-muted-fg hover:text-accent hover:bg-accent-dim transition-all duration-150"
          title="New conversation"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto py-1">
        {sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-muted-fg px-4">
            <MessageSquare className="w-5 h-5 opacity-30" />
            <p className="text-xs font-mono text-center">No sessions yet</p>
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
        'group relative flex flex-col gap-0.5 px-3 py-2.5 cursor-pointer mx-1 rounded-md transition-all duration-150',
        active
          ? 'bg-accent-dim border border-accent/20'
          : 'hover:bg-muted border border-transparent'
      )}
    >
      <div className="flex items-start justify-between gap-1">
        <p className={cn(
          'text-xs font-mono truncate flex-1',
          active ? 'text-accent' : 'text-foreground'
        )}>
          {session.title}
        </p>
        <button
          onClick={e => { e.stopPropagation(); onDelete(session.id) }}
          className="opacity-0 group-hover:opacity-100 text-muted-fg hover:text-danger transition-all flex-shrink-0"
        >
          <Trash2 className="w-2.5 h-2.5" />
        </button>
      </div>

      {session.preview && (
        <p className="text-[11px] font-mono text-muted-fg truncate">
          {session.preview}
        </p>
      )}

      <p className="text-[10px] font-mono text-muted-fg/60">
        {formatDistanceToNow(session.updatedAt)}
        {' · '}
        {session.messageCount} msg{session.messageCount !== 1 ? 's' : ''}
      </p>
    </div>
  )
}
