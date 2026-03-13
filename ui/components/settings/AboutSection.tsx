'use client'

import { ExternalLink, Github, Zap } from 'lucide-react'
import { SettingsSection } from './SettingsPrimitives'

const STACK = [
  { layer: 'Agent Framework', tech: 'LangGraph',       url: 'https://langchain-ai.github.io/langgraph/' },
  { layer: 'LLM Provider',    tech: 'Anthropic Claude', url: 'https://docs.anthropic.com' },
  { layer: 'API',             tech: 'FastAPI',          url: 'https://fastapi.tiangolo.com' },
  { layer: 'Database',        tech: 'PostgreSQL + SQLAlchemy', url: 'https://www.sqlalchemy.org' },
  { layer: 'Migrations',      tech: 'Alembic',          url: 'https://alembic.sqlalchemy.org' },
  { layer: 'Frontend',        tech: 'Next.js 14',       url: 'https://nextjs.org' },
  { layer: 'Styling',         tech: 'Tailwind CSS',     url: 'https://tailwindcss.com' },
  { layer: 'Package manager', tech: 'uv',               url: 'https://docs.astral.sh/uv/' },
]

const ROADMAP = [
  { status: '✅', item: 'LangGraph coding agent (Python)' },
  { status: '✅', item: 'FastAPI execution tracking' },
  { status: '✅', item: 'SSE live execution stream' },
  { status: '✅', item: 'Next.js dashboard UI' },
  { status: '🔜', item: 'JavaScript / Go agents' },
  { status: '🔜', item: 'Chat interface + RAG' },
  { status: '🔜', item: 'LangGraph long-term memory' },
  { status: '🔜', item: 'Settings persistence to DB' },
  { status: '🔜', item: 'Docker Compose full-stack setup' },
]

export function AboutSection() {
  return (
    <div className="space-y-5">

      {/* Project card */}
      <div className="card space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-accent flex items-center justify-center">
            <Zap className="w-5 h-5 text-background" strokeWidth={2.5} />
          </div>
          <div>
            <h3 className="text-sm font-bold font-sans text-foreground">Agentic SDLC</h3>
            <p className="text-[11px] font-mono text-muted-fg">v0.1.0 · development</p>
          </div>
        </div>
        <p className="text-xs font-mono text-muted-fg leading-relaxed">
          An AI-powered software development lifecycle system. LangGraph agents autonomously
          plan, write, review, and lint code from natural language task descriptions.
          Triggered via REST API and tracked in PostgreSQL.
        </p>
        <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-xs font-mono text-muted-fg hover:text-accent transition-colors w-fit"
        >
          <Github className="w-3.5 h-3.5" />
          View on GitHub
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      {/* Tech stack */}
      <SettingsSection title="Tech Stack" description="Libraries and frameworks powering this system.">
        <div className="space-y-0 divide-y divide-border/50">
          {STACK.map(item => (
            <div key={item.layer} className="flex items-center justify-between py-2.5">
              <p className="text-xs font-mono text-muted-fg w-36">{item.layer}</p>
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-xs font-mono text-foreground hover:text-accent transition-colors"
              >
                {item.tech}
                <ExternalLink className="w-2.5 h-2.5 opacity-50" />
              </a>
            </div>
          ))}
        </div>
      </SettingsSection>

      {/* Roadmap */}
      <SettingsSection title="Roadmap" description="What's built and what's coming.">
        <div className="space-y-2">
          {ROADMAP.map(item => (
            <div key={item.item} className="flex items-center gap-3 text-xs font-mono">
              <span className="text-base leading-none">{item.status}</span>
              <span className={item.status === '✅' ? 'text-foreground' : 'text-muted-fg'}>
                {item.item}
              </span>
            </div>
          ))}
        </div>
      </SettingsSection>

    </div>
  )
}
