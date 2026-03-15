import type {
  Execution,
  ExecutionListResponse,
  ExecutionListParams,
  CreateExecutionPayload,
  CreateExecutionFromGitPayload,
  Agent,
  ApiKeySettings,
  ModelSettings,
  AgentSettings,
  HealthResponse,
} from './types'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// ── Core fetch wrapper ─────────────────────────────────────────────────────

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    let message = text
    try { message = JSON.parse(text)?.detail ?? text } catch {}
    const err = new Error(message) as Error & { status: number }
    err.status = res.status
    throw err
  }
  return res.json()
}

// ── API client ─────────────────────────────────────────────────────────────

export const api = {

  // ── Health ────────────────────────────────────────────────────────────────
  health: () =>
    request<HealthResponse>('/health'),

  // ── Executions ────────────────────────────────────────────────────────────
  executions: {

    // Greenfield — plain task description, no existing code
    create: (payload: CreateExecutionPayload) =>
      request<Execution>('/api/v1/executions', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    // Brownfield — zip archive of existing codebase
    // CONCEPT: FormData is used for multipart/form-data uploads.
    // We cannot use JSON here because JSON cannot carry binary file data.
    // FastAPI reads the form fields (agent_name, task) and the file part
    // separately from the same multipart request.
    // Note: do NOT set Content-Type header manually — fetch sets it
    // automatically with the correct multipart boundary when given FormData.
    createFromZip: async (
      agentName: string,
      task: string,
      file: File,
    ): Promise<Execution> => {
      const form = new FormData()
      form.append('agent_name', agentName)
      form.append('task', task)
      form.append('file', file)

      const res = await fetch(`${BASE_URL}/api/v1/executions/from-zip`, {
        method: 'POST',
        body: form,
        // No Content-Type header — fetch sets multipart/form-data + boundary automatically
      })

      if (!res.ok) {
        const text = await res.text()
        let message = text
        try { message = JSON.parse(text)?.detail ?? text } catch {}
        throw new Error(message)
      }
      return res.json()
    },

    // Brownfield — public Git repository URL
    createFromGit: (payload: CreateExecutionFromGitPayload) =>
      request<Execution>('/api/v1/executions/from-git', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    list: (params?: ExecutionListParams) => {
      const qs = new URLSearchParams()
      if (params?.skip      !== undefined) qs.set('skip',       String(params.skip))
      if (params?.limit     !== undefined) qs.set('limit',      String(params.limit))
      if (params?.agent_name)              qs.set('agent_name', params.agent_name)
      if (params?.status)                  qs.set('status',     params.status)
      const query = qs.toString() ? `?${qs.toString()}` : ''
      return request<ExecutionListResponse>(`/api/v1/executions${query}`)
    },

    get: (id: number) =>
      request<Execution>(`/api/v1/executions/${id}`),

    // Artifact download — binary response, cannot use request<T>()
    downloadArtifacts: async (id: number): Promise<void> => {
      const res = await fetch(
        `${BASE_URL}/api/v1/executions/${id}/download`,
        { method: 'GET' }
      )
      if (!res.ok) {
        const text = await res.text()
        let message = text
        try { message = JSON.parse(text)?.detail ?? text } catch {}
        throw new Error(message)
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const disposition = res.headers.get('Content-Disposition') ?? ''
      const match = disposition.match(/filename=(.+)/)
      const filename = match ? match[1] : `execution_${id}_artifacts.zip`
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    },
  },

  // ── Agents ────────────────────────────────────────────────────────────────
  agents: {
    list: () => request<Agent[]>('/api/v1/agents'),
  },

  // ── Settings (stubbed — backend not yet wired) ────────────────────────────
  settings: {
    getApiKeys: () =>
      request<ApiKeySettings>('/api/v1/settings/api-keys'),
    saveApiKeys: (payload: ApiKeySettings) =>
      request<void>('/api/v1/settings/api-keys', { method: 'POST', body: JSON.stringify(payload) }),
    getModels: () =>
      request<ModelSettings>('/api/v1/settings/models'),
    saveModels: (payload: ModelSettings) =>
      request<void>('/api/v1/settings/models', { method: 'POST', body: JSON.stringify(payload) }),
    getAgents: () =>
      request<AgentSettings[]>('/api/v1/settings/agents'),
    saveAgents: (payload: AgentSettings[]) =>
      request<void>('/api/v1/settings/agents', { method: 'POST', body: JSON.stringify(payload) }),
  },

  // ── SSE stream ────────────────────────────────────────────────────────────
  streamExecution: (id: number) =>
    new EventSource(`${BASE_URL}/api/v1/executions/${id}/stream`),
}
