import type { Metadata } from 'next'
import { GlassPanel } from '@/components/glass-panel'
import { EvidencePanel } from '@/components/evidence-panel'
import { CounterfactualChart } from '@/components/counterfactual-chart'
import { LiveTimeline } from '@/components/live-timeline'
import { AgentNetwork } from '@/components/agent-network'
import { featuredDetection, counterfactualSeries } from '@/lib/data'

export const metadata: Metadata = {
  title: 'Detection Console — CoNDA',
  description:
    'Live adjudication of coordination risk between autonomous trading agents, backed by counterfactual evidence.',
}

export default function DetectionPage() {
  const { counterfactual, pair, window } = featuredDetection

  return (
    <div className="relative">
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-[400px] bg-blueprint mask-fade-b opacity-60" />

      <div className="relative mx-auto max-w-6xl px-5 pt-32 pb-24 sm:px-8 sm:pt-40">
        <div className="flex flex-col gap-3">
          <span className="inline-flex w-fit items-center gap-2 font-mono text-xs tracking-[0.2em] text-cyan uppercase">
            <span className="h-1.5 w-1.5 rounded-full bg-risk-high animate-conda-pulse" />
            Live adjudication
          </span>
          <h1 className="font-display text-4xl leading-tight tracking-tight text-balance text-foreground sm:text-5xl">
            Detection Console
          </h1>
          <p className="max-w-2xl text-lg text-pretty text-muted-foreground">
            A single detection under adjudication. The verdict is only as strong as the evidence
            behind it — so every score exposes its full reasoning.
          </p>
        </div>

        <div className="mt-12">
          <EvidencePanel detection={featuredDetection} />
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
          <GlassPanel blueprint className="p-6 sm:p-8">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="font-display text-lg font-semibold text-foreground">
                  Counterfactual divergence
                </h2>
                <p className="mt-1 font-mono text-xs text-muted-foreground">
                  {pair.source} ↔ {pair.target} · window {window.start}–{window.end}
                </p>
              </div>
              <span className="rounded-full border border-risk-high/30 bg-risk-high/10 px-3 py-1 font-mono text-xs text-risk-high">
                shock detected
              </span>
            </div>
            <CounterfactualChart
              data={counterfactualSeries}
              referencePrice={counterfactual.referencePrice}
              observedPrice={counterfactual.observedPrice}
              gapPct={counterfactual.gapPct}
            />
          </GlassPanel>

          <GlassPanel className="p-6 sm:p-8">
            <LiveTimeline />
          </GlassPanel>
        </div>

        <div className="mt-4">
          <GlassPanel className="overflow-hidden">
            <div className="flex flex-col gap-8 p-6 sm:p-8 lg:flex-row lg:items-center">
              <div className="flex-1">
                <h2 className="font-display text-lg font-semibold text-foreground">
                  Agent interaction graph
                </h2>
                <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
                  Edges represent measured coordination strength between agents. Brighter, faster
                  flows mark pairs whose behaviour most sharply diverges from the competitive
                  counterfactual.
                </p>
                <dl className="mt-6 flex flex-wrap gap-x-8 gap-y-4">
                  <LegendItem color="var(--risk-high)" label="High coordination" />
                  <LegendItem color="var(--risk-med)" label="Medium" />
                  <LegendItem color="var(--muted-foreground)" label="Competitive band" />
                </dl>
              </div>
              <div className="relative aspect-square w-full max-w-[320px] shrink-0 self-center">
                <AgentNetwork className="absolute inset-0" />
              </div>
            </div>
          </GlassPanel>
        </div>
      </div>
    </div>
  )
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
      <span className="font-mono text-xs text-muted-foreground">{label}</span>
    </div>
  )
}
