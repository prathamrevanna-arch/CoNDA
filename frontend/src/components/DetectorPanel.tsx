import React, { useState } from "react";
import {
  ShieldAlert,
  Sliders,
  Scale,
  Hash,
  Clock,
  Copy,
  Check,
  Info,
} from "lucide-react";
import type { RiskAssessment } from "../types/api";

interface DetectorPanelProps {
  latestRisk: RiskAssessment | null;
  riskHistory: RiskAssessment[];
}

export const DetectorPanel: React.FC<DetectorPanelProps> = ({
  latestRisk,
  riskHistory,
}) => {
  const [copied, setCopied] = useState(false);

  const copyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isHigh = latestRisk?.verdict === "HIGH";
  const isMedium = latestRisk?.verdict === "MEDIUM";

  const scoreColor = isHigh
    ? "text-rose-400"
    : isMedium
    ? "text-amber-400"
    : "text-emerald-400";

  const badgeBg = isHigh
    ? "bg-rose-950/60 text-rose-300 border-rose-500/50"
    : isMedium
    ? "bg-amber-950/60 text-amber-300 border-amber-500/50"
    : "bg-emerald-950/60 text-emerald-300 border-emerald-500/50";

  return (
    <div className="bg-[var(--navy-card)] rounded-xl border border-[var(--navy-border)] p-5 shadow-lg flex flex-col gap-5">
      {/* Panel Header */}
      <div className="flex items-center justify-between pb-3 border-b border-[var(--navy-border)]">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-rose-400" />
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--ink)]">
              Real-time Detector Engine
            </h2>
            <p className="text-[11px] text-[var(--ink-muted)]">
              M2 Graded Coordination Evaluator ({riskHistory.length} windows scored)
            </p>
          </div>
        </div>

        {latestRisk && (
          <span className="text-[10px] font-mono text-[var(--ink-faint)] flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>{latestRisk.computed_ms.toFixed(1)}ms latency</span>
          </span>
        )}
      </div>

      {!latestRisk ? (
        <div className="py-12 flex flex-col items-center justify-center text-center text-xs font-mono text-[var(--ink-faint)] border border-dashed border-[var(--navy-border)] rounded-lg">
          <Sliders className="w-8 h-8 mb-2 text-[var(--ink-faint)] animate-pulse" />
          <span>Awaiting detector window evaluations...</span>
          <p className="text-[10px] mt-1 text-[var(--ink-muted)] max-w-xs">
            The detector computes rolling counterfactual gap and shock synchronization over market windows.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Main Score & Verdict Display */}
          <div className="p-4 rounded-xl bg-[var(--navy-elevated)] border border-[var(--navy-border)] flex items-center justify-between">
            <div>
              <span className="text-[10px] uppercase font-mono tracking-wider text-[var(--ink-faint)] block mb-1">
                Evaluated Agent Group
              </span>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold font-mono text-[var(--ink)]">
                  [{latestRisk.group.join(" ↔ ")}]
                </span>
                <span className="text-xs font-mono text-[var(--ink-muted)]">
                  Window: t={latestRisk.window_start}–{latestRisk.window_end}
                </span>
              </div>
            </div>

            <div className="text-right">
              <span className="text-[10px] uppercase font-mono tracking-wider text-[var(--ink-faint)] block mb-1">
                Coordination Risk
              </span>
              <div className="flex items-center gap-2 justify-end">
                <span className={`text-3xl font-extrabold font-mono ${scoreColor}`}>
                  {latestRisk.risk_score}
                </span>
                <span className="text-xs font-mono text-[var(--ink-faint)]">/100</span>
                <span className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold tracking-wider uppercase border ${badgeBg}`}>
                  {latestRisk.verdict}
                </span>
              </div>
            </div>
          </div>

          {/* Signal Attribution Breakdown */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono font-semibold uppercase tracking-wider text-[var(--ink)] flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                <span>Signal Attribution</span>
              </span>
              <span className="text-[10px] font-mono text-[var(--ink-faint)]">
                Base weights: Gap 60% / Sync 40%
              </span>
            </div>

            <div className="grid grid-cols-1 gap-2.5">
              {/* Counterfactual Gap Signal */}
              {latestRisk.signals.counterfactual_gap && (
                <div className="p-3 rounded-lg bg-[var(--navy-elevated)] border border-[var(--navy-border)] text-xs">
                  <div className="flex items-center justify-between mb-1.5 font-mono">
                    <span className="font-semibold text-cyan-300">
                      1. Counterfactual Gap
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-[var(--ink-muted)] text-[11px]">
                        value: {latestRisk.signals.counterfactual_gap.value.toFixed(3)}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-700/50 font-bold">
                        +{latestRisk.signals.counterfactual_gap.contribution} pts
                      </span>
                    </div>
                  </div>
                  <p className="text-[11px] text-[var(--ink-muted)] leading-relaxed">
                    {latestRisk.signals.counterfactual_gap.explanation}
                  </p>
                </div>
              )}

              {/* Sync Under Shock Signal */}
              {latestRisk.signals.sync_under_shock && (
                <div className="p-3 rounded-lg bg-[var(--navy-elevated)] border border-[var(--navy-border)] text-xs">
                  <div className="flex items-center justify-between mb-1.5 font-mono">
                    <span className="font-semibold text-violet-300">
                      2. Sync Under Shock
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-[var(--ink-muted)] text-[11px]">
                        value: {latestRisk.signals.sync_under_shock.value.toFixed(4)}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-violet-950 text-violet-300 border border-violet-700/50 font-bold">
                        +{latestRisk.signals.sync_under_shock.contribution} pts
                      </span>
                    </div>
                  </div>
                  <p className="text-[11px] text-[var(--ink-muted)] leading-relaxed">
                    {latestRisk.signals.sync_under_shock.explanation}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Counterfactual Reference Comparison Card */}
          <div className="p-3.5 rounded-lg bg-[var(--navy-elevated)] border border-[var(--navy-border)]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono font-semibold uppercase tracking-wider text-[var(--ink)] flex items-center gap-1.5">
                <Scale className="w-3.5 h-3.5 text-amber-400" />
                <span>Counterfactual AMM Pricing Model</span>
              </span>
              <span className="text-[10px] font-mono text-[var(--ink-faint)]">
                Synthetic Competitive Reference
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-xs font-mono text-center">
              <div className="p-2 rounded bg-[var(--navy-card)] border border-[var(--navy-border)]">
                <span className="text-[10px] text-[var(--ink-faint)] block">
                  Reference Price
                </span>
                <span className="text-emerald-400 font-bold text-sm block mt-0.5">
                  ${latestRisk.counterfactual.reference_price.toFixed(2)}
                </span>
              </div>
              <div className="p-2 rounded bg-[var(--navy-card)] border border-[var(--navy-border)]">
                <span className="text-[10px] text-[var(--ink-faint)] block">
                  Observed Price
                </span>
                <span className="text-rose-400 font-bold text-sm block mt-0.5">
                  ${latestRisk.counterfactual.observed_price.toFixed(2)}
                </span>
              </div>
              <div className="p-2 rounded bg-[var(--navy-card)] border border-[var(--navy-border)]">
                <span className="text-[10px] text-[var(--ink-faint)] block">
                  Markup Gap %
                </span>
                <span className="text-amber-400 font-bold text-sm block mt-0.5">
                  +{latestRisk.counterfactual.gap_pct.toFixed(2)}%
                </span>
              </div>
            </div>
          </div>

          {/* Cryptographic Evidence Hash */}
          <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
            <div className="flex items-center justify-between mb-1 text-[11px] font-mono">
              <span className="text-[var(--ink-muted)] flex items-center gap-1">
                <Hash className="w-3.5 h-3.5 text-cyan-400" />
                <span>Cryptographic Evidence Hash</span>
              </span>
              <button
                onClick={() => copyHash(latestRisk.evidence_hash)}
                className="flex items-center gap-1 text-[10px] text-cyan-400 hover:text-cyan-300 transition"
              >
                {copied ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-400" />
                    <span className="text-emerald-400">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy Hash</span>
                  </>
                )}
              </button>
            </div>
            <p className="font-mono text-[10px] text-slate-300 break-all select-all bg-black/40 p-1.5 rounded border border-slate-900">
              {latestRisk.evidence_hash}
            </p>
          </div>

          {/* Legal / Non-accusatory Disclaimer note */}
          <div className="flex items-start gap-2 p-2.5 rounded-lg bg-slate-900/40 border border-slate-800/60 text-[10px] text-[var(--ink-faint)]">
            <Info className="w-4 h-4 shrink-0 text-cyan-500/70 mt-0.5" />
            <p>
              Risk scores reflect statistical probability of tacit coordination based on AMM counterfactual pricing and reaction synchrony. High scores represent potential coordination risk rather than proof of collusion.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
