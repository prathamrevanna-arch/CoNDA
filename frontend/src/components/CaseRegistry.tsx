import React, { useState } from "react";
import {
  FolderLock,
  ArrowRight,
  Blocks,
  AlertCircle,
  ChevronRight,
} from "lucide-react";
import type { CaseItem, ChallengeRequest, ChallengeResponse } from "../types/api";
import { ChallengeModal } from "./ChallengeModal";

interface CaseRegistryProps {
  cases: CaseItem[];
  onSubmitChallenge: (caseId: string, payload: ChallengeRequest) => Promise<ChallengeResponse>;
}

export const CaseRegistry: React.FC<CaseRegistryProps> = ({
  cases,
  onSubmitChallenge,
}) => {
  const [selectedCase, setSelectedCase] = useState<CaseItem | null>(null);

  const getStatusBadge = (status: CaseItem["status"]) => {
    switch (status) {
      case "OPEN":
        return "bg-amber-950/60 text-amber-300 border-amber-500/50";
      case "CHALLENGED":
        return "bg-cyan-950/60 text-cyan-300 border-cyan-500/50";
      case "CLEARED":
        return "bg-emerald-950/60 text-emerald-300 border-emerald-500/50";
      case "ESCALATED":
        return "bg-rose-950/60 text-rose-300 border-rose-500/50";
      default:
        return "bg-slate-900 text-slate-400 border-slate-700/50";
    }
  };

  return (
    <div className="bg-[var(--navy-card)] rounded-xl border border-[var(--navy-border)] p-5 shadow-lg flex flex-col gap-4">
      {/* Panel Header */}
      <div className="flex items-center justify-between pb-3 border-b border-[var(--navy-border)]">
        <div className="flex items-center gap-2">
          <FolderLock className="w-5 h-5 text-amber-400" />
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--ink)]">
              Case Registry & On-Chain Audit Trail
            </h2>
            <p className="text-[11px] text-[var(--ink-muted)]">
              Formal Case Lifecycle & Cryptographic Challenge Layer
            </p>
          </div>
        </div>

        <span className="text-xs font-mono px-2.5 py-0.5 rounded bg-[var(--navy-elevated)] border border-[var(--navy-border)] text-[var(--ink-muted)]">
          Total Cases: {cases.length}
        </span>
      </div>

      {/* Case List or Empty State */}
      {cases.length === 0 ? (
        <div className="py-8 px-4 flex flex-col items-center justify-center text-center text-xs font-mono text-[var(--ink-faint)] border border-dashed border-[var(--navy-border)] rounded-lg">
          <AlertCircle className="w-6 h-6 mb-2 text-[var(--ink-faint)]" />
          <span className="font-semibold text-[var(--ink-muted)]">
            No Active Cases Open
          </span>
          <p className="text-[11px] mt-1 text-[var(--ink-faint)] max-w-md">
            The reference scenario generates a single high-risk coordination window (Score 74 at t=150–249). The case opening rule strictly requires <strong>3 consecutive HIGH windows</strong> for a pair to automatically trigger a case.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {cases.map((c) => (
            <div
              key={c.case_id}
              className="p-4 rounded-xl bg-[var(--navy-elevated)] border border-[var(--navy-border)] flex flex-col md:flex-row md:items-center justify-between gap-4 transition hover:border-slate-700"
            >
              {/* Left Details */}
              <div className="space-y-1.5 font-mono text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-[var(--ink)] text-sm">
                    Case #{c.case_id.slice(0, 8)}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${getStatusBadge(
                      c.status
                    )}`}
                  >
                    {c.status}
                  </span>
                  <span className="text-rose-400 font-bold">
                    Risk: {c.risk_score}/100
                  </span>
                </div>

                <div className="text-[11px] text-[var(--ink-muted)] flex flex-wrap items-center gap-x-4 gap-y-1">
                  <span>
                    Flagged Group:{" "}
                    <strong className="text-[var(--ink)]">
                      [{c.group.join(", ")}]
                    </strong>
                  </span>
                  <span>
                    Opened at: <strong>t={c.opened_at_tick}</strong>
                  </span>
                  {c.run_id && (
                    <span className="text-[var(--ink-faint)]">
                      Run: {c.run_id.slice(0, 8)}...
                    </span>
                  )}
                </div>

                {/* Blockchain Tx Hashes */}
                <div className="text-[10px] text-[var(--ink-faint)] space-y-0.5 pt-1">
                  {c.opened_tx && (
                    <div className="flex items-center gap-1.5 truncate max-w-md">
                      <Blocks className="w-3 h-3 text-cyan-400 shrink-0" />
                      <span>Open Tx:</span>
                      <span className="text-cyan-300 select-all truncate">
                        {c.opened_tx}
                      </span>
                    </div>
                  )}
                  {c.challenge_tx && (
                    <div className="flex items-center gap-1.5 truncate max-w-md">
                      <Blocks className="w-3 h-3 text-amber-400 shrink-0" />
                      <span>Challenge Tx:</span>
                      <span className="text-amber-300 select-all truncate">
                        {c.challenge_tx}
                      </span>
                    </div>
                  )}
                  {c.resolved_tx && (
                    <div className="flex items-center gap-1.5 truncate max-w-md">
                      <Blocks className="w-3 h-3 text-emerald-400 shrink-0" />
                      <span>Resolved Tx:</span>
                      <span className="text-emerald-300 select-all truncate">
                        {c.resolved_tx}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Right: Lifecycle & Action */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                {/* Visual Lifecycle Stepper */}
                <div className="flex items-center gap-1.5 text-[10px] font-mono bg-black/30 px-3 py-1.5 rounded-lg border border-slate-800">
                  <span
                    className={
                      c.status === "OPEN"
                        ? "text-amber-400 font-bold"
                        : "text-slate-500"
                    }
                  >
                    OPEN
                  </span>
                  <ArrowRight className="w-3 h-3 text-slate-600" />
                  <span
                    className={
                      c.status === "CHALLENGED"
                        ? "text-cyan-400 font-bold"
                        : "text-slate-500"
                    }
                  >
                    CHALLENGED
                  </span>
                  <ArrowRight className="w-3 h-3 text-slate-600" />
                  <span
                    className={
                      c.status === "CLEARED"
                        ? "text-emerald-400 font-bold"
                        : c.status === "ESCALATED"
                        ? "text-rose-400 font-bold"
                        : "text-slate-500"
                    }
                  >
                    {c.status === "CLEARED"
                      ? "CLEARED"
                      : c.status === "ESCALATED"
                      ? "ESCALATED"
                      : "RESOLVED"}
                  </span>
                </div>

                {/* Challenge Action Button */}
                <button
                  onClick={() => setSelectedCase(c)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-700/50 text-xs font-mono transition cursor-pointer active:scale-95 shadow"
                >
                  <span>Challenge Policy</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Challenge Modal */}
      {selectedCase && (
        <ChallengeModal
          caseItem={selectedCase}
          isOpen={Boolean(selectedCase)}
          onClose={() => setSelectedCase(null)}
          onSubmitChallenge={onSubmitChallenge}
        />
      )}
    </div>
  );
};
