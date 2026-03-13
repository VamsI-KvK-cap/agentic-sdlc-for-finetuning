'use client'

import { useState } from 'react'
import { Bot } from 'lucide-react'
import {
  SettingsSection, SettingsField,
  Toggle, SaveButton,
} from './SettingsPrimitives'

interface AgentConfig {
  name: string
  language: string
  enabled: boolean
  maxReviewRetries: number
  maxStaticRetries: number
}

const DEFAULT_AGENTS: AgentConfig[] = [
  { name: 'python',     language: 'Python',     enabled: true,  maxReviewRetries: 2, maxStaticRetries: 2 },
  { name: 'javascript', language: 'JavaScript', enabled: false, maxReviewRetries: 2, maxStaticRetries: 2 },
  { name: 'go',         language: 'Go',         enabled: false, maxReviewRetries: 2, maxStaticRetries: 2 },
]

export function AgentsSection() {
  const [agents, setAgents] = useState<AgentConfig[]>(DEFAULT_AGENTS)
  const [saved,  setSaved]  = useState(false)
  const [saving, setSaving] = useState(false)

  const update = (name: string, patch: Partial<AgentConfig>) => {
    setAgents(prev => prev.map(a => a.name === name ? { ...a, ...patch } : a))
  }

  const handleSave = async () => {
    setSaving(true)
    await new Promise(r => setTimeout(r, 600))
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="space-y-5">
      <SettingsSection
        title="Registered Agents"
        description="Enable or disable agents and configure their retry behaviour."
        badge="coming-soon"
      >
        <div className="space-y-4">
          {agents.map(agent => (
            <div key={agent.name} className="p-4 rounded-md border border-border bg-muted/30 space-y-3">

              {/* Agent header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-6 h-6 rounded bg-accent-dim border border-accent/30 flex items-center justify-center">
                    <Bot className="w-3 h-3 text-accent" />
                  </div>
                  <div>
                    <p className="text-xs font-mono font-semibold text-foreground">{agent.language}</p>
                    <p className="text-[10px] font-mono text-muted-fg">{agent.name} agent</p>
                  </div>
                </div>
                <Toggle
                  enabled={agent.enabled}
                  onChange={v => update(agent.name, { enabled: v })}
                  disabled
                />
              </div>

              {/* Config rows */}
              <div className="grid grid-cols-2 gap-3 pt-1 border-t border-border/60">
                <div>
                  <p className="text-[10px] font-mono text-muted-fg mb-1">Review retries</p>
                  <input
                    type="number"
                    value={agent.maxReviewRetries}
                    onChange={e => update(agent.name, { maxReviewRetries: Number(e.target.value) })}
                    min={1} max={5}
                    className="input w-16 text-center py-1 text-xs"
                    disabled
                  />
                </div>
                <div>
                  <p className="text-[10px] font-mono text-muted-fg mb-1">Lint retries</p>
                  <input
                    type="number"
                    value={agent.maxStaticRetries}
                    onChange={e => update(agent.name, { maxStaticRetries: Number(e.target.value) })}
                    min={1} max={5}
                    className="input w-16 text-center py-1 text-xs"
                    disabled
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        <SaveButton onClick={handleSave} saving={saving} saved={saved} />
      </SettingsSection>

      <SettingsSection
        title="Output Directory"
        description="Where generated files are written on the server."
        badge="coming-soon"
      >
        <SettingsField label="Output path">
          <input
            type="text"
            defaultValue="./output"
            className="input font-mono"
            disabled
          />
        </SettingsField>
      </SettingsSection>
    </div>
  )
}
