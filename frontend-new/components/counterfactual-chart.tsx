import { cn } from '@/lib/utils'
import type { PricePoint } from '@/lib/data'

interface CounterfactualChartProps {
  data: PricePoint[]
  referencePrice: number
  observedPrice: number
  gapPct: number
  className?: string
}

const W = 640
const H = 260
const PAD = { top: 24, right: 16, bottom: 28, left: 16 }

export function CounterfactualChart({
  data,
  referencePrice,
  observedPrice,
  gapPct,
  className,
}: CounterfactualChartProps) {
  const values = data.flatMap((d) => [d.reference, d.observed])
  const min = Math.min(...values) - 0.5
  const max = Math.max(...values) + 0.5

  const x = (i: number) =>
    PAD.left + (i / (data.length - 1)) * (W - PAD.left - PAD.right)
  const y = (v: number) =>
    PAD.top + (1 - (v - min) / (max - min)) * (H - PAD.top - PAD.bottom)

  const line = (key: 'reference' | 'observed') =>
    data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${x(i).toFixed(1)} ${y(d[key]).toFixed(1)}`).join(' ')

  const gapArea =
    data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${x(i).toFixed(1)} ${y(d.observed).toFixed(1)}`).join(' ') +
    ' ' +
    [...data].reverse().map((d, i) => {
      const idx = data.length - 1 - i
      return `L ${x(idx).toFixed(1)} ${y(d.reference).toFixed(1)}`
    }).join(' ') +
    ' Z'

  return (
    <div className={cn('w-full', className)}>
      <div className="mb-5 grid grid-cols-3 gap-3">
        <Stat label="Reference Price" value={`$${referencePrice.toFixed(2)}`} tone="muted" />
        <Stat label="Observed Price" value={`$${observedPrice.toFixed(2)}`} tone="cyan" />
        <Stat label="Gap" value={`+${gapPct.toFixed(1)}%`} tone="high" />
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        role="img"
        aria-label={`Observed price diverges from the competitive counterfactual by ${gapPct}%`}
      >
        <defs>
          <linearGradient id="gapFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--risk-high)" stopOpacity="0.28" />
            <stop offset="100%" stopColor="var(--risk-high)" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* gridlines */}
        {[0.25, 0.5, 0.75].map((f) => (
          <line
            key={f}
            x1={PAD.left}
            x2={W - PAD.right}
            y1={PAD.top + f * (H - PAD.top - PAD.bottom)}
            y2={PAD.top + f * (H - PAD.top - PAD.bottom)}
            stroke="var(--border)"
            strokeDasharray="2 4"
          />
        ))}

        {/* divergence area */}
        <path d={gapArea} fill="url(#gapFill)" />

        {/* reference (counterfactual) */}
        <path
          d={line('reference')}
          fill="none"
          stroke="var(--muted-foreground)"
          strokeWidth="1.75"
          strokeDasharray="5 4"
        />
        {/* observed */}
        <path
          d={line('observed')}
          fill="none"
          stroke="var(--cyan)"
          strokeWidth="2.25"
          style={{ filter: 'drop-shadow(0 0 6px color-mix(in oklch, var(--cyan) 50%, transparent))' }}
        />

        {/* end markers */}
        <circle cx={x(data.length - 1)} cy={y(data[data.length - 1].observed)} r="4" fill="var(--cyan)" />
        <circle
          cx={x(data.length - 1)}
          cy={y(data[data.length - 1].reference)}
          r="3.5"
          fill="var(--background)"
          stroke="var(--muted-foreground)"
          strokeWidth="1.5"
        />
      </svg>

      <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 font-mono text-xs text-muted-foreground">
        <span className="flex items-center gap-2">
          <span className="h-0.5 w-5 rounded bg-cyan" /> Observed
        </span>
        <span className="flex items-center gap-2">
          <span className="h-0 w-5 border-t-2 border-dashed border-muted-foreground" /> Counterfactual
        </span>
        <span className="ml-auto text-muted-foreground/70">Window 150–189</span>
      </div>
    </div>
  )
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone: 'muted' | 'cyan' | 'high'
}) {
  const color =
    tone === 'cyan' ? 'text-cyan' : tone === 'high' ? 'text-risk-high' : 'text-foreground'
  return (
    <div className="rounded-lg border border-border bg-panel/60 px-3 py-3">
      <div className="font-mono text-[0.62rem] tracking-[0.16em] text-muted-foreground uppercase">
        {label}
      </div>
      <div className={cn('mt-1.5 font-mono text-lg font-medium tabular-nums', color)}>{value}</div>
    </div>
  )
}
