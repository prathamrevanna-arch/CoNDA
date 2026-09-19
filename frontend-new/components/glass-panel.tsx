import { cn } from '@/lib/utils'
import type { ElementType, ReactNode } from 'react'

interface GlassPanelProps {
  as?: ElementType
  className?: string
  children: ReactNode
  /** Adds a faint blueprint grid texture behind the content. */
  blueprint?: boolean
  /** Slightly brighter surface for nested / raised panels. */
  raised?: boolean
}

export function GlassPanel({
  as: Tag = 'div',
  className,
  children,
  blueprint = false,
  raised = false,
}: GlassPanelProps) {
  return (
    <Tag
      className={cn(
        'relative overflow-hidden rounded-xl border border-border',
        raised ? 'bg-panel-raised' : 'bg-panel/70',
        'backdrop-blur-sm',
        className,
      )}
    >
      {blueprint && (
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-blueprint-fine opacity-60"
        />
      )}
      <div className="relative">{children}</div>
    </Tag>
  )
}
