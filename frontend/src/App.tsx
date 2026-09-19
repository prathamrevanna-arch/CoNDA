import { Header } from "./components/Header";
import { AgentNetwork } from "./components/AgentNetwork";
import { MarketChart } from "./components/MarketChart";
import { DetectorPanel } from "./components/DetectorPanel";
import { CaseRegistry } from "./components/CaseRegistry";
import { BlockchainAudit } from "./components/BlockchainAudit";
import { useCoNDALive } from "./hooks/useCoNDALive";
import { AlertCircle } from "lucide-react";

export default function App() {
  const {
    health,
    isApiOnline,
    wsStatus,
    scenarios,
    selectedScenario,
    setSelectedScenario,
    runId,
    simulationState,
    currentTick,
    totalTicks,
    agents,
    priceHistory,
    recentEvents,
    pool,
    latestRisk,
    riskHistory,
    cases,
    errorMessage,
    startSimulation,
    submitChallenge,
  } = useCoNDALive();

  return (
    <div className="min-h-screen bg-[var(--navy)] text-[var(--ink)] flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Header */}
      <Header
        health={health}
        isApiOnline={isApiOnline}
        wsStatus={wsStatus}
        scenarios={scenarios}
        selectedScenario={selectedScenario}
        onSelectScenario={setSelectedScenario}
        onStartSimulation={() => startSimulation()}
        simulationState={simulationState}
        currentTick={currentTick}
        totalTicks={totalTicks}
        runId={runId}
      />

      {/* Error or Disconnected Alert Banner */}
      {!isApiOnline && (
        <div className="bg-rose-950/80 border-b border-rose-600/50 px-6 py-2.5 flex items-center justify-between text-xs font-mono text-rose-200">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>
              <strong>Backend Disconnected:</strong> Cannot reach FastAPI at http://127.0.0.1:8000. Ensure the backend service is running.
            </span>
          </div>
          <span className="text-[11px] text-rose-300">Retrying connection...</span>
        </div>
      )}

      {errorMessage && (
        <div className="bg-amber-950/80 border-b border-amber-600/50 px-6 py-2.5 flex items-center gap-2 text-xs font-mono text-amber-200">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Main Dashboard Workspace */}
      <main className="flex-1 p-5 md:p-6 space-y-6 max-w-[1720px] w-full mx-auto">
        {/* Top Grid: Left (Agents & Market) + Right (Detector) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column (8 cols): Autonomous Agents & Market AMM */}
          <div className="lg:col-span-7 xl:col-span-8 space-y-6">
            <AgentNetwork agents={agents} latestRisk={latestRisk} />
            <MarketChart
              priceHistory={priceHistory}
              pool={pool}
              recentEvents={recentEvents}
            />
          </div>

          {/* Right Column (5 cols): Detector Engine & Cryptographic Proof */}
          <div className="lg:col-span-5 xl:col-span-4">
            <div className="sticky top-24">
              <DetectorPanel latestRisk={latestRisk} riskHistory={riskHistory} />
            </div>
          </div>
        </div>

        {/* Bottom Grid: Cases & Blockchain Audit Trail */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7 xl:col-span-8">
            <CaseRegistry
              cases={cases}
              onSubmitChallenge={submitChallenge}
            />
          </div>

          <div className="lg:col-span-5 xl:col-span-4">
            <BlockchainAudit health={health} cases={cases} />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--navy-border)] px-6 py-4 text-xs font-mono text-[var(--ink-faint)] flex flex-col sm:flex-row items-center justify-between gap-2 bg-[var(--navy-card)]">
        <div>
          <span>CoNDA Protocol — Autonomous Agent Collusion Detection & Audit Layer</span>
        </div>
        <div className="flex items-center gap-4 text-[11px]">
          <span>FastAPI / SQLite</span>
          <span>•</span>
          <span>Real M2 Detector</span>
          <span>•</span>
          <span>Local Anvil Ethereum-Compatible</span>
        </div>
      </footer>
    </div>
  );
}
