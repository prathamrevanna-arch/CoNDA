import type { ReactNode } from "react"

type Props = {
  title: string
  subtitle?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}

export function Panel({ title, subtitle, action, children, className }: Props) {
  return (
    <section className={`flex flex-col rounded-xl border border-navy-border bg-navy-card ${className ?? ""}`}>
      <div className="flex items-center justify-between gap-2 border-b border-navy-border px-4 py-2.5">
        <div className="leading-tight">
          <h2 className="text-sm font-semibold tracking-tight text-ink">{title}</h2>
          {subtitle && <p className="text-xs text-ink-faint">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className="flex-1 p-4">{children}</div>
    </section>
  )
}
