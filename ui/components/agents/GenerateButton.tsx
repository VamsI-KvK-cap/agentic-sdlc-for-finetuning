'use client'

import { Loader2, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  onClick: () => void
  loading: boolean
  disabled: boolean
}

export function GenerateButton({ onClick, loading, disabled }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'btn-primary flex items-center gap-2 px-5 py-2.5',
        loading && 'opacity-80 cursor-not-allowed'
      )}
    >
      {loading ? (
        <>
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          Generating…
        </>
      ) : (
        <>
          <Sparkles className="w-3.5 h-3.5" />
          Generate
        </>
      )}
    </button>
  )
}
