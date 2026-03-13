'use client'

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import type { Stats } from '@/app/dashboard/page'

const COLORS = {
  completed: 'hsl(142, 70%, 45%)',
  failed:    'hsl(0, 72%, 55%)',
  running:   'hsl(180, 85%, 50%)',
  pending:   'hsl(220, 10%, 40%)',
}

interface TooltipProps {
  active?: boolean
  payload?: Array<{ name: string; value: number; payload: { fill: string } }>
}

function CustomTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload?.length) return null
  const item = payload[0]
  return (
    <div className="bg-surface border border-border rounded-md px-3 py-2 text-xs font-mono shadow-lg">
      <p className="text-muted-fg capitalize">{item.name}</p>
      <p className="text-foreground font-semibold text-base">{item.value}</p>
    </div>
  )
}

export function ExecutionPieChart({ stats, loading }: { stats: Stats; loading: boolean }) {
  const data = [
    { name: 'completed', value: stats.completed },
    { name: 'failed',    value: stats.failed },
    { name: 'running',   value: stats.running },
    { name: 'pending',   value: stats.pending },
  ].filter(d => d.value > 0)

  const isEmpty = data.length === 0

  return (
    <div className="card h-full flex flex-col gap-4">
      <div>
        <p className="text-xs font-mono text-muted-fg uppercase tracking-widest">Distribution</p>
        <p className="text-sm font-semibold font-sans text-foreground mt-0.5">Execution Breakdown</p>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="w-32 h-32 rounded-full bg-muted animate-pulse" />
        </div>
      ) : isEmpty ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2">
          <div className="w-24 h-24 rounded-full border-2 border-dashed border-border flex items-center justify-center">
            <p className="text-muted-fg text-xs font-mono text-center">no data</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col gap-4">
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={48}
                  outerRadius={72}
                  paddingAngle={3}
                  dataKey="value"
                  strokeWidth={0}
                >
                  {data.map(entry => (
                    <Cell
                      key={entry.name}
                      fill={COLORS[entry.name as keyof typeof COLORS]}
                    />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Legend */}
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            {data.map(entry => (
              <div key={entry.name} className="flex items-center gap-2">
                <span
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{ background: COLORS[entry.name as keyof typeof COLORS] }}
                />
                <span className="text-xs font-mono text-muted-fg capitalize">{entry.name}</span>
                <span className="text-xs font-mono text-foreground ml-auto">{entry.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
