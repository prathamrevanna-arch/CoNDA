import React from "react";
import {
  Activity,
  Play,
  CheckCircle2,
  AlertCircle,
  Radio,
  Cpu,
  ShieldCheck,
  Blocks,
  Loader2,
} from "lucide-react";
import type { HealthResponse, ScenarioItem } from "../types/api";

interface HeaderProps {
  health: HealthResponse | null;
  isApiOnline: boolean;
  wsStatus: "connected" | "connecting" | "disconnected";
  scenarios: ScenarioItem[];
  selectedScenario: string;
  onSelectScenario: (scenario: string) => void;
  onStartSimulation: () => void;
  simulationState: "idle" | "running" | "completed" | "error";
  currentTick: number;
  totalTicks: number;
  runId: string | null;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  isApiOnline,
  wsStatus,
  scenarios,
  selectedScenario,
  onSelectScenario,
  onStartSimulation,
  simulationState,
  currentTick,
  totalTicks,
  runId,
}) => {
  const isRunning = simulationState === "running";
  const progressPct = totalTicks > 0 ? Math.min(100, Math.round((currentTick / totalTicks) * 100)) : 0;

  return (
    <header className="border-b border-[var(--navy-border)] bg-[var(--navy-card)]/80 backdrop-blur-md px-6 py-4 sticky top-0 z-30">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        {/* Brand & Subtitle */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500/20 via-violet-500/30 to-rose-500/20 border border-cyan-500/40 flex items-center justify-center shadow-lg shadow-cyan-500/10">
            <ShieldCheck className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                CoNDA
              </h1>
              <span className="text-[11px] font-mono uppercase px-2 py-0.5 rounded-full bg-cyan-950/60 text-cyan-300 border border-cyan-700/50 font-semibold tracking-wider">
                Autonomous Collusion Detection
              </span>
            </div>
            <p className="text-xs text-[var(--ink-muted)]">
              Real-time cryptographic audit & coordination detection layer for autonomous DeFi agents
            </p>
          </div>
        </div>

        {/* System Health Indicators */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {/* API Health */}
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border ${
              isApiOnline
                ? "bg-emerald-950/40 text-emerald-300 border-emerald-700/40"
                : "bg-rose-950/40 text-rose-300 border-rose-700/40"
            }`}
            title="FastAPI Backend Health"
          >
            <Activity className="w-3.5 h-3.5" />
            <span className="font-mono">API: {isApiOnline ? "ONLINE" : "OFFLINE"}</span>
          </div>

          {/* Detector Mode */}
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border ${
              health?.detector === "real"
                ? "bg-violet-950/40 text-violet-300 border-violet-700/40"
                : "bg-amber-950/40 text-amber-300 border-amber-700/40"
            }`}
            title="M2 Detector Engine Status"
          >
            <Cpu className="w-3.5 h-3.5" />
            <span className="font-mono">
              DETECTOR: {health?.detector === "real" ? "REAL M2" : "STUB"}
            </span>
          </div>

          {/* Blockchain Indicator */}
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border ${
              health?.chain
                ? "bg-cyan-950/40 text-cyan-300 border-cyan-700/40"
                : "bg-slate-900 text-slate-400 border-slate-700/40"
            }`}
            title="Local Anvil Ethereum-compatible blockchain status"
          >
            <Blocks className="w-3.5 h-3.5" />
            <span className="font-mono">
              CHAIN: {health?.chain ? "ANVIL ACTIVE" : "ANVIL STANDBY"}
            </span>
          </div>

          {/* WebSocket Status */}
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border ${
              wsStatus === "connected"
                ? "bg-emerald-950/40 text-emerald-300 border-emerald-700/40"
                : wsStatus === "connecting"
                ? "bg-amber-950/40 text-amber-300 border-amber-700/40"
                : "bg-rose-950/40 text-rose-300 border-rose-700/40"
            }`}
            title="WebSocket Live Stream (/ws/live)"
          >
            <Radio
              className={`w-3.5 h-3.5 ${
                wsStatus === "connected" ? "animate-pulse text-emerald-400" : ""
              }`}
            />
            <span className="font-mono uppercase">WS: {wsStatus}</span>
          </div>
        </div>

        {/* Simulation Controls */}
        <div className="flex items-center gap-3">
          <div className="flex flex-col">
            <label className="text-[10px] uppercase font-mono tracking-wider text-[var(--ink-faint)] mb-1">
              Select Scenario
            </label>
            <select
              value={selectedScenario}
              onChange={(e) => onSelectScenario(e.target.value)}
              disabled={isRunning}
              className="bg-[var(--navy-elevated)] text-[var(--ink)] border border-[var(--navy-border)] rounded-lg px-3 py-1.5 text-xs font-mono focus:outline-none focus:border-cyan-500 disabled:opacity-50 transition cursor-pointer"
            >
              {scenarios.length === 0 ? (
                <option value="cartel_vs_competitive">cartel_vs_competitive</option>
              ) : (
                scenarios.map((sc) => (
                  <option key={sc.id} value={sc.id}>
                    {sc.label || sc.id}
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="flex flex-col justify-end">
            <span className="text-[10px] uppercase font-mono tracking-wider text-transparent mb-1 select-none">
              action
            </span>
            <button
              onClick={onStartSimulation}
              disabled={isRunning || !isApiOnline}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-xs tracking-wide transition shadow-lg ${
                isRunning
                  ? "bg-cyan-900/50 text-cyan-300 border border-cyan-600/50 cursor-not-allowed"
                  : "bg-gradient-to-r from-cyan-600 to-violet-600 hover:from-cyan-500 hover:to-violet-500 text-white shadow-cyan-500/20 hover:shadow-cyan-500/30 cursor-pointer active:scale-95"
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {isRunning ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Simulating...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Launch Simulation</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Live Run Progress Bar */}
      {isRunning && (
        <div className="mt-3 pt-3 border-t border-[var(--navy-border)]">
          <div className="flex items-center justify-between text-xs font-mono text-[var(--ink-muted)] mb-1">
            <div className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              <span>
                RUNNING SIMULATION: <strong className="text-[var(--ink)]">{selectedScenario}</strong>
              </span>
              {runId && (
                <span className="text-[var(--ink-faint)]">
                  (ID: {runId.slice(0, 8)}...)
                </span>
              )}
            </div>
            <span>
              Timestep {currentTick} / {totalTicks} ({progressPct}%)
            </span>
          </div>
          <div className="w-full bg-[var(--navy-elevated)] h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-gradient-to-r from-cyan-500 via-violet-500 to-rose-500 h-full rounded-full transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      {simulationState === "completed" && (
        <div className="mt-2 text-xs font-mono text-emerald-400 flex items-center gap-1.5">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Simulation completed successfully ({totalTicks} ticks processed).</span>
        </div>
      )}

      {simulationState === "error" && (
        <div className="mt-2 text-xs font-mono text-rose-400 flex items-center gap-1.5">
          <AlertCircle className="w-3.5 h-3.5" />
          <span>Simulation encountered an error. Check backend connection.</span>
        </div>
      )}
    </header>
  );
};
