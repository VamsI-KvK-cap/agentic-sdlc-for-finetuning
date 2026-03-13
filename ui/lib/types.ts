// ── Shared ─────────────────────────────────────────────────────────────────

export interface ApiError {
  status: number
  message: string
}

// ── Executions ─────────────────────────────────────────────────────────────

export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface Execution {
  id: number
  agent_name: string
  status: ExecutionStatus
  task: string
  error_message: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
}

export interface ExecutionListResponse {
  total: number
  executions: Execution[]
}

export interface CreateExecutionPayload {
  agent_name: string
  task: string
}

export interface ExecutionListParams {
  skip?: number
  limit?: number
  agent_name?: string
  status?: ExecutionStatus
}

// ── SSE ────────────────────────────────────────────────────────────────────

export interface SSEEvent {
  execution_id: number
  agent_name: string
  status: ExecutionStatus
  error_message: string | null
  updated_at: string
  completed_at: string | null
}

// ── Agents ─────────────────────────────────────────────────────────────────

export interface Agent {
  name: string
  language: string
  description: string
}

// ── Settings (future backend) ───────────────────────────────────────────────

export interface ApiKeySettings {
  anthropic_key: string
  openai_key: string
}

export interface ModelSettings {
  planner_model: string
  coder_model: string
  reviewer_model: string
  streaming: boolean
  max_retries: number
}

export interface AgentSettings {
  name: string
  enabled: boolean
  max_review_retries: number
  max_static_retries: number
}

// ── Health ─────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: 'ok' | 'error'
}
