'use client'

import { useState } from 'react'
import { Eye, EyeOff, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'

// ── Section wrapper ────────────────────────────────────────────────────────

export function SettingsSection({
  title,
  description,
  children,
  badge,
}: {
  title: string
  description?: string
  children: React.ReactNode
  badge?: 'coming-soon' | 'configured' | 'required'
}) {
  const BADGE_STYLES = {
    'coming-soon': 'text-warning border-warning/40 bg-warning/10',
    'configured':  'text-success border-success/40 bg-success/10',
    'required':    'text-danger  border-danger/40  bg-danger/10',
  }

  return (
    <div className="card space-y-5">
      <div className="flex items-start justify-between gap-3 pb-4 border-b border-border">
        <div>
          <h3 className="text-sm font-bold font-sans text-foreground">{title}</h3>
          {description && (
            <p className="text-xs font-mono text-muted-fg mt-0.5 leading-relaxed">{description}</p>
          )}
        </div>
        {badge && (
          <span className={cn('badge border flex-shrink-0', BADGE_STYLES[badge])}>
            {badge === 'coming-soon' ? 'Coming soon' : badge === 'configured' ? 'Configured' : 'Required'}
          </span>
        )}
      </div>
      <div className="space-y-4">
        {children}
      </div>
    </div>
  )
}

// ── Field row ──────────────────────────────────────────────────────────────

export function SettingsField({
  label,
  description,
  children,
}: {
  label: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-start justify-between gap-6">
      <div className="min-w-0 flex-shrink-0 w-48">
        <p className="text-xs font-mono text-foreground">{label}</p>
        {description && (
          <p className="text-[11px] font-mono text-muted-fg mt-0.5 leading-relaxed">{description}</p>
        )}
      </div>
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  )
}

// ── Secret input (masked by default) ──────────────────────────────────────

export function SecretInput({
  value,
  onChange,
  placeholder,
  saved,
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  saved?: boolean
}) {
  const [visible, setVisible] = useState(false)

  return (
    <div className="relative">
      <input
        type={visible ? 'text' : 'password'}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="input pr-16 font-mono"
      />
      <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
        {saved && value && (
          <CheckCircle2 className="w-3.5 h-3.5 text-success flex-shrink-0" />
        )}
        <button
          type="button"
          onClick={() => setVisible(v => !v)}
          className="text-muted-fg hover:text-foreground transition-colors p-1"
        >
          {visible
            ? <EyeOff className="w-3.5 h-3.5" />
            : <Eye    className="w-3.5 h-3.5" />}
        </button>
      </div>
    </div>
  )
}

// ── Toggle switch ──────────────────────────────────────────────────────────

export function Toggle({
  enabled,
  onChange,
  disabled,
}: {
  enabled: boolean
  onChange: (v: boolean) => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      disabled={disabled}
      onClick={() => onChange(!enabled)}
      className={cn(
        'relative w-9 h-5 rounded-full border transition-all duration-200 flex-shrink-0',
        enabled
          ? 'bg-accent border-accent'
          : 'bg-muted border-border',
        disabled && 'opacity-40 cursor-not-allowed'
      )}
    >
      <span className={cn(
        'absolute top-0.5 w-3.5 h-3.5 rounded-full transition-all duration-200',
        enabled ? 'left-[18px] bg-background' : 'left-0.5 bg-muted-fg'
      )} />
    </button>
  )
}

// ── Select dropdown ────────────────────────────────────────────────────────

export function SettingsSelect({
  value,
  onChange,
  options,
  disabled,
}: {
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
  disabled?: boolean
}) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      disabled={disabled}
      className={cn(
        'input appearance-none cursor-pointer',
        disabled && 'opacity-50 cursor-not-allowed'
      )}
    >
      {options.map(opt => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  )
}

// ── Save button ────────────────────────────────────────────────────────────

export function SaveButton({
  onClick,
  saving,
  saved,
}: {
  onClick: () => void
  saving?: boolean
  saved?: boolean
}) {
  return (
    <div className="flex items-center justify-end gap-3 pt-2 border-t border-border mt-2">
      {saved && (
        <span className="text-xs font-mono text-success flex items-center gap-1.5">
          <CheckCircle2 className="w-3.5 h-3.5" /> Saved
        </span>
      )}
      <button
        type="button"
        onClick={onClick}
        disabled={saving}
        className="btn-primary text-xs px-4 py-1.5"
      >
        {saving ? 'Saving…' : 'Save changes'}
      </button>
    </div>
  )
}
