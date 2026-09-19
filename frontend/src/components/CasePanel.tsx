import { useState } from "react"
import { Copy, Gavel, ShieldAlert } from "lucide-react"
import { truncateHash, type Case, type CaseStatus } from "@/types"

const STATUS_META: Record<CaseStatus, { color: string; label: string }> = {
  OPEN: { color: "var(--cyan)", label: "Under review" },
  CHALLENGED: { color: "var(--warn)", label: "Challenged" },
  CLEARED: { color: "var(--verified)", label: "Cleared" },
  ESCALATED: { color: "var(--risk)", label: "Escalated" },
}

function HashRow({ label, hash }: { label: string; hash: string | null }) {
  return (
    <div className="flex items-center justify-between gap-2 py-0.5">
      <span className="text-[11px] uppercase tracking-wider text-ink-faint">{label}</span>
      {hash ? (
        <span className="flex items-center gap-1.5">
          <span className="font-mono text-xs text-ink" title={hash}>
            {truncateHash(hash)}
          </span>
          <Copy className="h-3 w-3 text-ink-faint" />
        </span>
      ) : (
        <span className="font-mono text-xs text-ink-faint">—</span>
      )}
    </div>
  )
}

export function CasePanel({ cases, onSubmitChallenge }: { cases: Case[]; onSubmitChallenge: (id: string) => void }) {
  const [selected, setSelected] = useState(cases[0]?.id ?? "")
  const active = cases.find((c) => c.id === selected) ?? cases[0]

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-1.5">
        {cases.map((c) => {
          const meta = STATUS_META[c.status]
          const isActive = c.id === active?.id
          return (
            <button
              key={c.id}
              onClick={() => setSelected(c.id)}
              className="flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-medium transition-colors"
              style={{
                borderColor: isActive ? meta.color : "var(--navy-border)",
                backgroundColor: isActive ? `color-mix(in oklab, ${meta.color} 12%, transparent)` : "transparent",
                color: isActive ? "var(--ink)" : "var(--ink-muted)",
              }}
            >
              <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: meta.color }} />
              <span className="font-mono">{c.id}</span>
            </button>
          )
        })}
      </div>

      {active && (
        <div className="rounded-lg border border-navy-border bg-white/[0.02] p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="font-mono text-sm font-semibold text-ink">{active.id}</span>
            <span
              className="rounded-full px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider"
              style={{
                color: STATUS_META[active.status].color,
                backgroundColor: `color-mix(in oklab, ${STATUS_META[active.status].color} 16%, transparent)`,
              }}
            >
              {STATUS_META[active.status].label}
            </span>
          </div>

          {active.status === "CLEARED" && (
            <p className="mb-2 text-[11px] font-medium" style={{ color: "var(--verified)" }}>
              Policy compliance verified.
            </p>
          )}

          <div className="mb-2 flex items-center justify-between">
            <div>
              <span className="text-[11px] uppercase tracking-wider text-ink-faint">Group members</span>
              <div className="mt-1 flex flex-wrap gap-1">
                {active.members.map((m) => (
                  <span key={m} className="rounded bg-white/[0.05] px-1.5 py-0.5 font-mono text-xs text-ink">
                    {m}
                  </span>
                ))}
              </div>
            </div>
            <div className="text-right">
              <span className="text-[11px] uppercase tracking-wider text-ink-faint">Risk score</span>
              <div
                className="font-mono text-2xl font-bold"
                style={{ color: active.risk >= 70 ? "var(--risk)" : active.risk >= 40 ? "var(--warn)" : "var(--verified)" }}
              >
                {active.risk}
              </div>
            </div>
          </div>

          <div className="border-t border-navy-border pt-2">
            <HashRow label="Evidence hash" hash={active.evidenceHash} />
            <HashRow label="Opened tx" hash={active.openedTx} />
            <HashRow label="Challenge tx" hash={active.challengeTx} />
          </div>

          <button
            onClick={() => onSubmitChallenge(active.id)}
            disabled={active.status !== "OPEN"}
            className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-sm font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-40"
            style={{
              backgroundColor: active.status === "OPEN" ? "var(--violet)" : "rgba(255,255,255,0.06)",
              color: active.status === "OPEN" ? "#fff" : "var(--ink-muted)",
              boxShadow: active.status === "OPEN" ? "0 0 24px color-mix(in oklab, var(--violet) 45%, transparent)" : "none",
            }}
          >
            {active.status === "CHALLENGED" ? (
              <>
                <ShieldAlert className="h-4 w-4" /> Challenge submitted
              </>
            ) : (
              <>
                <Gavel className="h-4 w-4" /> Submit Challenge
              </>
            )}
          </button>
          <p className="mt-2 text-center text-[11px] leading-snug text-ink-faint">
            A challenge is a contestable, on-chain rebuttal — evidence, not a verdict.
          </p>
        </div>
      )}
    </div>
  )
}
