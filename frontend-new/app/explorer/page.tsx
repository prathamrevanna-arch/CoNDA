import type { Metadata } from 'next'
import { DetectionTable } from '@/components/explorer/detection-table'

export const metadata: Metadata = {
  title: 'Explorer — CoNDA',
  description:
    'Browse and inspect every coordination detection across agent pairs, sorted by risk and window.',
}

export default function ExplorerPage() {
  return (
    <div className="relative">
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-[360px] bg-blueprint mask-fade-b opacity-50" />
      <div className="relative mx-auto max-w-6xl px-5 pt-32 pb-24 sm:px-8 sm:pt-40">
        <div className="flex flex-col gap-3">
          <span className="inline-flex w-fit items-center gap-2 font-mono text-xs tracking-[0.2em] text-cyan uppercase">
            <span className="h-1 w-1 rounded-full bg-cyan animate-conda-pulse" />
            Detection feed
          </span>
          <h1 className="font-display text-4xl leading-tight tracking-tight text-balance text-foreground sm:text-5xl">
            Explorer
          </h1>
          <p className="max-w-2xl text-lg text-pretty text-muted-foreground">
            Every adjudicated detection across all agent pairs. Filter by risk, sort by score or
            window, and select a row to inspect its evidence.
          </p>
        </div>

        <div className="mt-12">
          <DetectionTable />
        </div>
      </div>
    </div>
  )
}
