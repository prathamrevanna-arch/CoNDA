"use client"

import type { Signal } from "@/lib/conda-data"

function barColor(v: number) {
  if (v >= 70) return "var(--risk)"
  if (v >= 40) return "var(--warn)"
  return "var(--verified)"
}

export function SignalBreakdown({ signals }: { signals: Signal[] }) {
  return (
    <div className="flex flex-col gap-3">
      {signals.map((s) => {
        const color = barColor(s.contribution)
        return (
          <div key={s.id} className="rounded-lg border border-navy-border bg-white/[0.02] p-3">
            <div className="mb-1.5 flex items-center justify-between gap-2">
              <span className="text-sm font-semibold text-ink">{s.name}</span>
              <span className="font-mono text-sm font-bold" style={{ color }}>
                {s.contribution}
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-white/[0.06]">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${s.contribution}%`, backgroundColor: color }}
              />
            </div>
            <p className="mt-1.5 text-xs leading-snug text-ink-muted">{s.explanation}</p>
          </div>
        )
      })}
    </div>
  )
}
