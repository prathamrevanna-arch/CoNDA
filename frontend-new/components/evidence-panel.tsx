import { cn } from '@/lib/utils'
import { GlassPanel } from '@/components/glass-panel'
import { RiskGauge } from '@/components/risk-gauge'
import { RiskBadge } from '@/components/risk-badge'
import { SignalCard } from '@/components/signal-card'
import type { DetectionResult } from '@/lib/data'

interface EvidencePanelProps {
  detection: DetectionResult
  className?: string
}

export function EvidencePanel({ detection, className }: EvidencePanelProps) {
  const { pair, window, score, level, signals } = detection
  return (
    <GlassPanel blueprint className={cn('p-6 sm:p-8', className)}>
      <div className="flex flex-col gap-8 lg:flex-row lg:items-center">
        <div className="flex flex-col items-center gap-4 lg:w-[240px] lg:shrink-0">
          <RiskGauge score={score} />
          <RiskBadge level={level} />
        </div>

        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <div>
              <div className="font-mono text-[0.62rem] tracking-[0.16em] text-muted-foreground uppercase">
                Agent Pair
              </div>
              <div className="mt-1 font-display text-2xl font-semibold text-foreground">
                {pair.source} <span className="text-cyan">↔</span> {pair.target}
              </div>
            </div>
            <div className="h-8 w-px bg-border" />
            <div>
              <div className="font-mono text-[0.62rem] tracking-[0.16em] text-muted-foreground uppercase">
                Window
              </div>
              <div className="mt-1 font-mono text-2xl font-medium tabular-nums text-foreground">
                {window.start}–{window.end}
              </div>
            </div>
            <div className="ml-auto hidden font-mono text-xs text-muted-foreground sm:block">
              {detection.id}
            </div>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            {signals.map((signal) => (
              <SignalCard key={signal.id} signal={signal} />
            ))}
          </div>
        </div>
      </div>
    </GlassPanel>
  )
}
