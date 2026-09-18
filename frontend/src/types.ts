export type RiskBand = "low" | "medium" | "high"

export function riskBand(value: number): RiskBand {
  if (value >= 70) return "high"
  if (value >= 40) return "medium"
  return "low"
}

export const RISK_COLORS: Record<RiskBand, string> = {
  low: "var(--verified)",
  medium: "var(--warn)",
  high: "var(--risk)",
}

export const RISK_LABELS: Record<RiskBand, string> = {
  low: "Low risk",
  medium: "Elevated",
  high: "High risk",
}

export type Scenario = {
  id: string
  name: string
  description: string
}

export type PricePoint = {
  tick: number
  observed: number
  reference: number
  gap: number
}

export type ShockEvent = {
  tick: number
  label: string
}

export type Signal = {
  id: string
  name: string
  contribution: number
  explanation: string
}

export type AgentStatus = "coordinating" | "watch" | "independent"

export type Agent = {
  id: string
  lastPrice: number
  pnl: number
  pairRisk: number
  status: AgentStatus
}

export type CaseStatus = "OPEN" | "CHALLENGED" | "CLEARED" | "ESCALATED"

export type Case = {
  id: string
  members: string[]
  risk: number
  status: CaseStatus
  evidenceHash: string
  openedTx: string
  challengeTx: string | null
}

export function truncateHash(hash: string, lead = 6, tail = 4): string {
  if (hash.length <= lead + tail + 2) return hash
  return `${hash.slice(0, lead)}…${hash.slice(-tail)}`
}

export function formatUsd(value: number): string {
  const sign = value < 0 ? "-" : ""
  return `${sign}$${Math.abs(value).toLocaleString("en-US")}`
}
