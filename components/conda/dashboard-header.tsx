"use client"

import { Activity, Radio } from "lucide-react"

type Props = {
  scenarioName: string
  connected: boolean
  runId: string
}

export function DashboardHeader({ scenarioName, connected, runId }: Props) {
  return (
    <header className="flex items-center justify-between gap-6 border-b border-navy-border bg-navy-card/60 px-5 py-3">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet/15 ring-1 ring-violet/30">
          <Activity className="h-5 w-5 text-violet" strokeWidth={2.4} />
        </div>
        <div className="leading-tight">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold tracking-tight text-ink">CoNDA</span>
            <span className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-widest text-ink-faint">
              detector
            </span>
          </div>
          <span className="text-xs text-ink-muted">Live Market Monitor</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden flex-col items-end leading-tight md:flex">
          <span className="text-[10px] uppercase tracking-wider text-ink-faint">Scenario</span>
          <span className="text-sm font-medium text-ink">{scenarioName}</span>
        </div>

        <div className="h-8 w-px bg-navy-border" />

        <div
          className="flex items-center gap-2 rounded-lg border px-2.5 py-1.5"
          style={{
            borderColor: connected ? "color-mix(in oklab, var(--verified) 40%, transparent)" : "var(--navy-border)",
            backgroundColor: connected ? "color-mix(in oklab, var(--verified) 12%, transparent)" : "transparent",
          }}
        >
          <span className="relative flex h-2 w-2">
            {connected && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-verified opacity-60" />
            )}
            <span
              className="relative inline-flex h-2 w-2 rounded-full"
              style={{ backgroundColor: connected ? "var(--verified)" : "var(--ink-faint)" }}
            />
          </span>
          <Radio className="h-3.5 w-3.5" style={{ color: connected ? "var(--verified)" : "var(--ink-faint)" }} />
          <span
            className="text-xs font-semibold"
            style={{ color: connected ? "var(--verified)" : "var(--ink-faint)" }}
          >
            {connected ? "WS Connected" : "Disconnected"}
          </span>
        </div>

        <div className="flex flex-col items-end leading-tight">
          <span className="text-[10px] uppercase tracking-wider text-ink-faint">Run ID</span>
          <span className="font-mono text-sm text-cyan">{runId}</span>
        </div>
      </div>
    </header>
  )
}
