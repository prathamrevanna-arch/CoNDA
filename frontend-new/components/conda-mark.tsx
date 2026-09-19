import { cn } from '@/lib/utils'

export function CondaMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      className={cn('text-cyan', className)}
      aria-hidden
    >
      <rect x="0.5" y="0.5" width="31" height="31" rx="7" className="fill-panel stroke-border" />
      <g stroke="currentColor" strokeWidth="1.4">
        <line x1="9" y1="10" x2="22" y2="9" opacity="0.45" />
        <line x1="9" y1="10" x2="11" y2="23" opacity="0.45" />
        <line x1="22" y1="9" x2="23" y2="22" opacity="0.9" />
        <line x1="11" y1="23" x2="23" y2="22" opacity="0.45" />
        <line x1="9" y1="10" x2="23" y2="22" opacity="0.25" />
      </g>
      <g className="fill-panel" stroke="currentColor" strokeWidth="1.4">
        <circle cx="9" cy="10" r="2.4" />
        <circle cx="11" cy="23" r="2.4" />
      </g>
      <g fill="currentColor">
        <circle cx="22" cy="9" r="2.6" />
        <circle cx="23" cy="22" r="2.6" />
      </g>
    </svg>
  )
}
