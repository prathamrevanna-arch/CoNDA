import { cn } from '@/lib/utils'
import { pipelineStages } from '@/lib/data'
import { ArrowRight } from 'lucide-react'
import { Fragment } from 'react'

export function Pipeline({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'flex w-full flex-col items-stretch gap-2 lg:flex-row lg:items-center',
        className,
      )}
    >
      {pipelineStages.map((stage, i) => (
        <Fragment key={stage.id}>
          <div className="group relative flex-1 rounded-xl border border-border bg-panel/60 p-4 transition-colors hover:border-cyan/40">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-cyan">{String(i + 1).padStart(2, '0')}</span>
              <span
                className={cn(
                  'h-1 w-1 rounded-full bg-cyan/60',
                  i === pipelineStages.length - 1 && 'bg-risk-high animate-conda-pulse',
                )}
              />
            </div>
            <h3 className="mt-3 font-display text-sm font-semibold text-foreground">
              {stage.label}
            </h3>
            <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{stage.detail}</p>
          </div>

          {i < pipelineStages.length - 1 && (
            <div className="flex shrink-0 items-center justify-center py-1 lg:py-0">
              <ArrowRight className="h-4 w-4 rotate-90 text-muted-foreground/45 lg:rotate-0" />
            </div>
          )}
        </Fragment>
      ))}
    </div>
  )
}
