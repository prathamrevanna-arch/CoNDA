import Link from 'next/link'
import { cn } from '@/lib/utils'
import type { ReactNode } from 'react'

interface CtaButtonProps {
  href: string
  children: ReactNode
  variant?: 'primary' | 'secondary'
  className?: string
  icon?: ReactNode
}

export function CtaButton({
  href,
  children,
  variant = 'primary',
  className,
  icon,
}: CtaButtonProps) {
  return (
    <Link
      href={href}
      className={cn(
        'group inline-flex items-center justify-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        variant === 'primary'
          ? 'bg-cyan text-background hover:brightness-110 hover:shadow-[0_0_28px_-6px_var(--cyan)]'
          : 'border border-border-strong bg-panel/50 text-foreground hover:border-cyan/40 hover:bg-panel',
        className,
      )}
    >
      {children}
      {icon && <span className="transition-transform duration-200 group-hover:translate-x-0.5">{icon}</span>}
    </Link>
  )
}
