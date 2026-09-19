import { cn } from '@/lib/utils'
import { RiskBadge } from '@/components/risk-badge'
import { timelineEvents, type TimelineEvent } from '@/lib/data'

interface LiveTimelineProps {
  events?: TimelineEvent[]
  className?: string
}

export function LiveTimeline({ events = timelineEvents, className }: LiveTimelineProps) {
  return (
    <div className={cn('flex flex-col', className)}>
      <div className="mb-4 flex items-center justify-between">
        <span className="font-mono text-[0.7rem] tracking-[0.2em] text-muted-foreground uppercase">
          Live detection feed
        </span>
        <span className="flex items-center gap-2 font-mono text-xs text-risk-low">
          <span className="h-1.5 w-1.5 rounded-full bg-risk-low animate-conda-pulse" />
          streaming
        </span>
      </div>

      <ol className="relative flex flex-col">
        <span aria-hidden className="absolute top-2 bottom-2 left-[5px] w-px bg-border" />
        {events.map((event) => (
          <li key={event.id} className="relative flex items-start gap-4 py-3 pl-6">
            <span
              className={cn(
                'absolute top-4 left-0 h-[11px] w-[11px] rounded-full border-2 border-background',
                event.level === 'HIGH'
                  ? 'bg-risk-high'
                  : event.level === 'MEDIUM'
                    ? 'bg-risk-med'
                    : 'bg-risk-low',
              )}
            />
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs text-muted-foreground">
                  tick {event.tick}
                </span>
                <span className="font-mono text-xs text-foreground">
                  {event.pair.source} ↔ {event.pair.target}
                </span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{event.message}</p>
            </div>
            <RiskBadge level={event.level} size="sm" />
          </li>
        ))}
      </ol>
    </div>
  )
}
