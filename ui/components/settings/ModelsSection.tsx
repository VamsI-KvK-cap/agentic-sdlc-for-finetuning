'use client'

import { useState } from 'react'
import {
  SettingsSection, SettingsField,
  SettingsSelect, Toggle, SaveButton,
} from './SettingsPrimitives'

const ANTHROPIC_MODELS = [
  { value: 'claude-opus-4-5',         label: 'Claude Opus 4.5 — most capable' },
  { value: 'claude-sonnet-4-5',       label: 'Claude Sonnet 4.5 — balanced' },
  { value: 'claude-haiku-4-5',        label: 'Claude Haiku 4.5 — fastest' },
]

const OPENAI_MODELS = [
  { value: 'gpt-4o',       label: 'GPT-4o' },
  { value: 'gpt-4o-mini',  label: 'GPT-4o Mini' },
  { value: 'o3-mini',      label: 'o3 Mini' },
]

export function ModelsSection() {
  const [plannerModel,  setPlannerModel]  = useState('claude-sonnet-4-5')
  const [coderModel,    setCoderModel]    = useState('claude-sonnet-4-5')
  const [reviewerModel, setReviewerModel] = useState('claude-haiku-4-5')
  const [streaming,     setStreaming]     = useState(true)
  const [saved,         setSaved]         = useState(false)
  const [saving,        setSaving]        = useState(false)

  const handleSave = async () => {
    setSaving(true)
    // TODO: POST /api/v1/settings/models
    await new Promise(r => setTimeout(r, 600))
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="space-y-5">
      <SettingsSection
        title="Agent Models"
        description="Assign models to each role in the coding agent workflow. Using cheaper models for reviewer/checker reduces cost."
        badge="coming-soon"
      >
        <SettingsField
          label="Planner"
          description="Plans the file structure and task breakdown."
        >
          <SettingsSelect
            value={plannerModel}
            onChange={setPlannerModel}
            options={[...ANTHROPIC_MODELS, ...OPENAI_MODELS]}
            disabled
          />
        </SettingsField>

        <SettingsField
          label="Coder"
          description="Writes the actual code for each file."
        >
          <SettingsSelect
            value={coderModel}
            onChange={setCoderModel}
            options={[...ANTHROPIC_MODELS, ...OPENAI_MODELS]}
            disabled
          />
        </SettingsField>

        <SettingsField
          label="Reviewer"
          description="Reviews code quality and approves or requests revisions."
        >
          <SettingsSelect
            value={reviewerModel}
            onChange={setReviewerModel}
            options={[...ANTHROPIC_MODELS, ...OPENAI_MODELS]}
            disabled
          />
        </SettingsField>

        <SaveButton onClick={handleSave} saving={saving} saved={saved} />
      </SettingsSection>

      <SettingsSection
        title="Inference Settings"
        description="Global settings applied to all LLM calls."
        badge="coming-soon"
      >
        <SettingsField
          label="Streaming"
          description="Stream tokens as they're generated. Disable for batch runs."
        >
          <Toggle enabled={streaming} onChange={setStreaming} disabled />
        </SettingsField>

        <SettingsField
          label="Max retries"
          description="Number of times to retry a failed LLM call."
        >
          <input
            type="number"
            defaultValue={3}
            min={1}
            max={10}
            className="input w-20"
            disabled
          />
        </SettingsField>
      </SettingsSection>
    </div>
  )
}
