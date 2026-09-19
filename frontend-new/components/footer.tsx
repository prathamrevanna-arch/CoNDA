import Link from 'next/link'
import { CondaMark } from '@/components/conda-mark'

const columns = [
  {
    title: 'Platform',
    links: [
      { href: '/detection', label: 'Detection' },
      { href: '/explorer', label: 'Explorer' },
      { href: '/methodology', label: 'Methodology' },
      { href: '/docs', label: 'Docs' },
    ],
  },
  {
    title: 'Research',
    links: [
      { href: '/methodology', label: 'Counterfactuals' },
      { href: '/methodology', label: 'Detection Signals' },
      { href: '/methodology', label: 'Adjudication' },
      { href: '/docs', label: 'Reproducibility' },
    ],
  },
  {
    title: 'Resources',
    links: [
      { href: '/docs', label: 'API Reference' },
      { href: '/docs', label: 'WebSocket Feed' },
      { href: '/docs', label: 'Data Schema' },
      { href: '/docs', label: 'Changelog' },
    ],
  },
]

export function Footer() {
  return (
    <footer className="relative border-t border-border bg-background">
      <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8">
        <div className="grid grid-cols-2 gap-10 md:grid-cols-[1.4fr_repeat(3,1fr)]">
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center gap-2.5">
              <CondaMark className="h-7 w-7" />
              <span className="font-display text-base font-semibold tracking-tight">CoNDA</span>
            </Link>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground">
              Coordination Detection &amp; Adjudication for autonomous agents in simulated DeFi
              markets.
            </p>
            <p className="mt-6 font-mono text-xs tracking-wide text-cyan">
              Correlation ≠ coordination.
            </p>
          </div>

          {columns.map((col) => (
            <div key={col.title}>
              <h3 className="font-mono text-[0.7rem] tracking-[0.2em] text-muted-foreground uppercase">
                {col.title}
              </h3>
              <ul className="mt-4 flex flex-col gap-3">
                {col.links.map((link, i) => (
                  <li key={`${link.label}-${i}`}>
                    <Link
                      href={link.href}
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-14 flex flex-col items-start justify-between gap-4 border-t border-border pt-6 sm:flex-row sm:items-center">
          <p className="font-mono text-xs text-muted-foreground">
            © {new Date().getFullYear()} CoNDA Research. Concept interface.
          </p>
          <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-risk-low animate-conda-pulse" />
            Detection engine: nominal
          </div>
        </div>
      </div>
    </footer>
  )
}
