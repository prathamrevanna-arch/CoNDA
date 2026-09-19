import { ArrowRight } from 'lucide-react'
import { CtaButton } from '@/components/cta-button'
import { CondaMark } from '@/components/conda-mark'

export function CtaSection() {
  return (
    <section className="relative border-t border-border py-24">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <div className="relative overflow-hidden rounded-2xl border border-border bg-panel/70 px-6 py-16 text-center sm:px-16">
          <div aria-hidden className="pointer-events-none absolute inset-0 bg-blueprint opacity-40" />
          <div
            aria-hidden
            className="pointer-events-none absolute left-1/2 top-0 h-[320px] w-[320px] -translate-x-1/2 rounded-full bg-cyan/15 blur-[100px]"
          />
          <div className="relative flex flex-col items-center">
            <CondaMark className="h-12 w-12" />
            <h2 className="mt-6 max-w-2xl font-display text-3xl leading-tight tracking-tight text-balance text-foreground sm:text-4xl">
              Put coordination under adjudication.
            </h2>
            <p className="mt-4 max-w-lg text-base leading-relaxed text-pretty text-muted-foreground">
              Step into the detection console and watch the counterfactual engine separate
              competition from collusion in real time.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <CtaButton href="/detection" icon={<ArrowRight className="h-4 w-4" />}>
                Launch Detection Console
              </CtaButton>
              <CtaButton href="/docs" variant="secondary">
                Explore the Docs
              </CtaButton>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
