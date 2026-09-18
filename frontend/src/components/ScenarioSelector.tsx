import { Play, RotateCw } from "lucide-react"
import type { Scenario } from "@/types"

type Props = {
  scenarios: Scenario[]
  selectedId: string
  onSelect: (id: string) => void
  onStart: () => void
  running: boolean
}

export function ScenarioSelector({ scenarios, selectedId, onSelect, onStart, running }: Props) {
  const selected = scenarios.find((s) => s.id === selectedId)

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        {scenarios.map((s) => {
          const isActive = s.id === selectedId
          return (
            <button
              key={s.id}
              onClick={() => onSelect(s.id)}
              className="rounded-lg border px-3 py-2 text-left transition-colors"
              style={{
                borderColor: isActive ? "var(--violet)" : "var(--navy-border)",
                backgroundColor: isActive ? "color-mix(in oklab, var(--violet) 10%, transparent)" : "transparent",
              }}
            >
              <div className="flex items-center gap-2">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: isActive ? "var(--violet)" : "var(--ink-faint)" }}
                />
                <span className="text-sm font-medium" style={{ color: isActive ? "var(--ink)" : "var(--ink-muted)" }}>
                  {s.name}
                </span>
              </div>
              <p className="mt-0.5 pl-4 text-xs leading-snug text-ink-faint">{s.description}</p>
            </button>
          )
        })}
      </div>

      <button
        onClick={onStart}
        className="flex items-center justify-center gap-2 rounded-lg bg-violet px-3 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110"
        style={{ boxShadow: "0 0 24px color-mix(in oklab, var(--violet) 40%, transparent)" }}
      >
        {running ? <RotateCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
        {running ? "Restart scenario" : "Start scenario"}
        {selected ? <span className="opacity-70">· {selected.name}</span> : null}
      </button>
    </div>
  )
}
