'use client'

import { useState, useEffect, useCallback } from 'react'
import { api } from '@/lib/api'
import type { Execution, ExecutionListParams, ExecutionStatus } from '@/lib/types'

// ── useExecutions — paginated list ─────────────────────────────────────────

export function useExecutions(params?: ExecutionListParams) {
  const [executions, setExecutions] = useState<Execution[]>([])
  const [total,      setTotal]      = useState(0)
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState<string | null>(null)

  const fetch = useCallback(() => {
    setLoading(true)
    setError(null)
    api.executions
      .list(params)
      .then(res => { setExecutions(res.executions); setTotal(res.total) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [JSON.stringify(params)])

  useEffect(() => { fetch() }, [fetch])

  return { executions, total, loading, error, refetch: fetch }
}

// ── useExecution — single execution with optional SSE ─────────────────────

export function useExecution(id: number) {
  const [execution, setExecution] = useState<Execution | null>(null)
  const [events,    setEvents]    = useState<any[]>([])
  const [streaming, setStreaming] = useState(false)
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    api.executions
      .get(id)
      .then(data => {
        setExecution(data)
        if (data.status === 'pending' || data.status === 'running') {
          setStreaming(true)
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    if (!streaming) return
    const es = api.streamExecution(id)
    es.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data)
        setEvents(prev => [...prev, event])
        setExecution(prev => prev ? {
          ...prev,
          status:        event.status,
          updated_at:    event.updated_at,
          completed_at:  event.completed_at,
          error_message: event.error_message,
        } : prev)
        if (event.status === 'completed' || event.status === 'failed') {
          setStreaming(false)
          es.close()
        }
      } catch {}
    }
    es.onerror = () => { setStreaming(false); es.close() }
    return () => es.close()
  }, [streaming, id])

  return { execution, events, streaming, loading, error }
}

// ── useAgents — available agent list ──────────────────────────────────────

export function useAgents() {
  const [agents,  setAgents]  = useState<{ name: string; language: string; description: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  useEffect(() => {
    api.agents
      .list()
      .then(setAgents)
      .catch(err => {
        setError(err.message)
        // Fallback so the page never breaks
        setAgents([{ name: 'python', language: 'Python', description: 'Python coding agent' }])
      })
      .finally(() => setLoading(false))
  }, [])

  return { agents, loading, error }
}

// ── useDashboardStats — aggregated stats for dashboard ────────────────────

export function useDashboardStats() {
  const { executions, loading, error } = useExecutions({ limit: 100 })

  const stats = {
    total:       executions.length,
    completed:   executions.filter(e => e.status === 'completed').length,
    failed:      executions.filter(e => e.status === 'failed').length,
    running:     executions.filter(e => e.status === 'running').length,
    pending:     executions.filter(e => e.status === 'pending').length,
    successRate: executions.length > 0
      ? Math.round((executions.filter(e => e.status === 'completed').length / executions.length) * 100)
      : 0,
  }

  return { stats, executions, loading, error }
}
