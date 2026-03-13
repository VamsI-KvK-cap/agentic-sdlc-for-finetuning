'use client'

import { useState } from 'react'
import { SettingsNav } from '@/components/settings/SettingsNav'
import { ApiSection } from '@/components/settings/ApiSection'
import { ModelsSection } from '@/components/settings/ModelsSection'
import { AgentsSection } from '@/components/settings/AgentsSection'
import { DatabaseSection } from '@/components/settings/DatabaseSection'
import { AboutSection } from '@/components/settings/AboutSection'

export type SettingsTab = 'api' | 'models' | 'agents' | 'database' | 'about'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('api')

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold font-sans text-foreground tracking-tight">Settings</h2>
        <p className="text-sm font-mono text-muted-fg mt-0.5">
          Configure API keys, models, and agent behaviour
        </p>
      </div>

      <div className="flex gap-6">
        {/* Left nav */}
        <SettingsNav active={activeTab} onChange={setActiveTab} />

        {/* Content */}
        <div className="flex-1 min-w-0">
          {activeTab === 'api'      && <ApiSection />}
          {activeTab === 'models'   && <ModelsSection />}
          {activeTab === 'agents'   && <AgentsSection />}
          {activeTab === 'database' && <DatabaseSection />}
          {activeTab === 'about'    && <AboutSection />}
        </div>
      </div>
    </div>
  )
}
