'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { api } from '@/lib/api'
import type { Execution, SSEEvent } from '@/lib/types'
import { ExecutionHeader } from '@/components/execution-detail/ExecutionHeader'
import { ExecutionMeta } from '@/components/execution-detail/ExecutionMeta'
import { LiveStatusStream } from '@/components/execution-detail/LiveStatusStream'
import { TaskCard } from '@/components/execution-detail/TaskCard'
import { ErrorCard } from '@/components/execution-detail/ErrorCard'

export default function ExecutionDetailPage() {
  const { id }   = useParams<{ id: string }>()
  const router   = useRouter()
  const execId   = parseInt(id, 10)

  const [execution, setExecution]   = useState<Execution | null>(null)
  const [events,    setEvents]      = useState<SSEEvent[]>([])
  const [streaming, setStreaming]   = useState(false)
  const [loading,   setLoading]     = useState(true)
  const [error,     setError]       = useState<string | null>(null)

  // Initial fetch
  useEffect(() => {
    api.executions
      .get(execId)
      .then(data => {
        setExecution(data)
        // Only open SSE if execution is still active
        if (data.status === 'pending' || data.status === 'running') {
          setStreaming(true)
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [execId])

  // SSE stream
  useEffect(() => {
    if (!streaming) return

    const es = api.streamExecution(execId)

    es.onmessage = (e) => {
      try {
        const event: SSEEvent = JSON.parse(e.data)
        setEvents(prev => [...prev, event])
        setExecution(prev => prev ? {
          ...prev,
          status:       event.status,
          updated_at:   event.updated_at,
          completed_at: event.completed_at,
          error_message: event.error_message,
        } : prev)

        if (event.status === 'completed' || event.status === 'failed') {
          setStreaming(false)
          es.close()
        }
      } catch {}
    }

    es.onerror = () => {
      setStreaming(false)
      es.close()
    }

    return () => es.close()
  }, [streaming, execId])

  if (loading) return <DetailSkeleton />

  if (error || !execution) return (
    <div className="max-w-3xl mx-auto">
      <div className="card border-danger/40 bg-red-950/20 text-danger font-mono text-sm">
        ⚠ {error ?? 'Execution not found'}
      </div>
    </div>
  )

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <ExecutionHeader
        execution={execution}
        onBack={() => router.push('/executions')}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left col — task + error */}
        <div className="lg:col-span-1 space-y-5">
          <TaskCard task={execution.task} />
          {execution.error_message && (
            <ErrorCard message={execution.error_message} />
          )}
          <ExecutionMeta execution={execution} />
        </div>

        {/* Right col — live stream */}
        <div className="lg:col-span-2">
          <LiveStatusStream
            execution={execution}
            events={events}
            streaming={streaming}
          />
        </div>
      </div>
    </div>
  )
}

function DetailSkeleton() {
  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <div className="flex items-center gap-4">
        <div className="w-24 h-8 bg-muted rounded animate-pulse" />
        <div className="w-48 h-8 bg-muted rounded animate-pulse" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="space-y-5">
          <div className="card h-40 animate-pulse bg-muted" />
          <div className="card h-24 animate-pulse bg-muted" />
        </div>
        <div className="lg:col-span-2 card h-96 animate-pulse bg-muted" />
      </div>
    </div>
  )
}
