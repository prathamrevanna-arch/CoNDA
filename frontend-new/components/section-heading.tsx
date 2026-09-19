import { cn } from '@/lib/utils'
import type { ReactNode } from 'react'

interface SectionHeadingProps {
  eyebrow?: string
  title: ReactNode
  description?: ReactNode
  align?: 'left' | 'center'
  className?: string
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  align = 'left',
  className,
}: SectionHeadingProps) {
  return (
    <div
      className={cn(
        'flex max-w-2xl flex-col gap-4',
        align === 'center' && 'mx-auto items-center text-center',
        className,
      )}
    >
      {eyebrow && (
        <div
          className={cn(
            'flex items-center gap-2.5 font-mono text-xs tracking-[0.2em] text-cyan uppercase',
          )}
        >
          <span className="h-1 w-1 rounded-full bg-cyan animate-conda-pulse" />
          {eyebrow}
        </div>
      )}
      <h2 className="font-display text-3xl leading-[1.05] tracking-tight text-balance text-foreground sm:text-4xl md:text-[2.75rem]">
        {title}
      </h2>
      {description && (
        <p className="max-w-xl text-base leading-relaxed text-pretty text-muted-foreground">
          {description}
        </p>
      )}
    </div>
  )
}
