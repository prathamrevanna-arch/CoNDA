import React from "react";
import { Blocks, Network } from "lucide-react";
import type { HealthResponse, CaseItem } from "../types/api";

interface BlockchainAuditProps {
  health: HealthResponse | null;
  cases: CaseItem[];
}

export const BlockchainAudit: React.FC<BlockchainAuditProps> = ({
  health,
  cases,
}) => {
  const isChainAvailable = health?.chain ?? false;

  // Extract all on-chain transactions across all cases
  const transactions = cases.flatMap((c) => {
    const txs: Array<{ type: string; hash: string; caseId: string; status: string }> = [];
    if (c.opened_tx) {
      txs.push({ type: "openCase", hash: c.opened_tx, caseId: c.case_id, status: "SUCCESS" });
    }
    if (c.challenge_tx) {
      txs.push({ type: "submitChallenge", hash: c.challenge_tx, caseId: c.case_id, status: "SUCCESS" });
    }
    if (c.resolved_tx) {
      txs.push({ type: "resolveCase", hash: c.resolved_tx, caseId: c.case_id, status: c.status });
    }
    return txs;
  });

  return (
    <div className="bg-[var(--navy-card)] rounded-xl border border-[var(--navy-border)] p-5 shadow-lg flex flex-col gap-4">
      <div className="flex items-center justify-between pb-3 border-b border-[var(--navy-border)]">
        <div className="flex items-center gap-2">
          <Blocks className="w-5 h-5 text-cyan-400" />
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--ink)]">
              Blockchain Audit Trail
            </h2>
            <p className="text-[11px] text-[var(--ink-muted)]">
              Local Anvil Ethereum-Compatible Smart Contract Layer
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <span
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border ${
              isChainAvailable
                ? "bg-emerald-950/60 text-emerald-300 border-emerald-700/50"
                : "bg-slate-900 text-slate-400 border-slate-700/50"
            }`}
          >
            <Network className="w-3.5 h-3.5" />
            <span>{isChainAvailable ? "ANVIL RPC CONNECTED" : "ANVIL RPC STANDBY"}</span>
          </span>
        </div>
      </div>

      {/* Network Specs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
        <div className="p-3 rounded-lg bg-[var(--navy-elevated)] border border-[var(--navy-border)]">
          <span className="text-[10px] text-[var(--ink-faint)] block mb-1">
            Network Architecture
          </span>
          <span className="font-semibold text-[var(--ink)]">
            Local Anvil Node (Chain ID 31337)
          </span>
        </div>

        <div className="p-3 rounded-lg bg-[var(--navy-elevated)] border border-[var(--navy-border)]">
          <span className="text-[10px] text-[var(--ink-faint)] block mb-1">
            Auditing Smart Contract
          </span>
          <span className="font-semibold text-cyan-300 truncate block" title="CaseRegistry.sol">
            CaseRegistry.sol
          </span>
        </div>

        <div className="p-3 rounded-lg bg-[var(--navy-elevated)] border border-[var(--navy-border)]">
          <span className="text-[10px] text-[var(--ink-faint)] block mb-1">
            Recorded On-Chain Txs
          </span>
          <span className="font-semibold text-emerald-400">
            {transactions.length} Transactions Confirmed
          </span>
        </div>
      </div>

      {/* Transaction History Table */}
      <div className="mt-1">
        <span className="text-xs font-mono font-semibold uppercase tracking-wider text-[var(--ink)] block mb-2">
          Immutable Smart Contract Log
        </span>

        {transactions.length === 0 ? (
          <div className="py-6 text-center text-xs font-mono text-[var(--ink-faint)] bg-[var(--navy-elevated)]/50 rounded-lg border border-[var(--navy-border)]">
            No on-chain transactions recorded for this session yet.
          </div>
        ) : (
          <div className="max-h-[160px] overflow-y-auto space-y-1.5 font-mono text-xs pr-1 custom-scrollbar">
            {transactions.map((tx, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 rounded bg-[var(--navy-elevated)] border border-slate-800 text-[11px]"
              >
                <div className="flex items-center gap-2 truncate max-w-md">
                  <span className="px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 text-[10px] font-bold">
                    {tx.type}()
                  </span>
                  <span className="text-[var(--ink-muted)] truncate select-all">
                    {tx.hash}
                  </span>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-[10px] text-[var(--ink-faint)]">
                    Case: #{tx.caseId.slice(0, 6)}
                  </span>
                  <span className="text-[10px] font-bold text-emerald-400">
                    CONFIRMED
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
