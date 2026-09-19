import { cn } from '@/lib/utils'
import type { RiskLevel } from '@/lib/data'

const styles: Record<RiskLevel, string> = {
  LOW: 'text-risk-low border-risk-low/30 bg-risk-low/10',
  MEDIUM: 'text-risk-med border-risk-med/30 bg-risk-med/10',
  HIGH: 'text-risk-high border-risk-high/30 bg-risk-high/10',
}

const dot: Record<RiskLevel, string> = {
  LOW: 'bg-risk-low',
  MEDIUM: 'bg-risk-med',
  HIGH: 'bg-risk-high',
}

interface RiskBadgeProps {
  level: RiskLevel
  className?: string
  size?: 'sm' | 'md'
}

export function RiskBadge({ level, className, size = 'md' }: RiskBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border font-mono font-medium tracking-wider uppercase',
        size === 'sm' ? 'px-2 py-0.5 text-[0.65rem]' : 'px-2.5 py-1 text-xs',
        styles[level],
        className,
      )}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', dot[level], level === 'HIGH' && 'animate-conda-pulse')} />
      {level}
    </span>
  )
}
