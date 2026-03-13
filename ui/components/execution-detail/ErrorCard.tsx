'use client'

import { AlertTriangle } from 'lucide-react'

export function ErrorCard({ message }: { message: string }) {
  return (
    <div className="card border-danger/40 bg-red-950/20 space-y-2">
      <div className="flex items-center gap-2 text-danger">
        <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
        <p className="text-[10px] font-mono uppercase tracking-widest">Error</p>
      </div>
      <p className="text-xs font-mono text-red-300 leading-relaxed whitespace-pre-wrap">
        {message}
      </p>
    </div>
  )
}
