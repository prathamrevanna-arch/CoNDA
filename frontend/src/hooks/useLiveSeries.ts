import { useEffect, useState } from "react"
import { generateSeries } from "@/mocks/data"
import type { PricePoint } from "@/types"

export function useLiveSeries(running: boolean) {
  const [series, setSeries] = useState<PricePoint[]>(() => generateSeries())

  useEffect(() => {
    if (!running) return
    const id = setInterval(() => {
      setSeries((prev) => generateSeries(prev.length, Math.floor(Math.random() * 1e9)))
    }, 2600)
    return () => clearInterval(id)
  }, [running])

  return { series, setSeries }
}
