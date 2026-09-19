import type { Metadata } from 'next'
import { GlassPanel } from '@/components/glass-panel'
import { SectionHeading } from '@/components/section-heading'
import { Pipeline } from '@/components/pipeline'
import { CounterfactualChart } from '@/components/counterfactual-chart'
import { featuredDetection, counterfactualSeries } from '@/lib/data'

export const metadata: Metadata = {
  title: 'Methodology — CoNDA',
  description:
    'How CoNDA distinguishes coordination from correlation using competitive counterfactuals and weighted evidence signals.',
}

const stages = [
  {
    n: '01',
    title: 'Observe',
    body: 'Per-agent order flow, quotes and fills are streamed and normalized into a common event clock.',
  },
  {
    n: '02',
    title: 'Simulate the counterfactual',
    body: 'For each window we simulate how rational, non-colluding competitors would have priced given the same public information — the competitive counterfactual.',
  },
  {
    n: '03',
    title: 'Measure divergence',
    body: 'Observed joint behaviour is compared against the counterfactual. Divergence, synchrony and lead/lag structure become quantified signals.',
  },
  {
    n: '04',
    title: 'Adjudicate',
    body: 'Signals are weighted into a single calibrated coordination risk score, with every contribution attributable back to its evidence.',
  },
]

export default function MethodologyPage() {
  const { counterfactual } = featuredDetection

  return (
    <div className="relative">
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-[420px] bg-blueprint mask-fade-b opacity-60" />

      <div className="relative mx-auto max-w-5xl px-5 pt-32 pb-24 sm:px-8 sm:pt-40">
        <div className="flex flex-col gap-3">
          <span className="inline-flex w-fit items-center gap-2 font-mono text-xs tracking-[0.2em] text-cyan uppercase">
            <span className="h-1 w-1 rounded-full bg-cyan animate-conda-pulse" />
            Methodology
          </span>
          <h1 className="max-w-3xl font-display text-4xl leading-[1.08] tracking-tight text-balance text-foreground sm:text-5xl">
            Correlation is cheap. Coordination has to be proven.
          </h1>
          <p className="max-w-2xl text-lg text-pretty text-muted-foreground">
            Two agents moving together is not evidence of collusion — competitive markets produce
            correlated behaviour all the time. CoNDA asks a sharper question: would rational
            competitors have behaved this way on their own?
          </p>
        </div>

        {/* Counterfactual definition */}
        <GlassPanel blueprint className="mt-14 p-6 sm:p-8">
          <SectionHeading
            eyebrow="The core idea"
            title="The competitive counterfactual"
            description="We model a world in which each agent optimizes independently against the same market conditions. The gap between that world and the observed one is the raw material of every detection."
          />
          <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_1.1fr] lg:items-center">
            <div className="flex flex-col gap-5">
              <div className="rounded-xl border border-border bg-background/50 p-5">
                <div className="font-mono text-[0.62rem] tracking-[0.16em] text-muted-foreground uppercase">
                  Coordination risk
                </div>
                <div className="mt-4 flex items-center justify-center gap-2 font-mono text-xl text-foreground">
                  <span className="italic">R</span>
                  <span className="text-muted-foreground">=</span>
                  <span className="text-cyan">σ</span>
                  <span className="text-muted-foreground">(</span>
                  <span className="relative inline-flex flex-col items-center leading-none">
                    <span className="text-[0.55em] text-muted-foreground">k</span>
                    <span className="text-2xl">Σ</span>
                  </span>
                  <span className="italic">
                    w<sub className="text-[0.6em]">k</sub>
                  </span>
                  <span className="italic">
                    s<sub className="text-[0.6em]">k</sub>
                  </span>
                  <span className="text-muted-foreground">)</span>
                </div>
                <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
                  Each signal{' '}
                  <span className="font-mono text-foreground">
                    s<sub>k</sub>
                  </span>{' '}
                  measures a distinct departure from the counterfactual and{' '}
                  <span className="font-mono text-foreground">
                    w<sub>k</sub>
                  </span>{' '}
                  is its calibrated weight. The logistic{' '}
                  <span className="font-mono text-cyan">σ</span> maps the weighted sum onto a bounded
                  0–100 risk scale.
                </p>
              </div>
              <div className="rounded-xl border border-border bg-background/50 p-5">
                <div className="font-mono text-[0.62rem] tracking-[0.16em] text-muted-foreground uppercase">
                  Counterfactual gap
                </div>
                <div className="mt-4 flex items-center justify-center gap-3 font-mono text-xl text-foreground">
                  <span className="italic">g</span>
                  <span className="text-muted-foreground">=</span>
                  <span className="inline-flex flex-col items-center">
                    <span className="px-2 pb-1">
                      p<sub className="text-[0.6em]">obs</sub> − p
                      <sub className="text-[0.6em]">cf</sub>
                    </span>
                    <span className="w-full border-t border-border-strong px-2 pt-1">
                      p<sub className="text-[0.6em]">cf</sub>
                    </span>
                  </span>
                </div>
                <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
                  A persistent positive gap under a shared shock is a strong coordination signature —
                  independent competitors would compete the gap away.
                </p>
              </div>
            </div>

            <div className="rounded-xl border border-border bg-background/40 p-5">
              <CounterfactualChart
                data={counterfactualSeries}
                referencePrice={counterfactual.referencePrice}
                observedPrice={counterfactual.observedPrice}
                gapPct={counterfactual.gapPct}
              />
            </div>
          </div>
        </GlassPanel>

        {/* Steps */}
        <div className="mt-20">
          <SectionHeading
            eyebrow="Four steps"
            title="From raw order flow to an adjudicated verdict"
          />
          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            {stages.map((s) => (
              <GlassPanel key={s.n} className="p-6">
                <div className="font-mono text-sm text-cyan">{s.n}</div>
                <h3 className="mt-3 font-display text-xl font-semibold text-foreground">
                  {s.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.body}</p>
              </GlassPanel>
            ))}
          </div>
        </div>

        {/* Full pipeline */}
        <div className="mt-20">
          <SectionHeading
            eyebrow="End to end"
            title="The detection pipeline"
            description="Every stage is inspectable. Nothing about a verdict is hidden behind an opaque score."
          />
          <GlassPanel className="mt-8 p-6 sm:p-8">
            <Pipeline />
          </GlassPanel>
        </div>
      </div>
    </div>
  )
}
