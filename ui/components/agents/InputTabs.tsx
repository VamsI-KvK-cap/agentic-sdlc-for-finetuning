'use client'

import { useRef } from 'react'
import { FileText, Upload, GitBranch, X, File } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { InputMode } from '@/app/agents/page'

interface Props {
  mode: InputMode
  onModeChange: (m: InputMode) => void
  text: string
  onTextChange: (v: string) => void
  file: File | null
  onFileChange: (f: File | null) => void
  gitUrl: string
  onGitUrlChange: (v: string) => void
}

const TABS: { id: InputMode; label: string; icon: React.ReactNode; hint: string }[] = [
  { id: 'text', label: 'Text',     icon: <FileText   className="w-3.5 h-3.5" />, hint: 'Greenfield — describe a new task' },
  { id: 'file', label: 'Zip Upload', icon: <Upload   className="w-3.5 h-3.5" />, hint: 'Brownfield — upload existing codebase as .zip' },
  { id: 'git',  label: 'Git URL',  icon: <GitBranch  className="w-3.5 h-3.5" />, hint: 'Brownfield — clone a public Git repo' },
]

export function InputTabs({
  mode, onModeChange,
  text, onTextChange,
  file, onFileChange,
  gitUrl, onGitUrlChange,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null)

  return (
    <div className="space-y-3">
      {/* Tab bar */}
      <div className="flex gap-1 bg-muted p-1 rounded-md w-fit">
        {TABS.map(tab => (
          <button
            key={tab.id}
            type="button"
            title={tab.hint}
            onClick={() => onModeChange(tab.id)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono transition-all duration-150',
              mode === tab.id
                ? 'bg-surface text-foreground shadow-sm border border-border'
                : 'text-muted-fg hover:text-foreground'
            )}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Text input — greenfield task description */}
      {mode === 'text' && (
        <textarea
          value={text}
          onChange={e => onTextChange(e.target.value)}
          placeholder={`Describe your task as a user story or requirement...\n\nExample: As a store manager, I want to add products to inventory so that I can track stock levels.`}
          rows={6}
          className="input resize-none leading-relaxed"
        />
      )}

      {/* Zip upload — brownfield codebase */}
      {mode === 'file' && (
        <div>
          {/* Hidden input — accepts .zip only */}
          <input
            ref={fileRef}
            type="file"
            accept=".zip,application/zip,application/x-zip-compressed"
            className="hidden"
            onChange={e => onFileChange(e.target.files?.[0] ?? null)}
          />
          {file ? (
            <div className="input flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <File className="w-4 h-4 text-accent flex-shrink-0" />
                <div>
                  <p className="text-sm font-mono text-foreground">{file.name}</p>
                  <p className="text-[11px] font-mono text-muted-fg">
                    {(file.size / 1024).toFixed(1)} KB · zip archive
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  onFileChange(null)
                  if (fileRef.current) fileRef.current.value = ''
                }}
                className="text-muted-fg hover:text-danger transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className={cn(
                'w-full border-2 border-dashed border-border rounded-md py-8',
                'flex flex-col items-center gap-2 text-muted-fg',
                'hover:border-accent/50 hover:text-accent transition-all duration-200',
              )}
            >
              <Upload className="w-6 h-6" />
              <span className="text-xs font-mono">Click to upload your codebase</span>
              <span className="text-[11px] font-mono opacity-60">.zip archives only</span>
            </button>
          )}
        </div>
      )}

      {/* Git URL — brownfield clone */}
      {mode === 'git' && (
        <div className="space-y-2">
          <div className="relative">
            <GitBranch className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-fg" />
            <input
              type="url"
              value={gitUrl}
              onChange={e => onGitUrlChange(e.target.value)}
              placeholder="https://github.com/user/repo"
              className="input pl-9"
            />
          </div>
          <p className="text-[11px] font-mono text-muted-fg px-1">
            Public HTTPS URLs only — GitHub, GitLab, Bitbucket. The agent will do a shallow clone before planning.
          </p>
        </div>
      )}
    </div>
  )
}
