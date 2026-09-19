import type { TooltipProps } from "recharts"
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import type { PricePoint, ShockEvent } from "@/types"

type Props = {
  data: PricePoint[]
  shocks: ShockEvent[]
}

function ChartTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null
  const observed = payload.find((p) => p.dataKey === "observed")?.value
  const reference = payload.find((p) => p.dataKey === "reference")?.value
  if (typeof observed !== "number" || typeof reference !== "number") return null
  const gap = Number((observed - reference).toFixed(2))

  return (
    <div className="min-w-[168px] rounded-lg border border-navy-border bg-navy-elevated/95 p-2.5 text-xs shadow-xl backdrop-blur">
      <div className="mb-1.5 flex items-center justify-between border-b border-navy-border pb-1.5">
        <span className="font-mono text-ink-faint">tick</span>
        <span className="font-mono font-semibold text-ink">t{label}</span>
      </div>
      <div className="flex items-center justify-between gap-4 py-0.5">
        <span className="flex items-center gap-1.5 text-ink-muted">
          <span className="h-2 w-2 rounded-full bg-violet" /> Observed
        </span>
        <span className="font-mono text-ink">{observed.toFixed(2)}</span>
      </div>
      <div className="flex items-center justify-between gap-4 py-0.5">
        <span className="flex items-center gap-1.5 text-ink-muted">
          <span className="h-2 w-2 rounded-full bg-cyan" /> Reference
        </span>
        <span className="font-mono text-ink">{reference.toFixed(2)}</span>
      </div>
      <div className="mt-1 flex items-center justify-between gap-4 border-t border-navy-border pt-1.5">
        <span className="text-ink-muted">Gap</span>
        <span className="font-mono font-semibold" style={{ color: gap >= 2 ? "var(--risk)" : "var(--warn)" }}>
          +{gap.toFixed(2)}
        </span>
      </div>
    </div>
  )
}

export function PriceChart({ data, shocks }: Props) {
  return (
    <div className="relative">
      <div className="h-[260px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 16, right: 16, bottom: 8, left: 8 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis
              dataKey="tick"
              tickFormatter={(tick: number) => `t${tick}`}
              tick={{ fill: "var(--ink-faint)", fontSize: 10, fontFamily: "ui-monospace, monospace" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              domain={["auto", "auto"]}
              tick={{ fill: "var(--ink-faint)", fontSize: 10, fontFamily: "ui-monospace, monospace" }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            {shocks.map((s) => (
              <ReferenceLine
                key={s.tick}
                x={s.tick}
                stroke="var(--warn)"
                strokeOpacity={0.5}
                strokeDasharray="4 4"
              />
            ))}
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: "rgba(255,255,255,0.25)" }} />
            <Line
              type="monotone"
              dataKey="reference"
              stroke="var(--cyan)"
              strokeWidth={2}
              strokeOpacity={0.9}
              dot={false}
              activeDot={{ r: 3.5, fill: "var(--cyan)" }}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="observed"
              stroke="var(--violet)"
              strokeWidth={2.4}
              dot={false}
              activeDot={{ r: 3.5, fill: "var(--violet)" }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-1 flex items-center gap-4 px-1 text-xs">
        <span className="flex items-center gap-1.5 text-ink-muted">
          <span className="h-0.5 w-4 rounded-full bg-violet" /> Observed mid-price
        </span>
        <span className="flex items-center gap-1.5 text-ink-muted">
          <span className="h-0.5 w-4 rounded-full bg-cyan" /> Competitive reference price
        </span>
        <span className="flex items-center gap-1.5 text-ink-muted">
          <span className="h-2 w-2 rounded-[1px] bg-warn" /> Shock event
        </span>
      </div>
    </div>
  )
}
