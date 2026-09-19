import { cn } from '@/lib/utils'
import { levelForScore, riskColor, type RiskLevel } from '@/lib/data'

interface RiskGaugeProps {
  score: number
  max?: number
  size?: number
  className?: string
  label?: string
}

/**
 * A 270° dial gauge rendered as SVG. Static (server-rendered) — the fill
 * is derived from the score. Swap `score` for live data as needed.
 */
export function RiskGauge({
  score,
  max = 100,
  size = 220,
  className,
  label = 'Risk Score',
}: RiskGaugeProps) {
  const level: RiskLevel = levelForScore((score / max) * 100)
  const color = riskColor[level]

  const stroke = 10
  const r = (size - stroke * 2) / 2
  const cx = size / 2
  const cy = size / 2
  const gap = 90 // degrees of open gap at bottom
  const sweep = 360 - gap
  const startAngle = 90 + gap / 2

  const circumference = 2 * Math.PI * r
  const trackLen = (sweep / 360) * circumference
  const fillLen = (Math.min(score, max) / max) * trackLen

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        {/* track */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="var(--border-strong)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${trackLen} ${circumference}`}
          transform={`rotate(${startAngle} ${cx} ${cy})`}
        />
        {/* fill */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${fillLen} ${circumference}`}
          transform={`rotate(${startAngle} ${cx} ${cy})`}
          style={{ filter: `drop-shadow(0 0 8px color-mix(in oklch, ${color} 55%, transparent))` }}
        />
        {/* tick marks */}
        {Array.from({ length: 28 }).map((_, i) => {
          const a = ((startAngle + (i / 27) * sweep) * Math.PI) / 180
          const inner = r - stroke - 6
          const outer = r - stroke - 2
          return (
            <line
              key={i}
              x1={cx + Math.cos(a) * inner}
              y1={cy + Math.sin(a) * inner}
              x2={cx + Math.cos(a) * outer}
              y2={cy + Math.sin(a) * outer}
              stroke="var(--border-strong)"
              strokeWidth={1}
            />
          )
        })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="flex items-baseline gap-1 font-display">
          <span className="text-5xl font-semibold tabular-nums tracking-tight" style={{ color }}>
            {score}
          </span>
          <span className="font-mono text-sm text-muted-foreground">/ {max}</span>
        </div>
        <span className="mt-1 font-mono text-[0.65rem] tracking-[0.25em] text-muted-foreground uppercase">
          {label}
        </span>
      </div>
    </div>
  )
}
