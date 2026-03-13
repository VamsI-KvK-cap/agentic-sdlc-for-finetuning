'use client'

import { FileText } from 'lucide-react'

export function TaskCard({ task }: { task: string }) {
  return (
    <div className="card space-y-3">
      <div className="flex items-center gap-2">
        <FileText className="w-3.5 h-3.5 text-muted-fg" />
        <p className="text-[10px] font-mono text-muted-fg uppercase tracking-widest">
          Task
        </p>
      </div>
      <p className="text-sm font-mono text-foreground leading-relaxed whitespace-pre-wrap">
        {task}
      </p>
    </div>
  )
}
