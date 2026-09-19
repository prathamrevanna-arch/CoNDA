import React, { useState } from "react";
import {
  X,
  ShieldCheck,
  Loader2,
  FileCheck2,
  FileX2,
  CheckCircle2,
  AlertTriangle,
  Info,
} from "lucide-react";
import type { CaseItem, ChallengeRequest, ChallengeResponse } from "../types/api";

interface ChallengeModalProps {
  caseItem: CaseItem;
  isOpen: boolean;
  onClose: () => void;
  onSubmitChallenge: (caseId: string, payload: ChallengeRequest) => Promise<ChallengeResponse>;
}

export const ChallengeModal: React.FC<ChallengeModalProps> = ({
  caseItem,
  isOpen,
  onClose,
  onSubmitChallenge,
}) => {
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<ChallengeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  // Pre-configured valid compliance payload matching backend/challenge.py + test_step4.py
  const handleValidChallenge = async () => {
    setSubmitting(true);
    setError(null);
    setResult(null);

    // Valid payload for Agent A2 with verified ECDSA signature and policy commitment
    const payload: ChallengeRequest = {
      agent_id: "A2",
      policy_commitment: "0xb65c188cb8eac7fc49cda6435e2d5df558efe5cd340727a673dd3287e38d926f",
      policy_json: { agent: "A2", strategy: "conservative_mm", spread_bps: 20 },
      signature:
        "0x1108d804a0fa65e98418cd5a3cb9e62664848a74a286ee826d9f775c6a7171fc1bbf5b72c1a119d28312194b2cb2e364f6e0a63a159803199e0597a7a477e9b11c",
      flagged_action: { t: 32, action: "quote", bid: 99.5, ask: 100.5 },
      trace: { inputs: { t: 32, action: "quote" }, output: "order_placed" },
    };

    try {
      const res = await onSubmitChallenge(caseItem.case_id, payload);
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Challenge submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  // Invalid/tampered payload to demonstrate ESCALATED verdict
  const handleInvalidChallenge = async () => {
    setSubmitting(true);
    setError(null);
    setResult(null);

    const payload: ChallengeRequest = {
      agent_id: "A2",
      policy_commitment: "0x0000000000000000000000000000000000000000000000000000000000000000",
      policy_json: { agent: "A2", tampered: true },
      signature: "0xdeadbeef00000000000000000000000000000000000000000000000000000000",
      flagged_action: { action: "unauthorized_trade" },
    };

    try {
      const res = await onSubmitChallenge(caseItem.case_id, payload);
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Challenge submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-[var(--navy-card)] border border-[var(--navy-border)] rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-[var(--navy-border)] flex items-center justify-between bg-[var(--navy-elevated)]">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="w-5 h-5 text-cyan-400" />
            <div>
              <h3 className="text-sm font-bold text-[var(--ink)]">
                Cryptographic Policy Challenge
              </h3>
              <p className="text-[11px] font-mono text-[var(--ink-muted)]">
                Case ID: {caseItem.case_id.slice(0, 13)}...
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--ink-faint)] hover:text-[var(--ink)] p-1 rounded-lg transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-4 font-mono text-xs">
          {/* Target Case Info */}
          <div className="p-3.5 rounded-xl bg-[var(--navy-elevated)] border border-[var(--navy-border)] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[var(--ink-muted)]">Flagged Group:</span>
              <span className="font-bold text-[var(--ink)]">
                [{caseItem.group.join(", ")}]
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--ink-muted)]">Risk Score at Opening:</span>
              <span className="font-bold text-rose-400">
                {caseItem.risk_score} / 100
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--ink-muted)]">Current Case Status:</span>
              <span className="px-2 py-0.5 rounded bg-amber-950/60 text-amber-300 border border-amber-500/40 text-[10px] font-bold">
                {caseItem.status}
              </span>
            </div>
            {caseItem.opened_tx && (
              <div className="flex items-center justify-between pt-1 border-t border-[var(--navy-border)]">
                <span className="text-[var(--ink-muted)]">On-Chain Open Tx:</span>
                <span className="text-cyan-400 text-[10px] truncate max-w-[200px]" title={caseItem.opened_tx}>
                  {caseItem.opened_tx}
                </span>
              </div>
            )}
          </div>

          {/* Compliance Statement Callout */}
          <div className="p-3 rounded-lg bg-cyan-950/30 border border-cyan-700/40 text-[11px] text-cyan-200/90 flex items-start gap-2.5">
            <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              <strong>Compliance Proof Protocol:</strong> A challenge verifies that the agent&apos;s action complied with its pre-committed execution policy (via keccak256 hash match & ECDSA signature).
              <br />
              <span className="text-cyan-300 font-medium">
                Note: A &quot;CLEARED&quot; verdict proves execution-policy compliance only; it does NOT prove absence of tacit coordination.
              </span>
            </p>
          </div>

          {/* Challenge Result Display */}
          {result && (
            <div
              className={`p-4 rounded-xl border text-xs space-y-2 animate-fade-in ${
                result.status === "CLEARED"
                  ? "bg-emerald-950/40 border-emerald-500/60 text-emerald-200"
                  : "bg-rose-950/40 border-rose-500/60 text-rose-200"
              }`}
            >
              <div className="flex items-center justify-between font-bold text-sm">
                <div className="flex items-center gap-2">
                  {result.status === "CLEARED" ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-rose-400" />
                  )}
                  <span>VERDICT: {result.status}</span>
                </div>
                <span className="text-xs px-2 py-0.5 rounded bg-black/40 border border-current font-mono">
                  {result.status === "CLEARED" ? "POLICY COMPLIANT" : "POLICY VIOLATION"}
                </span>
              </div>

              <p className="text-[11px] leading-relaxed pt-1">
                {result.explanation}
              </p>

              {result.challenge_tx && (
                <div className="pt-2 border-t border-emerald-500/20 text-[10px] flex items-center justify-between">
                  <span>Challenge Tx:</span>
                  <span className="font-mono text-cyan-300 truncate max-w-[260px]">
                    {result.challenge_tx}
                  </span>
                </div>
              )}

              {result.resolved_tx && (
                <div className="text-[10px] flex items-center justify-between">
                  <span>Resolution Tx:</span>
                  <span className="font-mono text-cyan-300 truncate max-w-[260px]">
                    {result.resolved_tx}
                  </span>
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="p-3 rounded-lg bg-rose-950/50 border border-rose-500/50 text-rose-300 text-xs">
              {error}
            </div>
          )}

          {/* Action Trigger Buttons */}
          <div className="pt-2 space-y-2">
            <span className="text-[10px] text-[var(--ink-faint)] uppercase tracking-wider block">
              Demonstration Triggers
            </span>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <button
                onClick={handleValidChallenge}
                disabled={submitting}
                className="flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-lg bg-emerald-950 hover:bg-emerald-900/80 text-emerald-300 border border-emerald-600/50 font-medium text-xs transition cursor-pointer disabled:opacity-50"
              >
                {submitting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <FileCheck2 className="w-4 h-4 text-emerald-400" />
                )}
                <span>Test Valid Policy (Clears)</span>
              </button>

              <button
                onClick={handleInvalidChallenge}
                disabled={submitting}
                className="flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-lg bg-rose-950 hover:bg-rose-900/80 text-rose-300 border border-rose-600/50 font-medium text-xs transition cursor-pointer disabled:opacity-50"
              >
                {submitting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <FileX2 className="w-4 h-4 text-rose-400" />
                )}
                <span>Test Invalid Policy (Escalates)</span>
              </button>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-[var(--navy-border)] flex justify-end bg-[var(--navy-elevated)]">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono transition cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
