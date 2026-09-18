"use client"

import { useMemo, useRef, useState } from "react"
import type { PricePoint, ShockEvent } from "@/lib/conda-data"

type Props = {
  data: PricePoint[]
  shocks: ShockEvent[]
}

const W = 720
const H = 260
const PAD = { top: 16, right: 16, bottom: 28, left: 44 }

export function PriceChart({ data, shocks }: Props) {
  const [hover, setHover] = useState<number | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  const { xFor, yFor, obsPath, refPath, minTick, maxTick } = useMemo(() => {
    const minTick = data[0]?.tick ?? 0
    const maxTick = data[data.length - 1]?.tick ?? 1
    const all = data.flatMap((d) => [d.observed, d.reference])
    const min = Math.min(...all) - 1
    const max = Math.max(...all) + 1

    const xFor = (tick: number) =>
      PAD.left + ((tick - minTick) / (maxTick - minTick || 1)) * (W - PAD.left - PAD.right)
    const yFor = (v: number) =>
      PAD.top + (1 - (v - min) / (max - min || 1)) * (H - PAD.top - PAD.bottom)

    const line = (key: "observed" | "reference") =>
      data.map((d, i) => `${i === 0 ? "M" : "L"} ${xFor(d.tick).toFixed(1)} ${yFor(d[key]).toFixed(1)}`).join(" ")

    return { xFor, yFor, obsPath: line("observed"), refPath: line("reference"), minTick, maxTick }
  }, [data])

  const yTicks = useMemo(() => {
    const all = data.flatMap((d) => [d.observed, d.reference])
    const min = Math.floor(Math.min(...all) - 1)
    const max = Math.ceil(Math.max(...all) + 1)
    const step = (max - min) / 4
    return Array.from({ length: 5 }, (_, i) => Number((min + step * i).toFixed(1)))
  }, [data])

  function handleMove(e: React.MouseEvent<SVGSVGElement>) {
    const svg = svgRef.current
    if (!svg) return
    const rect = svg.getBoundingClientRect()
    const x = ((e.clientX - rect.left) / rect.width) * W
    const ratio = (x - PAD.left) / (W - PAD.left - PAD.right)
    const tick = Math.round(minTick + ratio * (maxTick - minTick))
    if (tick < minTick || tick > maxTick) {
      setHover(null)
      return
    }
    setHover(tick)
  }

  const hoverPoint = hover != null ? data.find((d) => d.tick === hover) : null

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        onMouseMove={handleMove}
        onMouseLeave={() => setHover(null)}
        role="img"
        aria-label="Observed mid-price versus competitive reference price over time"
      >
        {/* grid + y axis */}
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={yFor(t)} y2={yFor(t)} stroke="rgba(255,255,255,0.05)" />
            <text x={PAD.left - 8} y={yFor(t) + 3} textAnchor="end" className="fill-[var(--ink-faint)] font-mono text-[10px]">
              {t}
            </text>
          </g>
        ))}

        {/* shock event markers */}
        {shocks.map((s) => (
          <g key={s.tick}>
            <line
              x1={xFor(s.tick)}
              x2={xFor(s.tick)}
              y1={PAD.top}
              y2={H - PAD.bottom}
              stroke="var(--warn)"
              strokeOpacity={0.5}
              strokeDasharray="4 4"
            />
            <rect x={xFor(s.tick) - 3} y={PAD.top} width={6} height={6} rx={1} fill="var(--warn)" />
          </g>
        ))}

        {/* reference then observed */}
        <path d={refPath} fill="none" stroke="var(--cyan)" strokeWidth={2} strokeOpacity={0.9} />
        <path d={obsPath} fill="none" stroke="var(--violet)" strokeWidth={2.4} />

        {/* hover marker */}
        {hoverPoint && (
          <g>
            <line
              x1={xFor(hoverPoint.tick)}
              x2={xFor(hoverPoint.tick)}
              y1={PAD.top}
              y2={H - PAD.bottom}
              stroke="rgba(255,255,255,0.25)"
            />
            <circle cx={xFor(hoverPoint.tick)} cy={yFor(hoverPoint.reference)} r={3.5} fill="var(--cyan)" />
            <circle cx={xFor(hoverPoint.tick)} cy={yFor(hoverPoint.observed)} r={3.5} fill="var(--violet)" />
          </g>
        )}

        {/* x axis ticks */}
        {[minTick, Math.round((minTick + maxTick) / 2), maxTick].map((t) => (
          <text key={t} x={xFor(t)} y={H - 8} textAnchor="middle" className="fill-[var(--ink-faint)] font-mono text-[10px]">
            t{t}
          </text>
        ))}
      </svg>

      {/* legend */}
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

      {/* tooltip */}
      {hoverPoint && (
        <div
          className="pointer-events-none absolute z-10 min-w-[168px] rounded-lg border border-navy-border bg-navy-elevated/95 p-2.5 text-xs shadow-xl backdrop-blur"
          style={{
            left: `${(xFor(hoverPoint.tick) / W) * 100}%`,
            top: 8,
            transform: `translateX(${xFor(hoverPoint.tick) > W / 2 ? "-108%" : "8%"})`,
          }}
        >
          <div className="mb-1.5 flex items-center justify-between border-b border-navy-border pb-1.5">
            <span className="font-mono text-ink-faint">tick</span>
            <span className="font-mono font-semibold text-ink">t{hoverPoint.tick}</span>
          </div>
          <div className="flex items-center justify-between gap-4 py-0.5">
            <span className="flex items-center gap-1.5 text-ink-muted">
              <span className="h-2 w-2 rounded-full bg-violet" /> Observed
            </span>
            <span className="font-mono text-ink">{hoverPoint.observed.toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between gap-4 py-0.5">
            <span className="flex items-center gap-1.5 text-ink-muted">
              <span className="h-2 w-2 rounded-full bg-cyan" /> Reference
            </span>
            <span className="font-mono text-ink">{hoverPoint.reference.toFixed(2)}</span>
          </div>
          <div className="mt-1 flex items-center justify-between gap-4 border-t border-navy-border pt-1.5">
            <span className="text-ink-muted">Gap</span>
            <span className="font-mono font-semibold" style={{ color: hoverPoint.gap >= 2 ? "var(--risk)" : "var(--warn)" }}>
              +{hoverPoint.gap.toFixed(2)}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
