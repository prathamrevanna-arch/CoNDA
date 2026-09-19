'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { ArrowRight, Menu, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { CondaMark } from '@/components/conda-mark'

const links = [
  { href: '/detection', label: 'Detection' },
  { href: '/explorer', label: 'Explorer' },
  { href: '/methodology', label: 'Methodology' },
  { href: '/docs', label: 'Docs' },
]

export function Navbar() {
  const pathname = usePathname()
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    setOpen(false)
  }, [pathname])

  return (
    <header className="fixed inset-x-0 top-0 z-50">
      <div
        className={cn(
          'transition-colors duration-300',
          scrolled
            ? 'border-b border-border bg-background/80 backdrop-blur-xl'
            : 'border-b border-transparent',
        )}
      >
        <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
          <Link href="/" className="flex items-center gap-2.5" aria-label="CoNDA home">
            <CondaMark className="h-7 w-7" />
            <div className="flex flex-col leading-none">
              <span className="font-display text-base font-semibold tracking-tight text-foreground">
                CoNDA
              </span>
              <span className="mt-0.5 font-mono text-[0.6rem] tracking-[0.18em] text-muted-foreground uppercase">
                Detection &amp; Adjudication
              </span>
            </div>
          </Link>

          <div className="hidden items-center gap-1 md:flex">
            {links.map((link) => {
              const active = pathname === link.href
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    'relative rounded-md px-3 py-2 text-sm transition-colors',
                    active
                      ? 'text-foreground'
                      : 'text-muted-foreground hover:text-foreground',
                  )}
                >
                  {link.label}
                  {active && (
                    <span className="absolute inset-x-3 -bottom-px h-px bg-cyan" />
                  )}
                </Link>
              )
            })}
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/detection"
              className="hidden items-center gap-1.5 rounded-lg bg-cyan px-4 py-2 text-sm font-medium text-background transition-all hover:shadow-[0_0_24px_-6px_var(--cyan)] sm:inline-flex"
            >
              Launch Detection
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border text-foreground md:hidden"
              aria-label={open ? 'Close menu' : 'Open menu'}
              aria-expanded={open}
            >
              {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </nav>
      </div>

      {/* Mobile menu */}
      <div
        className={cn(
          'overflow-hidden border-b border-border bg-background/95 backdrop-blur-xl transition-[max-height] duration-300 md:hidden',
          open ? 'max-h-96' : 'max-h-0',
        )}
      >
        <div className="mx-auto flex max-w-6xl flex-col gap-1 px-5 py-4 sm:px-8">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                'rounded-lg px-3 py-3 text-sm transition-colors',
                pathname === link.href
                  ? 'bg-panel text-foreground'
                  : 'text-muted-foreground hover:bg-panel/60 hover:text-foreground',
              )}
            >
              {link.label}
            </Link>
          ))}
          <Link
            href="/detection"
            className="mt-2 inline-flex items-center justify-center gap-1.5 rounded-lg bg-cyan px-4 py-3 text-sm font-medium text-background"
          >
            Launch Detection
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
    </header>
  )
}
