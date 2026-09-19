/**
 * Placeholder data for the CoNDA frontend concept.
 *
 * This module is the single seam between the UI and a future backend.
 * Every export is a plain, serializable value shaped like a REST payload,
 * so each can later be swapped for a `fetch()` call or a WebSocket stream
 * without touching component code. Nothing here performs network I/O.
 */

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH'

export type AgentId = 'A1' | 'A2' | 'A3' | 'A4'

export interface AgentPair {
  source: AgentId
  target: AgentId
}

export interface EvidenceSignal {
  id: string
  label: string
  contribution: number
  description: string
}

export interface DetectionResult {
  id: string
  score: number
  level: RiskLevel
  pair: AgentPair
  window: { start: number; end: number }
  signals: EvidenceSignal[]
  counterfactual: {
    referencePrice: number
    observedPrice: number
    gapPct: number
  }
}

export const riskColor: Record<RiskLevel, string> = {
  LOW: 'var(--risk-low)',
  MEDIUM: 'var(--risk-med)',
  HIGH: 'var(--risk-high)',
}

export function levelForScore(score: number): RiskLevel {
  if (score >= 66) return 'HIGH'
  if (score >= 33) return 'MEDIUM'
  return 'LOW'
}

/** Featured live-preview detection shown on the home page. */
export const featuredDetection: DetectionResult = {
  id: 'DET-4471',
  score: 74,
  level: 'HIGH',
  pair: { source: 'A2', target: 'A3' },
  window: { start: 150, end: 249 },
  signals: [
    {
      id: 'cf-gap',
      label: 'Counterfactual Gap',
      contribution: 34,
      description:
        'Observed joint behaviour diverges from the competitive counterfactual baseline.',
    },
    {
      id: 'sync-shock',
      label: 'Sync Under Shock',
      contribution: 40,
      description:
        'Agents realign quotes within the same tick following an exogenous price shock.',
    },
  ],
  counterfactual: {
    referencePrice: 99.8,
    observedPrice: 104.1,
    gapPct: 4.3,
  },
}

/** The pipeline stages, in order. Drives the storytelling section. */
export const pipelineStages = [
  {
    id: 'ingest',
    label: 'Market Data',
    detail: 'Order flow, quotes and fills streamed per agent.',
  },
  {
    id: 'window',
    label: 'Windowing',
    detail: 'Behaviour segmented into overlapping analysis windows.',
  },
  {
    id: 'counterfactual',
    label: 'Competitive Counterfactual',
    detail: 'Simulate how rational competitors would have acted.',
  },
  {
    id: 'signals',
    label: 'Detection Signals',
    detail: 'Extract divergence, synchrony and response signatures.',
  },
  {
    id: 'evidence',
    label: 'Evidence',
    detail: 'Attribute weighted contributions to each signal.',
  },
  {
    id: 'risk',
    label: 'Coordination Risk',
    detail: 'Adjudicate a calibrated coordination risk score.',
  },
] as const

/** Rows for the Explorer table. */
export const detectionFeed: DetectionResult[] = [
  featuredDetection,
  {
    id: 'DET-4468',
    score: 58,
    level: 'MEDIUM',
    pair: { source: 'A1', target: 'A4' },
    window: { start: 90, end: 189 },
    signals: [
      { id: 'cf-gap', label: 'Counterfactual Gap', contribution: 26, description: '' },
      { id: 'lead-lag', label: 'Lead / Lag', contribution: 18, description: '' },
    ],
    counterfactual: { referencePrice: 100.4, observedPrice: 102.1, gapPct: 1.7 },
  },
  {
    id: 'DET-4463',
    score: 81,
    level: 'HIGH',
    pair: { source: 'A2', target: 'A4' },
    window: { start: 210, end: 309 },
    signals: [
      { id: 'sync-shock', label: 'Sync Under Shock', contribution: 44, description: '' },
      { id: 'cf-gap', label: 'Counterfactual Gap', contribution: 31, description: '' },
    ],
    counterfactual: { referencePrice: 98.2, observedPrice: 103.9, gapPct: 5.8 },
  },
  {
    id: 'DET-4459',
    score: 22,
    level: 'LOW',
    pair: { source: 'A1', target: 'A3' },
    window: { start: 40, end: 139 },
    signals: [
      { id: 'cf-gap', label: 'Counterfactual Gap', contribution: 9, description: '' },
      { id: 'lead-lag', label: 'Lead / Lag', contribution: 7, description: '' },
    ],
    counterfactual: { referencePrice: 101.1, observedPrice: 101.4, gapPct: 0.3 },
  },
  {
    id: 'DET-4455',
    score: 47,
    level: 'MEDIUM',
    pair: { source: 'A3', target: 'A4' },
    window: { start: 300, end: 399 },
    signals: [
      { id: 'lead-lag', label: 'Lead / Lag', contribution: 24, description: '' },
      { id: 'cf-gap', label: 'Counterfactual Gap', contribution: 15, description: '' },
    ],
    counterfactual: { referencePrice: 99.5, observedPrice: 101.0, gapPct: 1.5 },
  },
  {
    id: 'DET-4451',
    score: 12,
    level: 'LOW',
    pair: { source: 'A1', target: 'A2' },
    window: { start: 0, end: 99 },
    signals: [{ id: 'cf-gap', label: 'Counterfactual Gap', contribution: 5, description: '' }],
    counterfactual: { referencePrice: 100.0, observedPrice: 100.1, gapPct: 0.1 },
  },
]

/** Counterfactual vs observed price series for the chart. */
export interface PricePoint {
  t: number
  reference: number
  observed: number
}

export const counterfactualSeries: PricePoint[] = Array.from({ length: 40 }, (_, i) => {
  const t = 150 + i
  const base = 99 + Math.sin(i / 6) * 1.4
  const shock = i > 18 ? Math.min((i - 18) * 0.42, 5.2) : 0
  const reference = base + Math.sin(i / 3) * 0.3
  const observed = base + shock + Math.sin(i / 2.4) * 0.35
  return {
    t,
    reference: Number(reference.toFixed(2)),
    observed: Number(observed.toFixed(2)),
  }
})

/** Live timeline events (would arrive over WebSocket). */
export interface TimelineEvent {
  id: string
  tick: number
  level: RiskLevel
  pair: AgentPair
  message: string
}

export const timelineEvents: TimelineEvent[] = [
  { id: 'e1', tick: 249, level: 'HIGH', pair: { source: 'A2', target: 'A3' }, message: 'Synchronized re-quote under shock' },
  { id: 'e2', tick: 233, level: 'MEDIUM', pair: { source: 'A1', target: 'A4' }, message: 'Counterfactual gap widening' },
  { id: 'e3', tick: 221, level: 'LOW', pair: { source: 'A1', target: 'A3' }, message: 'Behaviour within competitive band' },
  { id: 'e4', tick: 205, level: 'HIGH', pair: { source: 'A2', target: 'A4' }, message: 'Lead/lag lock detected' },
  { id: 'e5', tick: 188, level: 'MEDIUM', pair: { source: 'A3', target: 'A4' }, message: 'Partial quote mirroring' },
]

export const agents: { id: AgentId; label: string }[] = [
  { id: 'A1', label: 'Agent A1' },
  { id: 'A2', label: 'Agent A2' },
  { id: 'A3', label: 'Agent A3' },
  { id: 'A4', label: 'Agent A4' },
]
