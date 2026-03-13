'use client'

import { Activity, CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Stats } from '@/app/dashboard/page'

interface StatCardProps {
  label: string
  value: string | number
  sub?: string
  icon: React.ReactNode
  accent: string
  loading: boolean
}

function StatCard({ label, value, sub, icon, accent, loading }: StatCardProps) {
  return (
    <div className={cn(
      'card flex flex-col gap-3 relative overflow-hidden transition-all duration-200',
      'hover:border-border/80 hover:-translate-y-0.5'
    )}>
      {/* Subtle glow strip */}
      <div className={cn('absolute top-0 left-0 right-0 h-px opacity-60', accent)} />

      <div className="flex items-center justify-between">
        <p className="text-xs font-mono text-muted-fg uppercase tracking-widest">{label}</p>
        <div className={cn('w-7 h-7 rounded-md flex items-center justify-center opacity-70', accent.replace('bg-', 'bg-').replace('-500', '-950'))}>
          {icon}
        </div>
      </div>

      {loading ? (
        <div className="h-8 w-16 bg-muted rounded animate-pulse" />
      ) : (
        <div>
          <p className="text-3xl font-bold font-sans text-foreground">{value}</p>
          {sub && <p className="text-xs font-mono text-muted-fg mt-0.5">{sub}</p>}
        </div>
      )}
    </div>
  )
}

export function StatsGrid({ stats, loading }: { stats: Stats; loading: boolean }) {
  const cards = [
    {
      label: 'Total Runs',
      value: stats.total,
      sub: 'all time',
      icon: <Activity className="w-3.5 h-3.5 text-foreground" />,
      accent: 'bg-foreground',
    },
    {
      label: 'Completed',
      value: stats.completed,
      sub: `${stats.successRate}% success rate`,
      icon: <CheckCircle2 className="w-3.5 h-3.5 text-success" />,
      accent: 'bg-success',
    },
    {
      label: 'Running',
      value: stats.running,
      sub: stats.running > 0 ? 'in progress' : 'none active',
      icon: <Loader2 className="w-3.5 h-3.5 text-accent" />,
      accent: 'bg-accent',
    },
    {
      label: 'Pending',
      value: stats.pending,
      sub: 'queued',
      icon: <Clock className="w-3.5 h-3.5 text-warning" />,
      accent: 'bg-warning',
    },
    {
      label: 'Failed',
      value: stats.failed,
      sub: stats.total > 0 ? `${Math.round((stats.failed / stats.total) * 100)}% error rate` : '—',
      icon: <XCircle className="w-3.5 h-3.5 text-danger" />,
      accent: 'bg-danger',
    },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
      {cards.map(c => (
        <StatCard key={c.label} {...c} loading={loading} />
      ))}
    </div>
  )
}
