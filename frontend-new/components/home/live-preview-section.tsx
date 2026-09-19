import { SectionHeading } from '@/components/section-heading'
import { GlassPanel } from '@/components/glass-panel'
import { CounterfactualChart } from '@/components/counterfactual-chart'
import { LiveTimeline } from '@/components/live-timeline'
import { CtaButton } from '@/components/cta-button'
import { featuredDetection, counterfactualSeries } from '@/lib/data'
import { ArrowRight } from 'lucide-react'

export function LivePreviewSection() {
  const { counterfactual } = featuredDetection
  return (
    <section className="relative border-t border-border py-24">
      <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute left-[-5%] top-1/3 h-[360px] w-[360px] rounded-full bg-cyan/[0.07] blur-[110px]" />
      </div>

      <div className="relative mx-auto max-w-6xl px-5 sm:px-8">
        <SectionHeading
          eyebrow="Counterfactual engine"
          title={
            <>
              When observed prices drift from what{' '}
              <span className="text-cyan">competition predicts</span>.
            </>
          }
          description="The counterfactual gap is the heart of CoNDA. A widening divergence under a shared shock is strong evidence of coordination — not coincidence."
        />

        <div className="mt-14 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
          <GlassPanel blueprint className="p-6 sm:p-8">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h3 className="font-display text-lg font-semibold text-foreground">
                  Price divergence
                </h3>
                <p className="mt-1 font-mono text-xs text-muted-foreground">
                  {featuredDetection.pair.source} ↔ {featuredDetection.pair.target} · window{' '}
                  {featuredDetection.window.start}–{featuredDetection.window.end}
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
            <div className="mt-8 border-t border-border pt-6">
              <CtaButton
                href="/explorer"
                variant="secondary"
                className="w-full"
                icon={<ArrowRight className="h-4 w-4" />}
              >
                Open the Explorer
              </CtaButton>
            </div>
          </GlassPanel>
        </div>
      </div>
    </section>
  )
}
