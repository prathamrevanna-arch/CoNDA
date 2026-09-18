import { RISK_COLORS, RISK_LABELS, riskBand } from "@/types"

type Props = {
  value: number
}

function polar(cx: number, cy: number, r: number, angleDeg: number) {
  const a = (angleDeg * Math.PI) / 180
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) }
}

function arcPath(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
  const start = polar(cx, cy, r, startDeg)
  const end = polar(cx, cy, r, endDeg)
  const largeArc = Math.abs(endDeg - startDeg) > 180 ? 1 : 0
  const sweep = endDeg > startDeg ? 1 : 0
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} ${sweep} ${end.x} ${end.y}`
}

export function RiskGauge({ value }: Props) {
  const band = riskBand(value)
  const color = RISK_COLORS[band]

  const cx = 130
  const cy = 130
  const r = 100
  const angle = 180 + (value / 100) * 180
  const cap = polar(cx, cy, r, angle)

  const bandStops = [
    { from: 0, to: 40, color: "var(--verified)" },
    { from: 40, to: 70, color: "var(--warn)" },
    { from: 70, to: 100, color: "var(--risk)" },
  ]

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 260 150" className="w-full max-w-[260px]" role="img" aria-label={`Coordination risk ${value} out of 100`}>
        <path d={arcPath(cx, cy, r, 180, 360)} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={18} strokeLinecap="round" />
        {bandStops.map((b) => (
          <path
            key={b.from}
            d={arcPath(cx, cy, r, 180 + (b.from / 100) * 180, 180 + (b.to / 100) * 180)}
            fill="none"
            stroke={b.color}
            strokeWidth={18}
            strokeOpacity={b.color === color ? 0.28 : 0.12}
            strokeLinecap="butt"
          />
        ))}
        <path d={arcPath(cx, cy, r, 180, angle)} fill="none" stroke={color} strokeWidth={18} strokeLinecap="round" />
        <circle cx={cap.x} cy={cap.y} r={9} fill={color} stroke="var(--navy-card)" strokeWidth={3} />
      </svg>

      <div className="-mt-14 flex flex-col items-center">
        <span className="font-mono text-6xl font-bold leading-none tracking-tight" style={{ color }}>
          {value}
        </span>
        <span className="mt-1 text-sm font-medium text-ink-muted">/ 100</span>
      </div>

      <div
        className="mt-3 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wider"
        style={{ color, backgroundColor: `color-mix(in oklab, ${color} 16%, transparent)` }}
      >
        {RISK_LABELS[band]}
      </div>

      <div className="mt-4 grid w-full grid-cols-3 gap-1.5 text-[11px]">
        {[
          { label: "Low", range: "0–39", c: "var(--verified)", active: band === "low" },
          { label: "Medium", range: "40–69", c: "var(--warn)", active: band === "medium" },
          { label: "High", range: "70–100", c: "var(--risk)", active: band === "high" },
        ].map((t) => (
          <div
            key={t.label}
            className="flex flex-col items-center rounded-md border px-1.5 py-1.5"
            style={{
              borderColor: t.active ? t.c : "var(--navy-border)",
              backgroundColor: t.active ? `color-mix(in oklab, ${t.c} 12%, transparent)` : "transparent",
            }}
          >
            <span className="h-1.5 w-full rounded-full" style={{ backgroundColor: t.c, opacity: t.active ? 1 : 0.45 }} />
            <span className="mt-1 font-medium" style={{ color: t.active ? t.c : "var(--ink-muted)" }}>
              {t.label}
            </span>
            <span className="font-mono text-ink-faint">{t.range}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
