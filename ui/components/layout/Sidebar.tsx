'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Bot,
  ListChecks,
  MessageSquare,
  Settings,
  Zap,
} from 'lucide-react'
import { clsx } from 'clsx'

const NAV_ITEMS = [
  { href: '/dashboard',   label: 'Dashboard',   icon: LayoutDashboard },
  { href: '/agents',      label: 'Agents',       icon: Bot },
  { href: '/executions',  label: 'Executions',   icon: ListChecks },
  { href: '/chat',        label: 'Chat',         icon: MessageSquare },
  { href: '/settings',    label: 'Settings',     icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-56 flex-shrink-0 flex flex-col border-r border-border bg-surface">

      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 py-5 border-b border-border">
        <div className="w-7 h-7 rounded-md bg-accent flex items-center justify-center">
          <Zap className="w-4 h-4 text-background" strokeWidth={2.5} />
        </div>
        <div>
          <p className="text-sm font-bold font-sans tracking-tight text-foreground">Agentic</p>
          {/* <p className="text-[10px] font-mono text-muted-fg -mt-0.5 uppercase tracking-widest">SDLC</p> */}
          <p className="text-[11px] font-bold -mt-0.5 uppercase tracking-widest">SDLC</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-4 flex flex-col gap-0.5">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              className={clsx('nav-item', active && 'active')}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Bottom tag */}
      <div className="px-4 py-3 border-t border-border">
        <p className="text-[10px] font-mono text-muted-fg">v0.1.0 · dev</p>
      </div>
    </aside>
  )
}
