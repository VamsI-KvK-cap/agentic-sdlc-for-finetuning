'use client'

import { Lightbulb } from 'lucide-react'

interface Props {
  value: string
  onChange: (v: string) => void
}

const EXAMPLES = [
  'Use FastAPI with async endpoints',
  'Add type hints and docstrings',
  'Follow PEP8 strictly',
  'Include unit tests',
]

export function InstructionsBox({ value, onChange }: Props) {
  return (
    <div className="space-y-2">
      <textarea
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder="Any specific requirements, patterns, or constraints for the agent to follow…"
        rows={3}
        className="input resize-none leading-relaxed"
      />
      {/* Quick-insert chips */}
      <div className="flex items-center gap-2 flex-wrap">
        <Lightbulb className="w-3 h-3 text-muted-fg flex-shrink-0" />
        {EXAMPLES.map(ex => (
          <button
            key={ex}
            type="button"
            onClick={() => onChange(value ? `${value}\n${ex}` : ex)}
            className="text-[11px] font-mono text-muted-fg border border-border rounded px-2 py-0.5 hover:border-accent/50 hover:text-accent transition-all duration-150"
          >
            + {ex}
          </button>
        ))}
      </div>
    </div>
  )
}
