'use client'

import { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'

type Edge = {
  a: number
  b: number
  level: 'LOW' | 'MEDIUM' | 'HIGH'
  /** particles per edge, scaled by coordination strength */
  flow: number
}

const NODES = [
  { id: 'A1', x: 0.5, y: 0.14 },
  { id: 'A2', x: 0.85, y: 0.55 },
  { id: 'A3', x: 0.5, y: 0.9 },
  { id: 'A4', x: 0.15, y: 0.55 },
]

const EDGES: Edge[] = [
  { a: 1, b: 2, level: 'HIGH', flow: 3 }, // A2-A3
  { a: 1, b: 3, level: 'HIGH', flow: 2 }, // A2-A4
  { a: 0, b: 3, level: 'MEDIUM', flow: 1 }, // A1-A4
  { a: 0, b: 2, level: 'LOW', flow: 0.4 }, // A1-A3
  { a: 0, b: 1, level: 'LOW', flow: 0.3 }, // A1-A2
  { a: 2, b: 3, level: 'MEDIUM', flow: 1 }, // A3-A4
]

const COLORS = {
  LOW: 'rgba(120, 133, 148, ALPHA)',
  MEDIUM: 'rgba(240, 180, 90, ALPHA)',
  HIGH: 'rgba(74, 222, 210, ALPHA)',
}

function color(level: keyof typeof COLORS, alpha: number) {
  return COLORS[level].replace('ALPHA', String(alpha))
}

interface Particle {
  edge: number
  t: number
  speed: number
}

export function AgentNetwork({ className }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const reduce =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    let width = 0
    let height = 0
    let dpr = 1

    const resize = () => {
      const rect = canvas.getBoundingClientRect()
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      width = rect.width
      height = rect.height
      canvas.width = width * dpr
      canvas.height = height * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(canvas)

    // seed particles
    const particles: Particle[] = []
    EDGES.forEach((edge, i) => {
      const count = Math.round(edge.flow * 3)
      for (let p = 0; p < count; p++) {
        particles.push({ edge: i, t: Math.random(), speed: 0.0009 + Math.random() * 0.0012 })
      }
    })

    const pos = (n: (typeof NODES)[number]) => ({
      x: n.x * width,
      y: n.y * height,
    })

    let raf = 0
    let start = performance.now()

    const draw = (now: number) => {
      const elapsed = now - start
      ctx.clearRect(0, 0, width, height)

      // edges
      EDGES.forEach((edge) => {
        const a = pos(NODES[edge.a])
        const b = pos(NODES[edge.b])
        ctx.beginPath()
        ctx.moveTo(a.x, a.y)
        ctx.lineTo(b.x, b.y)
        ctx.strokeStyle = color(edge.level, edge.level === 'HIGH' ? 0.28 : 0.14)
        ctx.lineWidth = edge.level === 'HIGH' ? 1.4 : 1
        ctx.stroke()
      })

      // particles
      particles.forEach((particle) => {
        const edge = EDGES[particle.edge]
        if (!reduce) particle.t += particle.speed * 16
        if (particle.t > 1) particle.t -= 1
        const a = pos(NODES[edge.a])
        const b = pos(NODES[edge.b])
        const x = a.x + (b.x - a.x) * particle.t
        const y = a.y + (b.y - a.y) * particle.t
        const r = edge.level === 'HIGH' ? 2.4 : 1.6
        ctx.beginPath()
        ctx.arc(x, y, r, 0, Math.PI * 2)
        ctx.fillStyle = color(edge.level, 0.9)
        ctx.shadowColor = color(edge.level, 0.8)
        ctx.shadowBlur = 8
        ctx.fill()
        ctx.shadowBlur = 0
      })

      // nodes
      NODES.forEach((node, i) => {
        const p = pos(node)
        const pulse = reduce ? 0 : Math.sin(elapsed / 700 + i) * 1.5
        // outer ring
        ctx.beginPath()
        ctx.arc(p.x, p.y, 18 + pulse, 0, Math.PI * 2)
        ctx.strokeStyle = 'rgba(74, 222, 210, 0.22)'
        ctx.lineWidth = 1
        ctx.stroke()
        // core
        ctx.beginPath()
        ctx.arc(p.x, p.y, 10, 0, Math.PI * 2)
        ctx.fillStyle = 'rgba(11, 15, 20, 0.95)'
        ctx.fill()
        ctx.strokeStyle = 'rgba(74, 222, 210, 0.85)'
        ctx.lineWidth = 1.4
        ctx.stroke()
        // label
        ctx.fillStyle = 'rgba(232, 238, 245, 0.92)'
        ctx.font = '600 11px ui-monospace, monospace'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(node.id, p.x, p.y)
      })

      raf = requestAnimationFrame(draw)
    }

    raf = requestAnimationFrame(draw)

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
    }
  }, [])

  return (
    <div className={cn('relative', className)}>
      <canvas ref={canvasRef} className="h-full w-full" aria-hidden />
      <span className="sr-only">
        Animated network of four trading agents. Edges between agents A2, A3 and A4 show high
        coordination activity.
      </span>
    </div>
  )
}
