import { SectionHeading } from '@/components/section-heading'
import { Pipeline } from '@/components/pipeline'

export function PipelineSection() {
  return (
    <section className="relative border-t border-border py-24">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <SectionHeading
          eyebrow="How it works"
          title={
            <>
              From raw order flow to a{' '}
              <span className="text-cyan">calibrated risk verdict</span>.
            </>
          }
          description="Every detection travels the same auditable path. Market behaviour is measured against a competitive counterfactual — the outcome we'd expect from agents that were genuinely competing."
        />
        <div className="mt-14">
          <Pipeline />
        </div>
      </div>
    </section>
  )
}
