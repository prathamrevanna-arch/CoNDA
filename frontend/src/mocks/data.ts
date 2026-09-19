import type { Agent, Case, PricePoint, Scenario, ShockEvent, Signal } from "@/types"

export const SCENARIOS: Scenario[] = [
  { id: "collusion-shock", name: "Collusion Under Shock", description: "Agents synchronize price recovery after liquidity shocks" },
  { id: "tacit-parallel", name: "Tacit Parallel Pricing", description: "Sustained supra-competitive markup without messaging" },
  { id: "competitive-baseline", name: "Competitive Baseline", description: "Independent agents, no coordination signal" },
  { id: "punish-deviation", name: "Deviation Punishment", description: "Group punishes an undercutting agent back into line" },
]

export const SHOCK_EVENTS: ShockEvent[] = [
  { tick: 14, label: "Liquidity shock" },
  { tick: 33, label: "Demand spike" },
  { tick: 48, label: "Order-book drain" },
]

const SHOCK_TICKS = SHOCK_EVENTS.map((s) => s.tick)

function mulberry32(seed: number) {
  let a = seed >>> 0
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export function generateSeries(count = 60, seed = 1): PricePoint[] {
  const rand = mulberry32(seed)
  const points: PricePoint[] = []
  let observed = 100
  let reference = 100
  for (let tick = 0; tick < count; tick++) {
    reference += Math.sin(tick / 6) * 0.35 + (rand() - 0.5) * 0.25
    const nearShock = SHOCK_TICKS.some((t) => tick >= t && tick <= t + 4)
    const markup = nearShock ? 3.4 : 1.6
    observed = reference + markup + Math.sin(tick / 4) * 0.4 + (rand() - 0.5) * 0.2
    points.push({
      tick,
      observed: Number(observed.toFixed(2)),
      reference: Number(reference.toFixed(2)),
      gap: Number((observed - reference).toFixed(2)),
    })
  }
  return points
}

export const SIGNALS: Signal[] = [
  {
    id: "counterfactual-gap",
    name: "Counterfactual Gap",
    contribution: 92,
    explanation: "Observed price sits 3.1% above the modeled competitive counterfactual.",
  },
  {
    id: "sync-under-shock",
    name: "Sync Under Shock",
    contribution: 81,
    explanation: "Agent quote adjustments align within 2 ticks after each shock event.",
  },
  {
    id: "deviation-punishment",
    name: "Deviation Punishment",
    contribution: 64,
    explanation: "Undercutting by AGT-04 was met with coordinated price drops, then recovery.",
  },
  {
    id: "economic-benefit",
    name: "Economic Benefit",
    contribution: 58,
    explanation: "Group PnL rises while consumer surplus falls versus the competitive baseline.",
  },
]

export const AGENTS: Agent[] = [
  { id: "AGT-01", lastPrice: 103.42, pnl: 12840, pairRisk: 88, status: "coordinating" },
  { id: "AGT-02", lastPrice: 103.39, pnl: 11705, pairRisk: 85, status: "coordinating" },
  { id: "AGT-03", lastPrice: 103.51, pnl: 9962, pairRisk: 71, status: "coordinating" },
  { id: "AGT-04", lastPrice: 101.88, pnl: -1420, pairRisk: 44, status: "watch" },
  { id: "AGT-05", lastPrice: 100.12, pnl: 640, pairRisk: 18, status: "independent" },
  { id: "AGT-06", lastPrice: 100.05, pnl: 305, pairRisk: 12, status: "independent" },
]

export const CASES: Case[] = [
  {
    id: "CASE-0x91",
    members: ["AGT-01", "AGT-02", "AGT-03"],
    risk: 87,
    status: "OPEN",
    evidenceHash: "0x7f3a9c2b48e1d6f05a9b2c7d3e8f14a6b9c0d2e5f7a1b3c4d6e8f9a0b1c2d3e4f",
    openedTx: "0x4b8e1f2a9c7d3e6f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f",
    challengeTx: null,
  },
  {
    id: "CASE-0x74",
    members: ["AGT-01", "AGT-03"],
    risk: 76,
    status: "CHALLENGED",
    evidenceHash: "0x2c5d8e1f4a7b0c3d6e9f2a5b8c1d4e7f0a3b6c9d2e5f8a1b4c7d0e3f6a9b2c5d",
    openedTx: "0x9a2b5c8d1e4f7a0b3c6d9e2f5a8b1c4d7e0f3a6b9c2d5e8f1a4b7c0d3e6f9a2b",
    challengeTx: "0x1d4e7f0a3b6c9d2e5f8a1b4c7d0e3f6a9b2c5d8e1f4a7b0c3d6e9f2a5b8c1d4e",
  },
  {
    id: "CASE-0x58",
    members: ["AGT-05", "AGT-06"],
    risk: 22,
    status: "CLEARED",
    evidenceHash: "0x6e9f2a5b8c1d4e7f0a3b6c9d2e5f8a1b4c7d0e3f6a9b2c5d8e1f4a7b0c3d6e9f",
    openedTx: "0x3f6a9b2c5d8e1f4a7b0c3d6e9f2a5b8c1d4e7f0a3b6c9d2e5f8a1b4c7d0e3f6a",
    challengeTx: "0x8c1d4e7f0a3b6c9d2e5f8a1b4c7d0e3f6a9b2c5d8e1f4a7b0c3d6e9f2a5b8c1d",
  },
  {
    id: "CASE-0x42",
    members: ["AGT-01", "AGT-02", "AGT-03", "AGT-04"],
    risk: 93,
    status: "ESCALATED",
    evidenceHash: "0x5b8c1d4e7f0a3b6c9d2e5f8a1b4c7d0e3f6a9b2c5d8e1f4a7b0c3d6e9f2a5b8c",
    openedTx: "0x0a3b6c9d2e5f8a1b4c7d0e3f6a9b2c5d8e1f4a7b0c3d6e9f2a5b8c1d4e7f0a3b",
    challengeTx: "0x7d0e3f6a9b2c5d8e1f4a7b0c3d6e9f2a5b8c1d4e7f0a3b6c9d2e5f8a1b4c7d0e",
  },
]
