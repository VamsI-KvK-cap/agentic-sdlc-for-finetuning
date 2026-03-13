'use client'

import { useEffect, useRef } from 'react'
import { Bot, User, FileText, Image } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatDistanceToNow } from '@/lib/time'
import type { Message, Attachment } from '@/lib/chat-types'

interface Props {
  messages: Message[]
  loading: boolean
}

export function ChatWindow({ messages, loading }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  return (
    <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
      {messages.map(msg => (
        <MessageBubble key={msg.id} message={msg} />
      ))}

      {/* Thinking indicator */}
      {loading && (
        <div className="flex items-start gap-3">
          <Avatar role="assistant" />
          <div className="flex items-center gap-1.5 bg-surface border border-border rounded-lg px-4 py-3">
            {[0, 1, 2].map(i => (
              <span
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-dot"
                style={{ animationDelay: `${i * 0.18}s` }}
              />
            ))}
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex items-start gap-3', isUser && 'flex-row-reverse')}>
      <Avatar role={message.role} />

      <div className={cn('flex flex-col gap-1 max-w-[75%]', isUser && 'items-end')}>
        <div className={cn(
          'rounded-lg px-4 py-3 text-sm font-mono leading-relaxed',
          isUser
            ? 'bg-accent-dim border border-accent/30 text-foreground'
            : 'bg-surface border border-border text-foreground'
        )}>
          <MessageContent content={message.content} />
        </div>

        {message.attachments.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-1">
            {message.attachments.map((att, i) => (
              <AttachmentChip key={i} attachment={att} />
            ))}
          </div>
        )}

        <p className="text-[10px] font-mono text-muted-fg/60 px-1">
          {formatDistanceToNow(message.createdAt)}
        </p>
      </div>
    </div>
  )
}

function MessageContent({ content }: { content: string }) {
  const parts = content.split(/(```[\s\S]*?```)/g)
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('```')) {
          const code = part.replace(/^```\w*\n?/, '').replace(/```$/, '')
          return (
            <pre key={i} className="mt-2 mb-2 bg-background rounded p-3 text-xs overflow-x-auto border border-border">
              <code>{code}</code>
            </pre>
          )
        }
        return (
          <span key={i}>
            {part.split('\n').map((line, j, arr) => (
              <span key={j}>{line}{j < arr.length - 1 && <br />}</span>
            ))}
          </span>
        )
      })}
    </>
  )
}

function AttachmentChip({ attachment }: { attachment: Attachment }) {
  const isImage = attachment.type.startsWith('image/')
  return (
    <div className="flex items-center gap-1.5 bg-muted border border-border rounded px-2 py-1 text-[11px] font-mono text-muted-fg">
      {isImage
        ? <Image className="w-3 h-3 text-accent" />
        : <FileText className="w-3 h-3 text-accent" />
      }
      <span className="max-w-[120px] truncate">{attachment.name}</span>
      <span className="text-muted-fg/50">{(attachment.size / 1024).toFixed(0)}KB</span>
    </div>
  )
}

function Avatar({ role }: { role: 'user' | 'assistant' }) {
  return (
    <div className={cn(
      'w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 border',
      role === 'assistant' ? 'bg-accent-dim border-accent/30' : 'bg-muted border-border'
    )}>
      {role === 'assistant'
        ? <Bot className="w-3.5 h-3.5 text-accent" />
        : <User className="w-3.5 h-3.5 text-muted-fg" />
      }
    </div>
  )
}
