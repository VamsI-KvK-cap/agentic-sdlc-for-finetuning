'use client'

import { useEffect, useState, useRef } from 'react'
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

  const [agents, setAgents]               = useState<Agent[]>([])
  const [agentsLoading, setAgentsLoading] = useState(true)
  const [selectedAgent, setSelectedAgent] = useState<string>('')

  const [inputMode, setInputMode]         = useState<InputMode>('text')
  const [textInput, setTextInput]         = useState('')
  const [fileInput, setFileInput]         = useState<File | null>(null)
  const [gitUrl, setGitUrl]               = useState('')
  const [instructions, setInstructions]   = useState('')

  const [generating, setGenerating]       = useState(false)
  const [error, setError]                 = useState<string | null>(null)

  useEffect(() => {
    api.agents
      .list()
      .then(data => {
        setAgents(data)
        if (data.length > 0) setSelectedAgent(data[0].name)
      })
      .catch(() => {
        // Fallback: agents hardcoded if endpoint not yet wired
        const fallback = [{ name: 'python', language: 'Python', description: 'Python coding agent' }]
        setAgents(fallback)
        setSelectedAgent('python')
      })
      .finally(() => setAgentsLoading(false))
  }, [])

  const getTask = (): string => {
    if (inputMode === 'text') return textInput.trim()
    if (inputMode === 'git')  return `Git repository: ${gitUrl.trim()}`
    if (inputMode === 'file' && fileInput) return `File: ${fileInput.name}`
    return ''
  }

  const isValid = (): boolean => {
    if (!selectedAgent) return false
    if (inputMode === 'text') return textInput.trim().length > 0
    if (inputMode === 'git')  return gitUrl.trim().length > 0
    if (inputMode === 'file') return fileInput !== null
    return false
  }

  const handleGenerate = async () => {
    if (!isValid()) return
    setError(null)
    setGenerating(true)
    try {
      const task = instructions.trim()
        ? `${getTask()}\n\nSpecial instructions: ${instructions.trim()}`
        : getTask()

      const execution = await api.executions.create({
        agent_name: selectedAgent,
        task,
      })
      router.push(`/executions/${execution.id}`)
    } catch (err: any) {
      setError(err.message ?? 'Failed to trigger execution')
      setGenerating(false)
    }
  }

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
            Select an agent, describe your task, and generate code automatically.
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

        {/* Step 2 — Input */}
        <div className="space-y-2">
          <StepLabel number={2} label="Describe Your Task" />
          <InputTabs
            mode={inputMode}
            onModeChange={setInputMode}
            text={textInput}
            onTextChange={setTextInput}
            file={fileInput}
            onFileChange={setFileInput}
            gitUrl={gitUrl}
            onGitUrlChange={setGitUrl}
          />
        </div>

        <Divider />

        {/* Step 3 — Instructions */}
        <div className="space-y-2">
          <StepLabel number={3} label="Special Instructions" optional />
          <InstructionsBox
            value={instructions}
            onChange={setInstructions}
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
              ? `Ready · ${selectedAgent} agent`
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
          After clicking Generate you'll be redirected to the execution detail page
          where you can watch the agent run in real-time via a live status stream.
        </p>
      </div>
    </div>
  )
}

function StepLabel({ number, label, optional }: { number: number; label: string; optional?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-5 h-5 rounded-full bg-accent-dim border border-accent/40 text-accent text-[10px] font-mono font-bold flex items-center justify-center flex-shrink-0">
        {number}
      </span>
      <span className="text-xs font-mono text-muted-fg uppercase tracking-widest">{label}</span>
      {optional && (
        <span className="text-[10px] font-mono text-muted-fg/60 border border-border rounded px-1">
          optional
        </span>
      )}
    </div>
  )
}

function Divider() {
  return <div className="border-t border-border/60" />
}
