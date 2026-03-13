'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { Execution } from '@/lib/types'
import { StatsGrid } from '@/components/dashboard/StatsGrid'
import { ExecutionPieChart } from '@/components/dashboard/ExecutionPieChart'
import { RecentExecutions } from '@/components/dashboard/RecentExecutions'
import { ActivityFeed } from '@/components/dashboard/ActivityFeed'

export interface Stats {
  total: number
  completed: number
  failed: number
  running: number
  pending: number
  successRate: number
}

function computeStats(executions: Execution[]): Stats {
  const total = executions.length
  const completed = executions.filter(e => e.status === 'completed').length
  const failed = executions.filter(e => e.status === 'failed').length
  const running = executions.filter(e => e.status === 'running').length
  const pending = executions.filter(e => e.status === 'pending').length
  const successRate = total > 0 ? Math.round((completed / total) * 100) : 0
  return { total, completed, failed, running, pending, successRate }
}

export default function DashboardPage() {
  const [executions, setExecutions] = useState<Execution[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.executions
      .list({ limit: 100 })
      .then(res => setExecutions(res.executions))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const stats = computeStats(executions)

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-2xl font-bold font-sans text-foreground tracking-tight">
            System Overview
          </h2>
          <p className="text-sm font-mono text-muted-fg mt-0.5">
            Real-time snapshot of all agent executions
          </p>
        </div>
        {!loading && (
          <p className="text-xs font-mono text-muted-fg">
            Last updated: {new Date().toLocaleTimeString()}
          </p>
        )}
      </div>

      {error && (
        <div className="card border-danger/40 bg-red-950/20 text-danger text-sm font-mono">
          ⚠ Could not reach API — {error}
        </div>
      )}

      <StatsGrid stats={stats} loading={loading} />

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        <div className="lg:col-span-2">
          <ExecutionPieChart stats={stats} loading={loading} />
        </div>
        <div className="lg:col-span-3">
          <ActivityFeed executions={executions} loading={loading} />
        </div>
      </div>

      <RecentExecutions executions={executions.slice(0, 10)} loading={loading} />
    </div>
  )
}
