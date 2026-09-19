import { cn } from '@/lib/utils'
import { GlassPanel } from '@/components/glass-panel'
import type { EvidenceSignal } from '@/lib/data'

interface SignalCardProps {
  signal: EvidenceSignal
  /** Max contribution used to scale the bar. */
  max?: number
  className?: string
}

export function SignalCard({ signal, max = 50, className }: SignalCardProps) {
  const pct = Math.min((signal.contribution / max) * 100, 100)
  return (
    <GlassPanel raised className={cn('p-5', className)}>
      <div className="flex items-start justify-between gap-4">
        <span className="font-mono text-[0.7rem] tracking-[0.18em] text-muted-foreground uppercase">
          {signal.label}
        </span>
        <span className="font-mono text-xs text-cyan">signal</span>
      </div>
      <div className="mt-4 flex items-baseline gap-2">
        <span className="font-display text-3xl font-semibold tabular-nums text-foreground">
          {signal.contribution}
        </span>
        <span className="font-mono text-xs text-muted-foreground">contribution</span>
      </div>
      <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-border-strong">
        <div
          className="h-full rounded-full bg-cyan"
          style={{
            width: `${pct}%`,
            boxShadow: '0 0 12px -2px color-mix(in oklch, var(--cyan) 70%, transparent)',
          }}
        />
      </div>
      {signal.description && (
        <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{signal.description}</p>
      )}
    </GlassPanel>
  )
}
