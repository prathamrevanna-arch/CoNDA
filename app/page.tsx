"use client"

import { useEffect, useMemo, useState } from "react"
import { DashboardHeader } from "@/components/conda/dashboard-header"
import { Panel } from "@/components/conda/panel"
import { RiskGauge } from "@/components/conda/risk-gauge"
import { PriceChart } from "@/components/conda/price-chart"
import { SignalBreakdown } from "@/components/conda/signal-breakdown"
import { AgentTable } from "@/components/conda/agent-table"
import { CasePanel } from "@/components/conda/case-panel"
import { ScenarioSelector } from "@/components/conda/scenario-selector"
import {
  AGENTS,
  CASES,
  generateSeries,
  SCENARIOS,
  SHOCK_EVENTS,
  SIGNALS,
  type Case,
} from "@/lib/conda-data"

export default function Page() {
  const [scenarioId, setScenarioId] = useState(SCENARIOS[0].id)
  const [running, setRunning] = useState(true)
  const [runId, setRunId] = useState("RUN-8F42A1")
  const [series, setSeries] = useState(() => generateSeries())
  const [cases, setCases] = useState<Case[]>(CASES)

  const scenario = useMemo(() => SCENARIOS.find((s) => s.id === scenarioId)!, [scenarioId])

  // Simulate a live websocket feed by extending / rolling the price series.
  useEffect(() => {
    if (!running) return
    const id = setInterval(() => {
      setSeries((prev) => generateSeries(prev.length, Math.floor(Math.random() * 1e9)))
    }, 2600)
    return () => clearInterval(id)
  }, [running])

  function handleStart() {
    setSeries(generateSeries(60, Math.floor(Math.random() * 1e9)))
    setRunId(`RUN-${Math.random().toString(16).slice(2, 8).toUpperCase()}`)
    setRunning(true)
  }

  function handleSubmitChallenge(id: string) {
    setCases((prev) =>
      prev.map((c) =>
        c.id === id && c.status === "OPEN"
          ? {
              ...c,
              status: "CHALLENGED",
              challengeTx: "0x" + Math.random().toString(16).slice(2).padEnd(64, "0").slice(0, 64),
            }
          : c,
      ),
    )
  }

  return (
    <main className="min-h-screen bg-navy text-ink">
      <DashboardHeader scenarioName={scenario.name} connected={running} runId={runId} />

      <div className="mx-auto grid max-w-[1600px] grid-cols-12 gap-4 p-4">
        {/* Left column */}
        <div className="col-span-3 flex flex-col gap-4">
          <Panel title="Coordination Risk" subtitle="Aggregate detector score">
            <RiskGauge value={87} />
            <p className="mt-3 text-center text-xs leading-snug text-ink-muted">
              {"Coordination Risk: 87/100"} — evidence of coordinated behavior, contestable by challenge.
            </p>
          </Panel>

          <Panel title="Scenario" subtitle="Simulated DeFi market">
            <ScenarioSelector
              scenarios={SCENARIOS}
              selectedId={scenarioId}
              onSelect={setScenarioId}
              onStart={handleStart}
              running={running}
            />
          </Panel>
        </div>

        {/* Middle column */}
        <div className="col-span-6 flex flex-col gap-4">
          <Panel
            title="Observed vs Competitive Reference Price"
            subtitle="Mid-price divergence with shock-event markers"
          >
            <PriceChart data={series} shocks={SHOCK_EVENTS} />
          </Panel>

          <Panel title="Agent Activity" subtitle={`${AGENTS.length} agents in current run`}>
            <AgentTable agents={AGENTS} />
          </Panel>
        </div>

        {/* Right column */}
        <div className="col-span-3 flex flex-col gap-4">
          <Panel title="Signal Contribution" subtitle="Why the score is what it is">
            <SignalBreakdown signals={SIGNALS} />
          </Panel>

          <Panel title="Case Lifecycle" subtitle="Contestable evidence records">
            <CasePanel cases={cases} onSubmitChallenge={handleSubmitChallenge} />
          </Panel>
        </div>
      </div>
    </main>
  )
}
