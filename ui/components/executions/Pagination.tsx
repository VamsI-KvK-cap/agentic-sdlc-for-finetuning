'use client'

import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  page: number
  totalPages: number
  onPageChange: (p: number) => void
}

export function Pagination({ page, totalPages, onPageChange }: Props) {
  const pages = buildPageRange(page, totalPages)

  return (
    <div className="flex items-center justify-center gap-1 font-mono text-xs">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page === 1}
        className="btn-ghost px-2 py-1.5 disabled:opacity-30"
      >
        <ChevronLeft className="w-3.5 h-3.5" />
      </button>

      {pages.map((p, i) =>
        p === '...' ? (
          <span key={`ellipsis-${i}`} className="px-2 text-muted-fg">…</span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p as number)}
            className={cn(
              'w-7 h-7 rounded flex items-center justify-center transition-all duration-150',
              p === page
                ? 'bg-accent text-background font-semibold'
                : 'text-muted-fg hover:text-foreground hover:bg-muted'
            )}
          >
            {p}
          </button>
        )
      )}

      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page === totalPages}
        className="btn-ghost px-2 py-1.5 disabled:opacity-30"
      >
        <ChevronRight className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

function buildPageRange(current: number, total: number): (number | '...')[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  if (current <= 4) return [1, 2, 3, 4, 5, '...', total]
  if (current >= total - 3) return [1, '...', total - 4, total - 3, total - 2, total - 1, total]
  return [1, '...', current - 1, current, current + 1, '...', total]
}
