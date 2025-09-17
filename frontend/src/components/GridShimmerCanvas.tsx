import { useEffect, useRef } from 'react'

type GridShimmerOptions = {
  spacingX: number
  spacingY: number
  lineWidth: number
  baseAlpha: number
  baseColor: string
  glowColor: string
  glowLineWidth: number
  glowBlur: number
  maxGlowAlpha: number
  composite: GlobalCompositeOperation
  frontSpeedMin: number
  frontSpeedMax: number
  frontWidthCells: number
  onRate: number
  decay: number
  jump: number
  flickerAmp: number
  threshold: number
  fpsCap: number
}

type GridCell = { a: number }

type GridFront = {
  pos: number
  dir: number
  speed: number
}

const DEFAULT_OPTIONS: GridShimmerOptions = {
  spacingX: 72,
  spacingY: 72,
  lineWidth: 1,
  baseAlpha: 1,
  baseColor: '#000000',
  glowColor: '#00d9ff',
  glowLineWidth: 2,
  glowBlur: 18,
  maxGlowAlpha: 0.9,
  composite: 'lighter',
  frontSpeedMin: 0.08,
  frontSpeedMax: 0.18,
  frontWidthCells: 2,
  onRate: 3,
  decay: 1.1,
  jump: 0.45,
  flickerAmp: 0.02,
  threshold: 0.05,
  fpsCap: 60,
}

class GridShimmer {
  private readonly canvas: HTMLCanvasElement
  private readonly ctx: CanvasRenderingContext2D
  private readonly opts: GridShimmerOptions
  private running = false
  private viewW = 0
  private viewH = 0
  private baseCanvas: HTMLCanvasElement | null = null
  private cells: GridCell[][] = []
  private cols = 0
  private rows = 0
  private frontWidthPx = 0
  private front: GridFront = { pos: 0, dir: 1, speed: 0 }
  private last = 0
  private rafId: number | null = null
  private readonly onResize: () => void
    private lastPointerCell: { row: number; col: number } | null = null

  private readonly handlePointerMove = (event: PointerEvent): void => {
    if (!this.cells.length) return

    const rect = this.canvas.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top

    if (x < 0 || y < 0 || x >= this.viewW || y >= this.viewH) {
      this.lastPointerCell = null
      return
    }

    const col = Math.floor(x / this.opts.spacingX)
    const row = Math.floor(y / this.opts.spacingY)

    if (row < 0 || row >= this.rows || col < 0 || col >= this.cols) {
      this.lastPointerCell = null
      return
    }

    if (this.lastPointerCell?.row === row && this.lastPointerCell.col === col) {
      return
    }

    this.lastPointerCell = { row, col }

    const cell = this.cells[row]?.[col]
    if (!cell) return

    const isOn = cell.a >= this.opts.threshold
    cell.a = isOn ? 0 : 1
  }

  private readonly handlePointerLeave = (): void => {
    this.lastPointerCell = null
  }

  constructor(canvas: HTMLCanvasElement, opts: Partial<GridShimmerOptions> = {}) {
    this.canvas = canvas
    const ctx = canvas.getContext('2d', { alpha: true })
    if (!ctx) {
      throw new Error('Canvas 2D context is not available')
    }

    this.ctx = ctx
    this.opts = { ...DEFAULT_OPTIONS, ...opts }
    this.onResize = () => {
      this.resize()
      this.makeBaseGrid()
      this.initCells()
    }
    this.canvas.addEventListener('pointermove', this.handlePointerMove)
    this.canvas.addEventListener('pointerleave', this.handlePointerLeave)

    this.init()
  }

  start(): void {
    if (this.running) return
    this.running = true
    this.last = performance.now()
    this.rafId = requestAnimationFrame(() => this.loop())
  }

  stop(): void {
    this.running = false
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId)
      this.rafId = null
    }
  }

  destroy(): void {
    this.stop()
    window.removeEventListener('resize', this.onResize)
    this.canvas.removeEventListener('pointermove', this.handlePointerMove)
    this.canvas.removeEventListener('pointerleave', this.handlePointerLeave)
  }

  private init(): void {
    this.onResize()
    window.addEventListener('resize', this.onResize)
    const width = this.viewW
    this.front = {
      pos: Math.random() * width,
      dir: Math.random() < 0.5 ? -1 : 1,
      speed: this.lerp(this.opts.frontSpeedMin, this.opts.frontSpeedMax, Math.random()),
    }
    this.last = performance.now()
  }

  private resize(): void {
    const dpr = window.devicePixelRatio || 1
    const rect = this.canvas.getBoundingClientRect()
    this.viewW = Math.max(1, Math.floor(rect.width))
    this.viewH = Math.max(1, Math.floor(rect.height))
    this.canvas.width = Math.floor(this.viewW * dpr)
    this.canvas.height = Math.floor(this.viewH * dpr)
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  }

  private makeBaseGrid(): void {
    const { spacingX, spacingY, lineWidth, baseColor, baseAlpha } = this.opts
    const w = this.viewW
    const h = this.viewH
    const off = document.createElement('canvas')
    off.width = w
    off.height = h
    const context = off.getContext('2d', { alpha: true })
    if (!context) return
    context.clearRect(0, 0, w, h)
    context.globalAlpha = baseAlpha
    context.strokeStyle = baseColor
    context.lineWidth = lineWidth
    context.beginPath()
    for (let x = 0; x <= w; x += spacingX) {
      context.moveTo(Math.floor(x) + 0.5, 0)
      context.lineTo(Math.floor(x) + 0.5, h)
    }
    for (let y = 0; y <= h; y += spacingY) {
      context.moveTo(0, Math.floor(y) + 0.5)
      context.lineTo(w, Math.floor(y) + 0.5)
    }
    context.stroke()
    this.baseCanvas = off
  }

  private initCells(): void {
    const { spacingX, spacingY } = this.opts
    this.cols = Math.max(1, Math.ceil(this.viewW / spacingX))
    this.rows = Math.max(1, Math.ceil(this.viewH / spacingY))
    this.cells = new Array(this.rows)
    for (let j = 0; j < this.rows; j += 1) {
      this.cells[j] = new Array(this.cols)
      for (let i = 0; i < this.cols; i += 1) {
        this.cells[j][i] = { a: 0 }
      }
    }
    this.frontWidthPx = this.opts.frontWidthCells * spacingX
  }

  private loop(): void {
    if (!this.running) return
    const now = performance.now()
    const dt = Math.min(100, now - this.last)
    this.last = now
    this.update(dt)
    this.render()
    this.rafId = requestAnimationFrame(() => this.loop())
  }

  private update(dt: number): void {
    const dtSec = dt / 1000
    const { spacingX, onRate, decay, jump, flickerAmp } = this.opts
    const width = this.viewW

    this.front.pos += this.front.dir * this.front.speed * dt
    if (this.front.pos < 0) {
      this.front.pos = 0
      this.front.dir = 1
      this.front.speed = this.lerp(this.opts.frontSpeedMin, this.opts.frontSpeedMax, Math.random())
    }
    if (this.front.pos > width) {
      this.front.pos = width
      this.front.dir = -1
      this.front.speed = this.lerp(this.opts.frontSpeedMin, this.opts.frontSpeedMax, Math.random())
    }

    const sigma = this.frontWidthPx * 0.5
    const inv2sigma2 = 1 / (2 * sigma * sigma + 1e-6)

    for (let j = 0; j < this.rows; j += 1) {
      for (let i = 0; i < this.cols; i += 1) {
        const xCenter = (i + 0.5) * spacingX
        const dx = xCenter - this.front.pos
        const g = Math.exp(-(dx * dx) * inv2sigma2)

        const lambdaOn = onRate * g
        const pOn = 1 - Math.exp(-lambdaOn * dtSec)
        if (Math.random() < pOn) {
          this.cells[j][i].a = Math.min(1, this.cells[j][i].a + jump * (0.8 + 0.4 * Math.random()))
        }

        this.cells[j][i].a *= Math.exp(-decay * dtSec)

        if (flickerAmp > 0) {
          this.cells[j][i].a += (Math.random() - 0.5) * flickerAmp
        }

        if (this.cells[j][i].a < 0) this.cells[j][i].a = 0
        if (this.cells[j][i].a > 1) this.cells[j][i].a = 1
      }
    }
  }

  private render(): void {
    const { spacingX, spacingY, maxGlowAlpha, glowLineWidth, glowBlur, glowColor, threshold, composite } = this.opts
    const ctx = this.ctx
    const width = this.viewW
    const height = this.viewH
    ctx.clearRect(0, 0, width, height)
    if (this.baseCanvas) {
      ctx.drawImage(this.baseCanvas, 0, 0)
    }

    ctx.save()
    ctx.globalCompositeOperation = composite
    ctx.lineCap = 'square'
    ctx.lineWidth = glowLineWidth
    ctx.shadowBlur = glowBlur
    ctx.shadowColor = glowColor
    ctx.strokeStyle = glowColor

    for (let j = 0; j < this.rows; j += 1) {
      const y0 = Math.floor(j * spacingY) + 0.5
      const y1 = Math.floor((j + 1) * spacingY) + 0.5
      for (let i = 0; i < this.cols; i += 1) {
        const alpha = this.cells[j][i].a
        if (alpha < threshold) continue
        ctx.globalAlpha = alpha * maxGlowAlpha

        const x0 = Math.floor(i * spacingX) + 0.5
        const x1Base = Math.min(Math.floor((i + 1) * spacingX), width)
        const x1 = x1Base + 0.5

        ctx.beginPath()
        ctx.moveTo(x0, y0)
        ctx.lineTo(x1, y0)
        ctx.moveTo(x0, y0)
        ctx.lineTo(x0, y1)
        ctx.moveTo(x1, y0)
        ctx.lineTo(x1, y1)
        ctx.moveTo(x0, y1)
        ctx.lineTo(x1, y1)
        ctx.stroke()
      }
    }
    ctx.restore()
  }

  private lerp(a: number, b: number, t: number): number {
    return a + (b - a) * t
  }
}

export default function GridShimmerCanvas(): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return undefined
    const canvas = canvasRef.current
    if (!canvas) return undefined

    const shimmer = new GridShimmer(canvas, {
      spacingX: 72,
      spacingY: 72,
      glowColor: '#00d9ff',
      glowBlur: 18,
      glowLineWidth: 2,
      maxGlowAlpha: 0.9,
      frontWidthCells: 2,
      onRate: 3,
      decay: 1.1,
      jump: 0.45,
      flickerAmp: 0.02,
    })

    shimmer.start()

    return () => {
      shimmer.destroy()
    }
  }, [])

  return <canvas ref={canvasRef} className="grid-shimmer-overlay" aria-hidden="true" />
}