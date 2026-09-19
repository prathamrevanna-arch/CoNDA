import { ArrowRight, Activity } from 'lucide-react'
import { AgentNetwork } from '@/components/agent-network'
import { CtaButton } from '@/components/cta-button'

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      {/* ambient background */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-blueprint mask-fade-b opacity-70" />
        <div className="absolute left-1/2 top-[-10%] h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-cyan/10 blur-[120px]" />
        <div className="absolute right-[10%] top-[30%] h-[280px] w-[280px] rounded-full bg-risk-high/10 blur-[100px]" />
      </div>

      <div className="relative mx-auto max-w-6xl px-5 pt-32 pb-20 sm:px-8 sm:pt-40 lg:pt-44">
        <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
          {/* copy */}
          <div className="flex flex-col items-start">
            <div className="inline-flex items-center gap-2 rounded-full border border-border bg-panel/60 px-3 py-1.5 backdrop-blur-sm">
              <Activity className="h-3.5 w-3.5 text-cyan" />
              <span className="font-mono text-xs tracking-wide text-muted-foreground">
                Coordination Detection &amp; Adjudication
              </span>
            </div>

            <h1 className="mt-6 font-display text-5xl leading-[0.98] tracking-tight text-balance text-foreground sm:text-6xl lg:text-[4.25rem]">
              Detecting collusion between{' '}
              <span className="text-cyan">autonomous agents</span>.
            </h1>

            <p className="mt-6 max-w-xl text-lg leading-relaxed text-pretty text-muted-foreground">
              CoNDA observes autonomous trading agents in simulated DeFi markets and adjudicates
              whether their behaviour reflects genuine competition — or coordinated collusion.
              Built on competitive counterfactuals, not correlation.
            </p>

            <div className="mt-9 flex flex-wrap items-center gap-3">
              <CtaButton href="/detection" icon={<ArrowRight className="h-4 w-4" />}>
                Launch Detection Console
              </CtaButton>
              <CtaButton href="/methodology" variant="secondary">
                Read the Methodology
              </CtaButton>
            </div>

            <dl className="mt-12 grid w-full max-w-md grid-cols-3 gap-6 border-t border-border pt-8">
              <Metric value="4" label="Agents observed" />
              <Metric value="270°" label="Risk adjudication" />
              <Metric value="6-stage" label="Evidence pipeline" />
            </dl>
          </div>

          {/* network centerpiece */}
          <div className="relative">
            <div className="relative aspect-square w-full">
              <div aria-hidden className="absolute inset-0 rounded-full border border-border/60" />
              <div aria-hidden className="absolute inset-[12%] rounded-full border border-border/40" />
              <div aria-hidden className="absolute inset-[26%] rounded-full border border-border/25" />
              <AgentNetwork className="absolute inset-0" />
            </div>
            <div className="pointer-events-none absolute -bottom-2 left-1/2 -translate-x-1/2 rounded-full border border-border bg-background/80 px-4 py-1.5 font-mono text-xs text-muted-foreground backdrop-blur-sm">
              <span className="text-risk-high">●</span> A2 ↔ A3 coordination detected
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function Metric({ value, label }: { value: string; label: string }) {
  return (
    <div className="flex flex-col">
      <dt className="font-display text-2xl font-semibold tracking-tight text-foreground">
        {value}
      </dt>
      <dd className="mt-1 font-mono text-[0.7rem] leading-snug tracking-wide text-muted-foreground uppercase">
        {label}
      </dd>
    </div>
  )
}
