import { Hero } from '@/components/home/hero'
import { PipelineSection } from '@/components/home/pipeline-section'
import { LivePreviewSection } from '@/components/home/live-preview-section'
import { PrinciplesSection } from '@/components/home/principles-section'
import { CtaSection } from '@/components/home/cta-section'

export default function HomePage() {
  return (
    <>
      <Hero />
      <PipelineSection />
      <LivePreviewSection />
      <PrinciplesSection />
      <CtaSection />
    </>
  )
}
