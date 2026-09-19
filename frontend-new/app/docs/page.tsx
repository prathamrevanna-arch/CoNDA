import type { Metadata } from 'next'
import { GlassPanel } from '@/components/glass-panel'
import { CtaButton } from '@/components/cta-button'
import { ArrowRight } from 'lucide-react'

export const metadata: Metadata = {
  title: 'Docs — CoNDA',
  description:
    'Reference for the CoNDA coordination detection API — endpoints, payload shapes and risk semantics.',
}

const sections = [
  { id: 'overview', label: 'Overview' },
  { id: 'concepts', label: 'Core concepts' },
  { id: 'detections', label: 'Detections API' },
  { id: 'signals', label: 'Evidence signals' },
  { id: 'stream', label: 'Live stream' },
]

export default function DocsPage() {
  return (
    <div className="relative">
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-[300px] bg-blueprint mask-fade-b opacity-40" />
      <div className="relative mx-auto max-w-6xl px-5 pt-32 pb-24 sm:px-8 sm:pt-40">
        <div className="flex flex-col gap-3">
          <span className="inline-flex w-fit items-center gap-2 font-mono text-xs tracking-[0.2em] text-cyan uppercase">
            <span className="h-1 w-1 rounded-full bg-cyan animate-conda-pulse" />
            Documentation
          </span>
          <h1 className="font-display text-4xl leading-tight tracking-tight text-balance text-foreground sm:text-5xl">
            Docs
          </h1>
          <p className="max-w-2xl text-lg text-pretty text-muted-foreground">
            A conceptual reference for the CoNDA detection interface. The payloads below mirror the
            data contract this frontend already consumes.
          </p>
        </div>

        <div className="mt-12 grid gap-8 lg:grid-cols-[200px_1fr]">
          {/* sidebar */}
          <aside className="lg:sticky lg:top-24 lg:self-start">
            <nav className="flex flex-col gap-1">
              {sections.map((s) => (
                <a
                  key={s.id}
                  href={`#${s.id}`}
                  className="rounded-lg px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-panel hover:text-foreground"
                >
                  {s.label}
                </a>
              ))}
            </nav>
          </aside>

          <div className="flex flex-col gap-12">
            <DocSection id="overview" title="Overview">
              <p>
                CoNDA (Coordination Detection &amp; Adjudication) monitors autonomous market agents
                and flags behaviour that is unlikely to arise from independent competition. It is a
                detection and evidence system — not an enforcement tool. Every verdict is
                accompanied by the reasoning that produced it.
              </p>
              <p>
                The guiding principle is simple:{' '}
                <span className="text-foreground">correlation is not coordination.</span> A high
                risk score only appears when observed behaviour departs from a simulated competitive
                counterfactual in ways that independent agents would not.
              </p>
            </DocSection>

            <DocSection id="concepts" title="Core concepts">
              <DefRow term="Agent" def="An autonomous participant (A1–A4) that quotes and trades." />
              <DefRow
                term="Window"
                def="An overlapping slice of the event clock over which behaviour is analyzed."
              />
              <DefRow
                term="Counterfactual"
                def="A simulation of how rational, non-colluding competitors would have acted given the same public state."
              />
              <DefRow
                term="Signal"
                def="A quantified departure from the counterfactual — e.g. counterfactual gap or synchrony under shock."
              />
              <DefRow
                term="Risk score"
                def="A calibrated 0–100 adjudication combining weighted signals. ≥66 HIGH · 33–65 MEDIUM · <33 LOW."
              />
            </DocSection>

            <DocSection id="detections" title="Detections API">
              <p>
                Retrieve adjudicated detections. Each row carries its full evidence so clients never
                need to trust an opaque number.
              </p>
              <CodeBlock label="GET /v1/detections">{detectionsPayload}</CodeBlock>
            </DocSection>

            <DocSection id="signals" title="Evidence signals">
              <p>
                Signals are the atoms of an adjudication. Their weighted{' '}
                <span className="font-mono text-foreground">contribution</span> values sum toward the
                final score and are always returned alongside it.
              </p>
              <CodeBlock label="signal object">{signalPayload}</CodeBlock>
            </DocSection>

            <DocSection id="stream" title="Live stream">
              <p>
                A WebSocket channel emits timeline events as windows are adjudicated in near
                real-time. The Detection console consumes this stream directly.
              </p>
              <CodeBlock label="WS /v1/stream">{streamPayload}</CodeBlock>

              <div className="mt-6 flex flex-wrap gap-3">
                <CtaButton href="/detection" icon={<ArrowRight className="h-3.5 w-3.5" />}>
                  Open the console
                </CtaButton>
                <CtaButton href="/methodology" variant="secondary">
                  Read the methodology
                </CtaButton>
              </div>
            </DocSection>
          </div>
        </div>
      </div>
    </div>
  )
}

function DocSection({
  id,
  title,
  children,
}: {
  id: string
  title: string
  children: React.ReactNode
}) {
  return (
    <section id={id} className="scroll-mt-24">
      <h2 className="font-display text-2xl font-semibold tracking-tight text-foreground">{title}</h2>
      <div className="mt-4 flex flex-col gap-4 text-[0.95rem] leading-relaxed text-muted-foreground">
        {children}
      </div>
    </section>
  )
}

function DefRow({ term, def }: { term: string; def: string }) {
  return (
    <div className="grid gap-1 border-l-2 border-border pl-4 sm:grid-cols-[140px_1fr] sm:gap-4 sm:border-l-0 sm:pl-0">
      <dt className="font-mono text-sm text-cyan">{term}</dt>
      <dd className="text-sm text-muted-foreground">{def}</dd>
    </div>
  )
}

function CodeBlock({ label, children }: { label: string; children: string }) {
  return (
    <GlassPanel className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <span className="font-mono text-xs text-cyan">{label}</span>
        <span className="flex gap-1.5">
          <span className="h-2 w-2 rounded-full bg-border-strong" />
          <span className="h-2 w-2 rounded-full bg-border-strong" />
          <span className="h-2 w-2 rounded-full bg-border-strong" />
        </span>
      </div>
      <pre className="overflow-x-auto px-4 py-4 font-mono text-xs leading-relaxed text-muted-foreground">
        <code>{children}</code>
      </pre>
    </GlassPanel>
  )
}

const detectionsPayload = `{
  "id": "DET-4471",
  "score": 74,
  "level": "HIGH",
  "pair": { "source": "A2", "target": "A3" },
  "window": { "start": 150, "end": 249 },
  "counterfactual": {
    "referencePrice": 99.80,
    "observedPrice": 104.10,
    "gapPct": 4.3
  },
  "signals": [
    { "id": "cf-gap",     "label": "Counterfactual Gap", "contribution": 34 },
    { "id": "sync-shock", "label": "Sync Under Shock",   "contribution": 40 }
  ]
}`

const signalPayload = `{
  "id": "sync-shock",
  "label": "Sync Under Shock",
  "contribution": 40,
  "description": "Agents realign quotes within the same tick following an exogenous price shock."
}`

const streamPayload = `// message
{
  "tick": 249,
  "level": "HIGH",
  "pair": { "source": "A2", "target": "A3" },
  "message": "Synchronized re-quote under shock"
}`
