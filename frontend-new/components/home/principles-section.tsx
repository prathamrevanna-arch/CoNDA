import { SectionHeading } from '@/components/section-heading'
import { GlassPanel } from '@/components/glass-panel'
import { GitCompare, Radar, Scale } from 'lucide-react'

const principles = [
  {
    icon: Radar,
    title: 'Observe behaviour, not intent',
    body: 'Agents never declare collusion. CoNDA reads quotes, fills and timing — the observable footprint of how agents actually behave under market pressure.',
  },
  {
    icon: GitCompare,
    title: 'Compare against a counterfactual',
    body: 'A competitive counterfactual simulates rational, non-colluding rivals. Coordination reveals itself as a persistent gap from that baseline.',
  },
  {
    icon: Scale,
    title: 'Adjudicate with calibrated evidence',
    body: 'Signals are weighted into a single coordination-risk score. Every verdict carries the evidence that produced it — auditable and reproducible.',
  },
]

export function PrinciplesSection() {
  return (
    <section className="relative border-t border-border py-24">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <SectionHeading
          eyebrow="Principles"
          align="center"
          title={
            <>
              Correlation is not coordination.
            </>
          }
          description="Two agents moving together may simply be reacting to the same market. CoNDA is designed to tell the difference."
        />

        <div className="mt-14 grid gap-4 md:grid-cols-3">
          {principles.map((principle) => (
            <GlassPanel key={principle.title} raised className="group p-6">
              <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-border bg-background/60 text-cyan transition-colors group-hover:border-cyan/40">
                <principle.icon className="h-5 w-5" />
              </div>
              <h3 className="mt-5 font-display text-lg font-semibold text-foreground">
                {principle.title}
              </h3>
              <p className="mt-2.5 text-sm leading-relaxed text-muted-foreground">
                {principle.body}
              </p>
            </GlassPanel>
          ))}
        </div>
      </div>
    </section>
  )
}
