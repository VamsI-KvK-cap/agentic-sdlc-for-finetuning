'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { api } from '@/lib/api'
import type { Execution, ExecutionStatus } from '@/lib/types'
import { ExecutionsTable } from '@/components/executions/ExecutionsTable'
import { ExecutionsFilter } from '@/components/executions/ExecutionsFilter'
import { Pagination } from '@/components/executions/Pagination'
import { RefreshCw } from 'lucide-react'

const PAGE_SIZE = 15

export default function ExecutionsPage() {
  const router       = useRouter()
  const searchParams = useSearchParams()

  const [executions, setExecutions] = useState<Execution[]>([])
  const [total,      setTotal]      = useState(0)
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState<string | null>(null)

  const page       = parseInt(searchParams.get('page') ?? '1', 10)
  const agentFilter  = searchParams.get('agent') ?? ''
  const statusFilter = (searchParams.get('status') ?? '') as ExecutionStatus | ''

  const fetch = useCallback(() => {
    setLoading(true)
    setError(null)
    api.executions
      .list({
        skip:       (page - 1) * PAGE_SIZE,
        limit:      PAGE_SIZE,
        agent_name: agentFilter || undefined,
        status:     statusFilter || undefined,
      })
      .then(res => {
        setExecutions(res.executions)
        setTotal(res.total)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [page, agentFilter, statusFilter])

  useEffect(() => { fetch() }, [fetch])

  const setParam = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString())
    if (value) params.set(key, value)
    else params.delete(key)
    params.delete('page')
    router.push(`/executions?${params.toString()}`)
  }

  const setPage = (p: number) => {
    const params = new URLSearchParams(searchParams.toString())
    params.set('page', String(p))
    router.push(`/executions?${params.toString()}`)
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="max-w-7xl mx-auto space-y-5">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold font-sans text-foreground tracking-tight">
            Executions
          </h2>
          <p className="text-sm font-mono text-muted-fg mt-0.5">
            {loading ? '—' : `${total} total run${total !== 1 ? 's' : ''}`}
          </p>
        </div>
        <button
          onClick={fetch}
          disabled={loading}
          className="btn-ghost flex items-center gap-2"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <ExecutionsFilter
        agentFilter={agentFilter}
        statusFilter={statusFilter}
        onAgentChange={v => setParam('agent', v)}
        onStatusChange={v => setParam('status', v)}
        onClear={() => router.push('/executions')}
      />

      {/* Error */}
      {error && (
        <div className="card border-danger/40 bg-red-950/20 text-danger text-sm font-mono">
          ⚠ {error}
        </div>
      )}

      {/* Table */}
      <ExecutionsTable
        executions={executions}
        loading={loading}
        onRowClick={id => router.push(`/executions/${id}`)}
      />

      {/* Pagination */}
      {totalPages > 1 && (
        <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
      )}
    </div>
  )
}
