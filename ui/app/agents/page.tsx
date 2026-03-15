'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'
import type { Agent } from '@/lib/types'
import { AgentSelector } from '@/components/agents/AgentSelector'
import { InputTabs } from '@/components/agents/InputTabs'
import { InstructionsBox } from '@/components/agents/InstructionsBox'
import { GenerateButton } from '@/components/agents/GenerateButton'
import { Bot, Sparkles } from 'lucide-react'

export type InputMode = 'text' | 'file' | 'git'

export default function AgentsPage() {
  const router = useRouter()

  const [agents,        setAgents]        = useState<Agent[]>([])
  const [agentsLoading, setAgentsLoading] = useState(true)
  const [selectedAgent, setSelectedAgent] = useState<string>('')

  const [inputMode,     setInputMode]     = useState<InputMode>('text')
  const [textInput,     setTextInput]     = useState('')
  const [fileInput,     setFileInput]     = useState<File | null>(null)
  const [gitUrl,        setGitUrl]        = useState('')
  const [instructions,  setInstructions]  = useState('')

  const [generating,    setGenerating]    = useState(false)
  const [error,         setError]         = useState<string | null>(null)

  useEffect(() => {
    api.agents
      .list()
      .then(data => {
        setAgents(data)
        if (data.length > 0) setSelectedAgent(data[0].name)
      })
      .catch(() => {
        const fallback = [{ name: 'python', language: 'Python', description: 'Python coding agent' }]
        setAgents(fallback)
        setSelectedAgent('python')
      })
      .finally(() => setAgentsLoading(false))
  }, [])

  const isValid = (): boolean => {
    if (!selectedAgent) return false
    if (inputMode === 'text') return textInput.trim().length > 0
    if (inputMode === 'git')  return gitUrl.trim().startsWith('http')
    if (inputMode === 'file') return fileInput !== null && fileInput.name.endsWith('.zip')
    return false
  }

  const handleGenerate = async () => {
    if (!isValid()) return
    setError(null)
    setGenerating(true)

    try {
      // Build the task string — append special instructions if provided
      const baseTask = inputMode === 'text' ? textInput.trim() : instructions.trim() || 'Analyse and improve the existing codebase'
      const task = instructions.trim() && inputMode !== 'text'
        ? `${instructions.trim()}`
        : inputMode === 'text' && instructions.trim()
        ? `${textInput.trim()}\n\nSpecial instructions: ${instructions.trim()}`
        : baseTask

      let execution

      if (inputMode === 'text') {
        // ── Greenfield: plain task description ──────────────────────────
        execution = await api.executions.create({
          agent_name: selectedAgent,
          task: instructions.trim()
            ? `${textInput.trim()}\n\nAdditional instructions: ${instructions.trim()}`
            : textInput.trim(),
        })

      } else if (inputMode === 'file' && fileInput) {
        // ── Brownfield: zip upload ───────────────────────────────────────
        // The task here is what the agent should DO with the uploaded code.
        // Instructions box becomes the task description for brownfield mode.
        const brownfieldTask = instructions.trim() || 'Analyse the existing codebase and suggest improvements'
        execution = await api.executions.createFromZip(
          selectedAgent,
          brownfieldTask,
          fileInput,
        )

      } else if (inputMode === 'git') {
        // ── Brownfield: git clone ────────────────────────────────────────
        const brownfieldTask = instructions.trim() || 'Analyse the existing codebase and suggest improvements'
        execution = await api.executions.createFromGit({
          agent_name: selectedAgent,
          task: brownfieldTask,
          git_url: gitUrl.trim(),
        })
      }

      if (execution) {
        router.push(`/executions/${execution.id}`)
      }

    } catch (err: any) {
      setError(err.message ?? 'Failed to trigger execution')
      setGenerating(false)
    }
  }

  // Derive a helpful hint for the instructions box based on current mode
  const instructionsHint = inputMode === 'text'
    ? 'Additional constraints or preferences for code generation'
    : 'Describe what to change or add in the existing codebase (required for brownfield)'

  return (
    <div className="max-w-3xl mx-auto space-y-6">

      {/* Page hero */}
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-lg bg-accent-dim border border-accent/30 flex items-center justify-center flex-shrink-0 mt-0.5">
          <Bot className="w-5 h-5 text-accent" />
        </div>
        <div>
          <h2 className="text-xl font-bold font-sans text-foreground tracking-tight">
            Trigger an Agent
          </h2>
          <p className="text-sm font-mono text-muted-fg mt-0.5">
            Select an agent, provide your codebase or task, and generate code automatically.
          </p>
        </div>
      </div>

      {/* Main form card */}
      <div className="card space-y-6">

        {/* Step 1 — Agent */}
        <div className="space-y-2">
          <StepLabel number={1} label="Select Agent" />
          <AgentSelector
            agents={agents}
            loading={agentsLoading}
            value={selectedAgent}
            onChange={setSelectedAgent}
          />
        </div>

        <Divider />

        {/* Step 2 — Input source */}
        <div className="space-y-2">
          <StepLabel
            number={2}
            label={inputMode === 'text' ? 'Describe Your Task' : 'Provide Existing Codebase'}
          />
          {/* Mode hint */}
          {inputMode !== 'text' && (
            <p className="text-[11px] font-mono text-accent bg-accent-dim/40 border border-accent/20 rounded px-2.5 py-1.5">
              Brownfield mode — the agent will read your existing code before planning changes.
            </p>
          )}
          <InputTabs
            mode={inputMode}
            onModeChange={(m) => { setInputMode(m); setError(null) }}
            text={textInput}
            onTextChange={setTextInput}
            file={fileInput}
            onFileChange={setFileInput}
            gitUrl={gitUrl}
            onGitUrlChange={setGitUrl}
          />
        </div>

        <Divider />

        {/* Step 3 — Instructions (required for brownfield, optional for text) */}
        <div className="space-y-2">
          <StepLabel
            number={3}
            label={inputMode === 'text' ? 'Special Instructions' : 'Task Description'}
            optional={inputMode === 'text'}
            required={inputMode !== 'text'}
          />
          <InstructionsBox
            value={instructions}
            onChange={setInstructions}
            placeholder={instructionsHint}
          />
        </div>

        <Divider />

        {/* Error */}
        {error && (
          <div className="text-danger text-xs font-mono bg-red-950/30 border border-danger/30 rounded-md px-3 py-2">
            ⚠ {error}
          </div>
        )}

        {/* Generate */}
        <div className="flex items-center justify-between">
          <p className="text-xs font-mono text-muted-fg">
            {isValid()
              ? `Ready · ${selectedAgent} agent · ${inputMode} mode`
              : inputMode === 'file'
              ? 'Upload a .zip file to continue'
              : inputMode === 'git'
              ? 'Enter a public HTTPS Git URL to continue'
              : 'Complete the form above to continue'}
          </p>
          <GenerateButton
            onClick={handleGenerate}
            loading={generating}
            disabled={!isValid() || generating}
          />
        </div>
      </div>

      {/* Info note */}
      <div className="flex items-start gap-2.5 px-4 py-3 rounded-md bg-accent-dim/40 border border-accent/20">
        <Sparkles className="w-3.5 h-3.5 text-accent flex-shrink-0 mt-0.5" />
        <p className="text-xs font-mono text-muted-fg leading-relaxed">
          {inputMode === 'text'
            ? 'After clicking Generate you\'ll be redirected to the execution detail page where you can watch the agent run in real-time.'
            : 'The agent will read the existing file structure before planning. Use the Task Description above to specify what needs to change.'}
        </p>
      </div>
    </div>
  )
}

function StepLabel({
  number, label, optional, required,
}: {
  number: number
  label: string
  optional?: boolean
  required?: boolean
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-5 h-5 rounded-full bg-accent-dim border border-accent/40 text-accent text-[10px] font-mono font-bold flex items-center justify-center flex-shrink-0">
        {number}
      </span>
      <span className="text-xs font-mono text-muted-fg uppercase tracking-widest">{label}</span>
      {optional && (
        <span className="text-[10px] font-mono text-muted-fg/60 border border-border rounded px-1">optional</span>
      )}
      {required && (
        <span className="text-[10px] font-mono text-accent/80 border border-accent/30 rounded px-1">required</span>
      )}
    </div>
  )
}

function Divider() {
  return <div className="border-t border-border/60" />
}
