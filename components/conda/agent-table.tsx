"use client"

import type { Agent, AgentStatus } from "@/lib/conda-data"
import { formatUsd } from "@/lib/conda-data"

const STATUS_META: Record<AgentStatus, { label: string; color: string }> = {
  coordinating: { label: "Coordinating", color: "var(--risk)" },
  watch: { label: "Watch", color: "var(--warn)" },
  independent: { label: "Independent", color: "var(--verified)" },
}

function pairRiskColor(v: number) {
  if (v >= 70) return "var(--risk)"
  if (v >= 40) return "var(--warn)"
  return "var(--verified)"
}

export function AgentTable({ agents }: { agents: Agent[] }) {
  return (
    <div className="overflow-hidden rounded-lg border border-navy-border">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="bg-white/[0.03] text-left text-[11px] uppercase tracking-wider text-ink-faint">
            <th className="px-3 py-2 font-medium">Agent ID</th>
            <th className="px-3 py-2 text-right font-medium">Last Price</th>
            <th className="px-3 py-2 text-right font-medium">PnL</th>
            <th className="px-3 py-2 font-medium">Pair Risk</th>
            <th className="px-3 py-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {agents.map((a) => {
            const meta = STATUS_META[a.status]
            const prc = pairRiskColor(a.pairRisk)
            return (
              <tr key={a.id} className="border-t border-navy-border hover:bg-white/[0.02]">
                <td className="px-3 py-2 font-mono font-medium text-ink">{a.id}</td>
                <td className="px-3 py-2 text-right font-mono text-ink">{a.lastPrice.toFixed(2)}</td>
                <td
                  className="px-3 py-2 text-right font-mono"
                  style={{ color: a.pnl >= 0 ? "var(--verified)" : "var(--risk)" }}
                >
                  {formatUsd(a.pnl)}
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-white/[0.06]">
                      <div className="h-full rounded-full" style={{ width: `${a.pairRisk}%`, backgroundColor: prc }} />
                    </div>
                    <span className="font-mono text-xs" style={{ color: prc }}>
                      {a.pairRisk}
                    </span>
                  </div>
                </td>
                <td className="px-3 py-2">
                  <span
                    className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium"
                    style={{ color: meta.color, backgroundColor: `color-mix(in oklab, ${meta.color} 14%, transparent)` }}
                  >
                    <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: meta.color }} />
                    {meta.label}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
