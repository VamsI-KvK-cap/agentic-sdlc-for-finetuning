'use client'

import { Key, Brain, Bot, Database, Info } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SettingsTab } from '@/app/settings/page'

const TABS: { id: SettingsTab; label: string; icon: React.ReactNode; badge?: string }[] = [
  { id: 'api',      label: 'API Keys',     icon: <Key      className="w-3.5 h-3.5" /> },
  { id: 'models',   label: 'Models',       icon: <Brain    className="w-3.5 h-3.5" /> },
  { id: 'agents',   label: 'Agents',       icon: <Bot      className="w-3.5 h-3.5" /> },
  { id: 'database', label: 'Database',     icon: <Database className="w-3.5 h-3.5" /> },
  { id: 'about',    label: 'About',        icon: <Info     className="w-3.5 h-3.5" /> },
]

export function SettingsNav({
  active,
  onChange,
}: {
  active: SettingsTab
  onChange: (t: SettingsTab) => void
}) {
  return (
    <nav className="w-44 flex-shrink-0 flex flex-col gap-0.5">
      {TABS.map(tab => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={cn(
            'flex items-center gap-2.5 px-3 py-2.5 rounded-md text-sm font-mono text-left transition-all duration-150',
            active === tab.id
              ? 'bg-accent-dim text-accent'
              : 'text-muted-fg hover:text-foreground hover:bg-muted'
          )}
        >
          {tab.icon}
          {tab.label}
          {tab.badge && (
            <span className="ml-auto text-[10px] bg-warning/20 text-warning border border-warning/30 rounded px-1">
              {tab.badge}
            </span>
          )}
        </button>
      ))}
    </nav>
  )
}
