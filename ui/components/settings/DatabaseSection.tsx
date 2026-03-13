'use client'

import { useEffect, useState } from 'react'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { SettingsSection, SettingsField } from './SettingsPrimitives'

type ConnStatus = 'checking' | 'connected' | 'error'

export function DatabaseSection() {
  const [status, setStatus] = useState<ConnStatus>('checking')

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/health`)
      .then(r => r.ok ? setStatus('connected') : setStatus('error'))
      .catch(() => setStatus('error'))
  }, [])

  return (
    <div className="space-y-5">
      <SettingsSection
        title="PostgreSQL Connection"
        description="Connection is configured via DATABASE_URL in your server .env file."
      >
        {/* Connection status */}
        <div className="flex items-center gap-3 p-3 rounded-md bg-muted border border-border">
          {status === 'checking'  && <Loader2     className="w-4 h-4 text-muted-fg animate-spin" />}
          {status === 'connected' && <CheckCircle2 className="w-4 h-4 text-success" />}
          {status === 'error'     && <XCircle      className="w-4 h-4 text-danger" />}
          <div>
            <p className="text-xs font-mono text-foreground">
              {status === 'checking'  && 'Checking API connection…'}
              {status === 'connected' && 'API reachable — database connected'}
              {status === 'error'     && 'Cannot reach API — check backend is running'}
            </p>
            <p className="text-[11px] font-mono text-muted-fg mt-0.5">
              via GET /health
            </p>
          </div>
        </div>

        <SettingsField
          label="Connection string"
          description="Set in web/.env — never exposed to the frontend."
        >
          <input
            type="password"
            value="postgresql+asyncpg://***:***@localhost:5432/agentic_sdlc"
            className="input font-mono"
            readOnly
          />
        </SettingsField>
      </SettingsSection>

      <SettingsSection
        title="Migrations"
        description="Managed by Alembic. Run from the web/ directory."
        badge="coming-soon"
      >
        <div className="space-y-2">
          {[
            { cmd: 'python -m alembic upgrade head',   desc: 'Apply all pending migrations' },
            { cmd: 'python -m alembic downgrade -1',   desc: 'Rollback last migration' },
            { cmd: 'python -m alembic revision --autogenerate -m "desc"', desc: 'Generate new migration' },
          ].map(item => (
            <div key={item.cmd} className="flex items-center gap-3 p-2.5 rounded bg-muted border border-border/60">
              <code className="text-[11px] font-mono text-accent flex-1 truncate">
                {item.cmd}
              </code>
              <span className="text-[11px] font-mono text-muted-fg flex-shrink-0">{item.desc}</span>
            </div>
          ))}
        </div>
        <p className="text-[11px] font-mono text-muted-fg">
          A UI to run migrations directly will be added in a future sprint.
        </p>
      </SettingsSection>
    </div>
  )
}
