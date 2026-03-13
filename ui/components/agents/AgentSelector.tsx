'use client'

import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Bot, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Agent } from '@/lib/types'

interface Props {
  agents: Agent[]
  loading: boolean
  value: string
  onChange: (v: string) => void
}

export function AgentSelector({ agents, loading, value, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const selected = agents.find(a => a.name === value)

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  if (loading) {
    return <div className="h-10 bg-muted rounded-md animate-pulse w-full" />
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className={cn(
          'input flex items-center justify-between text-left',
          open && 'border-accent ring-1 ring-accent'
        )}
      >
        <div className="flex items-center gap-2.5">
          <Bot className="w-3.5 h-3.5 text-accent flex-shrink-0" />
          {selected ? (
            <span className="text-foreground">
              {/* {selected.language} */}
              {selected.name}
              <span className="text-muted-fg ml-2 text-[11px]">— {selected.description}</span>
            </span>
          ) : (
            <span className="text-muted-fg">Select an agent…</span>
          )}
        </div>
        <ChevronDown className={cn('w-3.5 h-3.5 text-muted-fg transition-transform duration-150', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-surface border border-border rounded-md shadow-xl overflow-hidden animate-fade-in">
          {agents.map(agent => (
            <button
              key={agent.name}
              type="button"
              onClick={() => { onChange(agent.name); setOpen(false) }}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-muted transition-colors',
                agent.name === value && 'bg-accent-dim'
              )}
            >
              <div className="w-6 h-6 rounded bg-accent-dim border border-accent/30 flex items-center justify-center flex-shrink-0">
                <Bot className="w-3 h-3 text-accent" />
              </div>
              <div className="flex-1 min-w-0">
                {/* <p className="text-sm font-mono text-foreground">{agent.language}</p> */}
                <p className="text-sm font-mono text-foreground">{agent.name}</p>
                <p className="text-[11px] font-mono text-muted-fg">{agent.description}</p>
              </div>
              {agent.name === value && (
                <Check className="w-3.5 h-3.5 text-accent flex-shrink-0" />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
