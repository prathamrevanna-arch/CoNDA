import React from "react";
import { Bot, AlertTriangle, ShieldAlert } from "lucide-react";
import type { AgentLiveState } from "../hooks/useCoNDALive";
import type { RiskAssessment } from "../types/api";

interface AgentNetworkProps {
  agents: Record<string, AgentLiveState>;
  latestRisk: RiskAssessment | null;
}

export const AgentNetwork: React.FC<AgentNetworkProps> = ({ agents, latestRisk }) => {
  // Check if A2 and A3 are in the high-risk group
  const isA2A3Flagged =
    latestRisk?.verdict === "HIGH" &&
    latestRisk.group.includes("A2") &&
    latestRisk.group.includes("A3");

  const flaggedGroup = latestRisk?.group || [];
  const verdict = latestRisk?.verdict;

  return (
    <div className="bg-[var(--navy-card)] rounded-xl border border-[var(--navy-border)] p-5 shadow-lg relative overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-cyan-400" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--ink)]">
            Autonomous Agent Topology
          </h2>
        </div>
        <span className="text-[11px] font-mono text-[var(--ink-muted)]">
          4 Active Trading Agents (AMM Pool)
        </span>
      </div>

      {/* Coordination Warning Banner when High Risk Detected */}
      {isA2A3Flagged && (
        <div className="mb-5 px-4 py-3 rounded-lg bg-rose-950/50 border border-rose-600/50 flex items-center justify-between gap-3 text-xs animate-pulse shadow-lg shadow-rose-950/30">
          <div className="flex items-center gap-2.5">
            <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0" />
            <div>
              <p className="font-semibold text-rose-200">
                Potential Coordination Detected: Pair [A2 ↔ A3]
              </p>
              <p className="text-[11px] text-rose-300/80">
                High coordination risk (Score: {latestRisk?.risk_score}/100 in Window {latestRisk?.window_start}–{latestRisk?.window_end}). Synchronous quote adjustments and supracompetitive spread observed.
              </p>
            </div>
          </div>
          <span className="px-2.5 py-1 rounded bg-rose-900 text-rose-200 font-mono font-bold text-[11px] tracking-wider uppercase shrink-0 border border-rose-500/50">
            HIGH RISK
          </span>
        </div>
      )}

      {/* Agent Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 relative">
        {(["A1", "A2", "A3", "A4"] as const).map((agentId) => {
          const agent = agents[agentId];
          const isFlagged = flaggedGroup.includes(agentId);
          const isHighRisk = isFlagged && verdict === "HIGH";
          const isMediumRisk = isFlagged && verdict === "MEDIUM";

          const roleLabels: Record<string, string> = {
            A1: "Competitive Arbitrageur",
            A2: "Market Maker A (Explicit Cartel)",
            A3: "Market Maker B (Explicit Cartel)",
            A4: "Competitive Liquidity Provider",
          };

          return (
            <div
              key={agentId}
              className={`p-4 rounded-xl border transition-all duration-300 relative ${
                isHighRisk
                  ? "bg-rose-950/20 border-rose-500/80 shadow-lg shadow-rose-500/10 ring-1 ring-rose-500/40"
                  : isMediumRisk
                  ? "bg-amber-950/20 border-amber-500/60 shadow-lg shadow-amber-500/10"
                  : "bg-[var(--navy-elevated)] border-[var(--navy-border)] hover:border-slate-600"
              }`}
            >
              {/* Top Row: Agent ID and Status Badge */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className={`w-7 h-7 rounded-lg flex items-center justify-center font-mono font-bold text-xs ${
                      isHighRisk
                        ? "bg-rose-500/20 text-rose-300 border border-rose-500/50"
                        : "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                    }`}
                  >
                    {agentId}
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-[var(--ink)] block">
                      Agent {agentId}
                    </span>
                    <span className="text-[10px] text-[var(--ink-faint)] block truncate max-w-[120px]" title={roleLabels[agentId]}>
                      {roleLabels[agentId]}
                    </span>
                  </div>
                </div>

                <div
                  className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-medium ${
                    agent.lastEvent === "trade"
                      ? "bg-emerald-950 text-emerald-300 border border-emerald-700/50"
                      : agent.lastEvent === "quote"
                      ? "bg-cyan-950 text-cyan-300 border border-cyan-700/50"
                      : "bg-slate-900 text-slate-400 border border-slate-700/40"
                  }`}
                >
                  {agent.lastEvent}
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="space-y-1.5 text-xs font-mono mt-3 pt-3 border-t border-[var(--navy-border)]">
                <div className="flex items-center justify-between text-[var(--ink-muted)]">
                  <span className="text-[11px]">Side / Price:</span>
                  <span className="text-[var(--ink)] font-medium">
                    {agent.side ? (
                      <span
                        className={
                          agent.side === "bid" ? "text-emerald-400" : "text-amber-400"
                        }
                      >
                        {agent.side.toUpperCase()}{" "}
                        {agent.price !== null ? `$${agent.price.toFixed(2)}` : "—"}
                      </span>
                    ) : (
                      "—"
                    )}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[var(--ink-muted)]">
                  <span className="text-[11px]">Last Qty:</span>
                  <span className="text-[var(--ink)]">
                    {agent.quantity !== null && agent.quantity > 0
                      ? agent.quantity.toFixed(1)
                      : "—"}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[var(--ink-muted)]">
                  <span className="text-[11px]">Capital:</span>
                  <span className="text-[var(--ink)]">
                    {agent.capital !== null ? `$${Math.round(agent.capital).toLocaleString()}` : "$50,000"}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[var(--ink-muted)]">
                  <span className="text-[11px]">PnL:</span>
                  <span
                    className={
                      agent.pnl && agent.pnl > 0
                        ? "text-emerald-400"
                        : agent.pnl && agent.pnl < 0
                        ? "text-rose-400"
                        : "text-[var(--ink-muted)]"
                    }
                  >
                    {agent.pnl !== null ? `${agent.pnl >= 0 ? "+" : ""}$${agent.pnl.toFixed(2)}` : "$0.00"}
                  </span>
                </div>
              </div>

              {/* Status Indicator */}
              {isHighRisk && (
                <div className="mt-2 pt-2 border-t border-rose-500/20 text-[10px] font-mono text-rose-300 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3 text-rose-400" />
                  <span>High Coordination Risk</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Visual Connection Bar for Flagged Cartel Pair (A2 - A3) */}
      {isA2A3Flagged && (
        <div className="mt-4 p-3 rounded-lg bg-gradient-to-r from-rose-950/40 via-purple-950/50 to-rose-950/40 border border-rose-500/40 text-center">
          <div className="flex items-center justify-center gap-4 text-xs font-mono text-rose-300">
            <span className="font-bold px-2 py-0.5 rounded bg-rose-900/60 border border-rose-500/40">
              Agent A2
            </span>
            <span className="text-rose-400 flex items-center gap-1 font-bold animate-pulse">
              ◄─────── [ SYNCHRONOUS COORDINATION DETECTED: RISK 74 ] ───────►
            </span>
            <span className="font-bold px-2 py-0.5 rounded bg-rose-900/60 border border-rose-500/40">
              Agent A3
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
