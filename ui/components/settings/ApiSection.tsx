'use client'

import { useState } from 'react'
import {
  SettingsSection, SettingsField,
  SecretInput, SaveButton,
} from './SettingsPrimitives'

export function ApiSection() {
  const [anthropicKey, setAnthropicKey] = useState('')
  const [openaiKey,    setOpenaiKey]    = useState('')
  const [saved,        setSaved]        = useState(false)
  const [saving,       setSaving]       = useState(false)

  const handleSave = async () => {
    setSaving(true)
    // TODO: POST /api/v1/settings/api-keys
    await new Promise(r => setTimeout(r, 600))
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="space-y-5">
      <SettingsSection
        title="LLM API Keys"
        description="Keys are stored in your .env file and never sent to the browser in production."
        badge={anthropicKey || openaiKey ? 'configured' : 'required'}
      >
        <SettingsField
          label="Anthropic API Key"
          description="Used by all agents by default. Get yours at console.anthropic.com"
        >
          <SecretInput
            value={anthropicKey}
            onChange={setAnthropicKey}
            placeholder="sk-ant-…"
            saved={saved}
          />
        </SettingsField>

        <SettingsField
          label="OpenAI API Key"
          description="Optional — used if you configure an agent to use GPT models."
        >
          <SecretInput
            value={openaiKey}
            onChange={setOpenaiKey}
            placeholder="sk-…"
            saved={saved}
          />
        </SettingsField>

        <SaveButton onClick={handleSave} saving={saving} saved={saved} />
      </SettingsSection>

      <SettingsSection
        title="API Server"
        description="The FastAPI backend URL the UI connects to."
      >
        <SettingsField label="Backend URL">
          <input
            type="text"
            defaultValue="http://localhost:8000"
            className="input font-mono"
            readOnly
          />
        </SettingsField>
        <p className="text-[11px] font-mono text-muted-fg">
          Change via <code className="text-accent">NEXT_PUBLIC_API_URL</code> in <code className="text-accent">.env.local</code>
        </p>
      </SettingsSection>
    </div>
  )
}
