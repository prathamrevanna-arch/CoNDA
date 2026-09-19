'use client'

import { useMemo, useState } from 'react'
import { cn } from '@/lib/utils'
import { RiskBadge } from '@/components/risk-badge'
import { GlassPanel } from '@/components/glass-panel'
import { detectionFeed, type DetectionResult, type RiskLevel } from '@/lib/data'
import { ArrowUpDown } from 'lucide-react'

type Filter = 'ALL' | RiskLevel
type SortKey = 'score' | 'window'

const filters: Filter[] = ['ALL', 'HIGH', 'MEDIUM', 'LOW']

export function DetectionTable() {
  const [filter, setFilter] = useState<Filter>('ALL')
  const [sort, setSort] = useState<{ key: SortKey; dir: 'asc' | 'desc' }>({
    key: 'score',
    dir: 'desc',
  })
  const [selected, setSelected] = useState<string>(detectionFeed[0].id)

  const rows = useMemo(() => {
    const filtered = detectionFeed.filter((d) => filter === 'ALL' || d.level === filter)
    const sorted = [...filtered].sort((a, b) => {
      const va = sort.key === 'score' ? a.score : a.window.start
      const vb = sort.key === 'score' ? b.score : b.window.start
      return sort.dir === 'desc' ? vb - va : va - vb
    })
    return sorted
  }, [filter, sort])

  const active = detectionFeed.find((d) => d.id === selected) ?? detectionFeed[0]

  const toggleSort = (key: SortKey) =>
    setSort((s) =>
      s.key === key ? { key, dir: s.dir === 'desc' ? 'asc' : 'desc' } : { key, dir: 'desc' },
    )

  return (
    <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
      <GlassPanel className="overflow-hidden">
        {/* filter bar */}
        <div className="flex flex-wrap items-center gap-2 border-b border-border p-4">
          <span className="mr-1 font-mono text-[0.65rem] tracking-[0.18em] text-muted-foreground uppercase">
            Risk
          </span>
          {filters.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              className={cn(
                'rounded-full border px-3 py-1 font-mono text-xs transition-colors',
                filter === f
                  ? 'border-cyan/50 bg-cyan/10 text-cyan'
                  : 'border-border text-muted-foreground hover:text-foreground',
              )}
            >
              {f}
            </button>
          ))}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] border-collapse text-left">
            <thead>
              <tr className="border-b border-border font-mono text-[0.65rem] tracking-[0.14em] text-muted-foreground uppercase">
                <th className="px-4 py-3 font-medium">ID</th>
                <th className="px-4 py-3 font-medium">Pair</th>
                <th className="px-4 py-3 font-medium">
                  <button
                    type="button"
                    onClick={() => toggleSort('window')}
                    className="inline-flex items-center gap-1 hover:text-foreground"
                  >
                    Window <ArrowUpDown className="h-3 w-3" />
                  </button>
                </th>
                <th className="px-4 py-3 font-medium">
                  <button
                    type="button"
                    onClick={() => toggleSort('score')}
                    className="inline-flex items-center gap-1 hover:text-foreground"
                  >
                    Score <ArrowUpDown className="h-3 w-3" />
                  </button>
                </th>
                <th className="px-4 py-3 font-medium">Level</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => (
                <tr
                  key={d.id}
                  onClick={() => setSelected(d.id)}
                  className={cn(
                    'cursor-pointer border-b border-border/60 transition-colors last:border-0',
                    selected === d.id ? 'bg-cyan/[0.06]' : 'hover:bg-panel-raised/60',
                  )}
                >
                  <td className="px-4 py-3.5 font-mono text-xs text-muted-foreground">{d.id}</td>
                  <td className="px-4 py-3.5 font-mono text-sm text-foreground">
                    {d.pair.source} ↔ {d.pair.target}
                  </td>
                  <td className="px-4 py-3.5 font-mono text-sm tabular-nums text-muted-foreground">
                    {d.window.start}–{d.window.end}
                  </td>
                  <td className="px-4 py-3.5">
                    <ScoreBar score={d.score} level={d.level} />
                  </td>
                  <td className="px-4 py-3.5">
                    <RiskBadge level={d.level} size="sm" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassPanel>

      <DetailCard detection={active} />
    </div>
  )
}

function ScoreBar({ score, level }: { score: number; level: RiskLevel }) {
  const color =
    level === 'HIGH' ? 'var(--risk-high)' : level === 'MEDIUM' ? 'var(--risk-med)' : 'var(--risk-low)'
  return (
    <div className="flex items-center gap-2.5">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-border-strong">
        <div className="h-full rounded-full" style={{ width: `${score}%`, backgroundColor: color }} />
      </div>
      <span className="font-mono text-sm tabular-nums text-foreground">{score}</span>
    </div>
  )
}

function DetailCard({ detection }: { detection: DetectionResult }) {
  return (
    <GlassPanel blueprint className="p-6 sm:p-7">
      <div className="flex items-center justify-between">
        <span className="font-mono text-xs text-muted-foreground">{detection.id}</span>
        <RiskBadge level={detection.level} size="sm" />
      </div>
      <div className="mt-4 font-display text-3xl font-semibold text-foreground">
        {detection.pair.source} <span className="text-cyan">↔</span> {detection.pair.target}
      </div>
      <div className="mt-1 font-mono text-xs text-muted-foreground">
        window {detection.window.start}–{detection.window.end}
      </div>

      <div className="mt-6 flex items-baseline gap-2">
        <span
          className="font-display text-5xl font-semibold tabular-nums"
          style={{
            color:
              detection.level === 'HIGH'
                ? 'var(--risk-high)'
                : detection.level === 'MEDIUM'
                  ? 'var(--risk-med)'
                  : 'var(--risk-low)',
          }}
        >
          {detection.score}
        </span>
        <span className="font-mono text-sm text-muted-foreground">/ 100 risk</span>
      </div>

      <div className="mt-6 border-t border-border pt-5">
        <div className="font-mono text-[0.62rem] tracking-[0.16em] text-muted-foreground uppercase">
          Counterfactual gap
        </div>
        <div className="mt-2 flex items-center justify-between font-mono text-sm">
          <span className="text-muted-foreground">
            ${detection.counterfactual.referencePrice.toFixed(2)} ref
          </span>
          <span className="text-cyan">${detection.counterfactual.observedPrice.toFixed(2)} obs</span>
          <span className="text-risk-high">+{detection.counterfactual.gapPct.toFixed(1)}%</span>
        </div>
      </div>

      <div className="mt-5 border-t border-border pt-5">
        <div className="font-mono text-[0.62rem] tracking-[0.16em] text-muted-foreground uppercase">
          Contributing signals
        </div>
        <ul className="mt-3 flex flex-col gap-2">
          {detection.signals.map((s) => (
            <li key={s.id} className="flex items-center justify-between gap-3">
              <span className="text-sm text-foreground">{s.label}</span>
              <span className="font-mono text-xs tabular-nums text-muted-foreground">
                +{s.contribution}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </GlassPanel>
  )
}
