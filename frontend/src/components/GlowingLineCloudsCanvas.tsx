import { useEffect, useRef } from 'react'

type GlowingLineCloudsProps = {
  cloudCount?: number
  minRadius?: number
  maxRadius?: number
  pointsPerCloud?: number
  baseSpeed?: number
  speedVariance?: number
  verticalDrift?: number
  strokeWidth?: number
  glowBlur?: number
  strokeColor?: string
  secondaryStroke?: boolean
  secondaryOpacity?: number
  globalChaos?: number
  mouseInfluence?: number
  reactToHoverRadius?: number
  hoverNudgeBaseX?: number
  hoverNudgeBaseY?: number
  hoverFlipChance?: number
  collisionPadding?: number
  collisionImpulse?: number
  collisionPushRatio?: number
  maxRightwardRatio?: number
  sparkleEnabled?: boolean
  sparklePulseHz?: number
  sparkleOpacity?: number
  sparkleBaseBlur?: number
  sparkleMaxBlur?: number
  sparkleStrokeWidth?: number
  zIndex?: number
}

type CloudPoint = { x: number; y: number }

type Cloud = {
  x: number
  y: number
  radius: number
  outline: CloudPoint[]
  speed: number
  vy: number
  wobbleAmp: number
  wobbleFreq: number
  spin: number
  phase: number
  nudgeVX: number
  nudgeVY: number
  hitRadius: number
  mass: number
  twinkleFreq: number
}

type MouseState = { x: number; y: number; inside: boolean }

type CanvasSize = { w: number; h: number; dpr: number }

export default function GlowingLineCloudsCanvas({
  cloudCount = 14,
  minRadius = 60,
  maxRadius = 140,
  pointsPerCloud = 32,
  baseSpeed = 24,
  speedVariance = 0.45,
  verticalDrift = 18,
  strokeWidth = 2.2,
  glowBlur = 18,
  strokeColor = 'rgba(88, 160, 255, 0.9)',
  secondaryStroke = true,
  secondaryOpacity = 0.5,
  globalChaos = 0.65,
  mouseInfluence = 0.4,
  reactToHoverRadius = 110,
  hoverNudgeBaseX = 50,
  hoverNudgeBaseY = 60,
  hoverFlipChance = 0.08,
  collisionPadding = 0.9,
  collisionImpulse = 220,
  collisionPushRatio = 1,
  maxRightwardRatio = 0.6,
  sparkleEnabled = true,
  sparklePulseHz = 1.6,
  sparkleOpacity = 0.9,
  sparkleBaseBlur = 10,
  sparkleMaxBlur = 22,
  sparkleStrokeWidth = 1,
  zIndex = 1,
}: GlowingLineCloudsProps = {}): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const rafRef = useRef<number | null>(null)
  const cloudsRef = useRef<Cloud[]>([])
  const mouseRef = useRef<MouseState>({ x: -1e6, y: -1e6, inside: false })
  const sizeRef = useRef<CanvasSize>({ w: 0, h: 0, dpr: 1 })

  useEffect(() => {
    const handleMove = (event: PointerEvent) => {
      const rect = canvasRef.current?.getBoundingClientRect()
      if (!rect) return
      mouseRef.current = {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
        inside: true,
      }
    }

    const handleLeave = () => {
      mouseRef.current = { x: -1e6, y: -1e6, inside: false }
    }

    window.addEventListener('pointermove', handleMove, { passive: true })
    window.addEventListener('pointerleave', handleLeave, { passive: true })

    return () => {
      window.removeEventListener('pointermove', handleMove)
      window.removeEventListener('pointerleave', handleLeave)
    }
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || typeof window === 'undefined') {
      return undefined
    }

    const rand = (a: number, b: number) => Math.random() * (b - a) + a

    const parseRgba = (input: string): [number, number, number, number] | null => {
      const match = input.match(/rgba?\(([^)]+)\)/i)
      if (!match) return null
      const parts = match[1].split(',').map(part => Number(part.trim()))
      if (parts.length < 3) return null
      const [r, g, b] = parts
      const a = parts[3] ?? 1
      if ([r, g, b, a].some(value => Number.isNaN(value))) {
        return null
      }
      return [
        Math.min(255, Math.max(0, r)),
        Math.min(255, Math.max(0, g)),
        Math.min(255, Math.max(0, b)),
        Math.max(0, Math.min(1, a)),
      ]
    }

    const makeCloudShape = (radius: number, points: number, jitterStrength: number) => {
      const pts: CloudPoint[] = []
      const twoPi = Math.PI * 2
      for (let i = 0; i < points; i++) {
        const t = (i / points) * twoPi
        const rJitter =
          radius *
          (
            1 +
            jitterStrength * 0.22 * Math.sin(3 * t + rand(0, twoPi)) +
            jitterStrength * 0.12 * Math.sin(5 * t + rand(0, twoPi)) +
            jitterStrength * 0.08 * Math.sin(9 * t + rand(0, twoPi))
          )
        pts.push({ x: Math.cos(t) * rJitter, y: Math.sin(t) * rJitter })
      }
      return pts
    }

    const initClouds = (w: number, h: number) => {
      const list: Cloud[] = []
      for (let i = 0; i < cloudCount; i++) {
        const radius = rand(minRadius, maxRadius)
        const outline = makeCloudShape(radius, pointsPerCloud, globalChaos)
        const speed = baseSpeed * (1 + rand(-speedVariance, speedVariance))
        const vy0 = rand(-verticalDrift, verticalDrift)
        const wobbleAmp = rand(0.02, 0.06) * radius
        const wobbleFreq = rand(0.2, 0.6)
        const spin = rand(-0.15, 0.15)
        const twinkleFreq = sparklePulseHz * (1 + rand(-0.35, 0.35))

        let x: number
        let y: number
        let tries = 0
        while (true) {
          x = rand(0, w)
          y = rand(0, h)
          let ok = true
          for (let j = 0; j < list.length; j++) {
            const other = list[j]
            const dx = x - other.x
            const dy = y - other.y
            const dist2 = dx * dx + dy * dy
            const minD = (radius + other.radius) * collisionPadding
            if (dist2 < minD * minD) {
              ok = false
              break
            }
          }
          if (ok || tries++ > 40) break
        }

        list.push({
          x,
          y,
          radius,
          outline,
          speed,
          vy: vy0,
          wobbleAmp,
          wobbleFreq,
          spin,
          phase: rand(0, Math.PI * 2),
          nudgeVX: 0,
          nudgeVY: 0,
          hitRadius: radius * 1.05,
          mass: Math.max(30, radius * radius * 0.002 + 1),
          twinkleFreq,
        })
      }
      cloudsRef.current = list
    }

    const resize = () => {
      const context = canvas.getContext('2d')
      if (!context) return
      const dpr = Math.max(1, Math.min(2.5, window.devicePixelRatio || 1))
      const w = Math.floor(window.innerWidth)
      const h = Math.floor(window.innerHeight)

      canvas.width = Math.floor(w * dpr)
      canvas.height = Math.floor(h * dpr)
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`

      context.setTransform(dpr, 0, 0, dpr, 0, 0)

      sizeRef.current = { w, h, dpr }
      initClouds(w, h)
    }

    resize()

    const ctx = canvas.getContext('2d')
    if (!ctx) return undefined
    ctx.lineJoin = 'round'
    ctx.lineCap = 'round'
    ctx.globalCompositeOperation = 'lighter'

    const baseStroke = parseRgba(strokeColor)

    let last = performance.now()

    const frame = (now: number) => {
      const { w, h } = sizeRef.current
      const dt = Math.max(0.001, Math.min(0.05, (now - last) / 1000))
      last = now

      ctx.clearRect(0, 0, w, h)

      const { x: mx, y: my } = mouseRef.current

      for (const cloud of cloudsRef.current) {
        let vx = -cloud.speed
        let vy = cloud.vy

        const t = now / 1000 + cloud.phase
        vy += Math.sin(t * 0.6) * 6 + Math.cos(t * 0.9) * 4

        const dx = cloud.x - mx
        const dy = cloud.y - my
        const dist2 = dx * dx + dy * dy
        const r = Math.max(reactToHoverRadius, cloud.hitRadius)
        if (dist2 < r * r) {
          const d = Math.sqrt(dist2) || 1
          const nx = dx / d
          const ny = dy / d
          const strength = (1 - d / r) * mouseInfluence
          cloud.nudgeVX += nx * hoverNudgeBaseX * strength
          cloud.nudgeVY += ny * hoverNudgeBaseY * strength
          if (Math.random() < hoverFlipChance) {
            cloud.vy = -cloud.vy
          }
        }

        const nDecay = Math.exp(-dt * 1.8)
        cloud.nudgeVX *= nDecay
        cloud.nudgeVY *= nDecay

        if (cloud.nudgeVX > cloud.speed * maxRightwardRatio) {
          cloud.nudgeVX = cloud.speed * maxRightwardRatio
        }

        vx += cloud.nudgeVX
        vy += cloud.nudgeVY

        cloud.x += vx * dt
        cloud.y += vy * dt

        if (cloud.y < -cloud.radius * 0.3) {
          cloud.y = -cloud.radius * 0.3
          cloud.vy = Math.abs(cloud.vy)
        } else if (cloud.y > h + cloud.radius * 0.3) {
          cloud.y = h + cloud.radius * 0.3
          cloud.vy = -Math.abs(cloud.vy)
        }

        if (cloud.x < -cloud.radius - 20) {
          cloud.x = w + cloud.radius + rand(0, 80)
          cloud.y = rand(0, h)
        }
      }

      const arr = cloudsRef.current
      for (let i = 0; i < arr.length; i++) {
        for (let j = i + 1; j < arr.length; j++) {
          const a = arr[i]
          const b = arr[j]
          let dx = b.x - a.x
          let dy = b.y - a.y
          let d2 = dx * dx + dy * dy
          const minD = (a.radius + b.radius) * collisionPadding
          const minD2 = minD * minD
          if (d2 < minD2) {
            const d = Math.sqrt(d2) || 0.0001
            let nx = dx / d
            let ny = dy / d
            if (!Number.isFinite(nx) || !Number.isFinite(ny)) {
              nx = 1
              ny = 0
            }
            const overlap = (minD - d) * collisionPushRatio

            const imA = 1 / a.mass
            const imB = 1 / b.mass
            const imSum = imA + imB
            const moveA = (imA / imSum) * overlap
            const moveB = (imB / imSum) * overlap

            a.x -= nx * moveA
            a.y -= ny * moveA
            b.x += nx * moveB
            b.y += ny * moveB

            const intensity = overlap / minD
            const jImpulse = collisionImpulse * intensity
            a.nudgeVX -= nx * jImpulse * imA
            a.nudgeVY -= ny * jImpulse * imA
            b.nudgeVX += nx * jImpulse * imB
            b.nudgeVY += ny * jImpulse * imB

            if (a.nudgeVX > a.speed * maxRightwardRatio) {
              a.nudgeVX = a.speed * maxRightwardRatio
            }
            if (b.nudgeVX > b.speed * maxRightwardRatio) {
              b.nudgeVX = b.speed * maxRightwardRatio
            }
          }
        }
      }

      for (const cloud of cloudsRef.current) {
        const t = now / 1000 + cloud.phase
        const wobble = cloud.wobbleAmp
        const wf = cloud.wobbleFreq

        ctx.save()
        ctx.translate(cloud.x, cloud.y)

        ctx.shadowColor = strokeColor
        ctx.shadowBlur = glowBlur
        ctx.lineWidth = strokeWidth
        ctx.strokeStyle = strokeColor

        ctx.beginPath()
        for (let i = 0; i < cloud.outline.length; i++) {
          const p = cloud.outline[i]
          const wx = p.x + Math.sin(i * 0.7 + t * 1.2 * wf) * wobble * 0.3
          const wy = p.y + Math.cos(i * 0.9 + t * 1.1 * wf) * wobble * 0.3
          if (i === 0) {
            ctx.moveTo(wx, wy)
          } else {
            ctx.lineTo(wx, wy)
          }
        }
        ctx.closePath()
        ctx.stroke()

        if (secondaryStroke) {
          ctx.shadowBlur = glowBlur * 0.5
          ctx.lineWidth = strokeWidth * 0.8
          if (baseStroke) {
            const [r, g, b, a] = baseStroke
            const nextA = Math.max(0, Math.min(1, a * secondaryOpacity))
            ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${nextA})`
          } else {
            ctx.strokeStyle = strokeColor
          }
          ctx.beginPath()
          for (let i = 0; i < cloud.outline.length; i++) {
            const p = cloud.outline[i]
            const wx = p.x + Math.sin(i * 0.6 + t * 1.4 * wf + 1.3) * wobble * 0.22
            const wy = p.y + Math.cos(i * 0.85 + t * 1.3 * wf + 0.7) * wobble * 0.22
            if (i === 0) {
              ctx.moveTo(wx, wy)
            } else {
              ctx.lineTo(wx, wy)
            }
          }
          ctx.closePath()
          ctx.stroke()
        }

        if (sparkleEnabled) {
          let pulse =
            0.5 +
            0.5 *
              Math.sin(t * Math.PI * 2 * (cloud.twinkleFreq || sparklePulseHz) + cloud.phase * 1.17)
          pulse += 0.04 * Math.sin(t * 11 + cloud.phase * 1.9) + 0.03 * Math.cos(t * 6.1 + cloud.phase * 1.3)
          pulse = Math.max(0, Math.min(1, pulse))

          if (baseStroke) {
            const [r, g, b] = baseStroke
            const brightR = Math.min(255, Math.round(r * 0.55 + 255 * 0.45))
            const brightG = Math.min(255, Math.round(g * 0.55 + 255 * 0.45))
            const brightB = Math.min(255, Math.round(b * 0.75 + 255 * 0.25))
            const alpha = sparkleOpacity * (0.7 + 0.3 * pulse)
            ctx.strokeStyle = `rgba(${brightR}, ${brightG}, ${brightB}, ${alpha})`
          } else {
            ctx.strokeStyle = strokeColor
          }
          ctx.shadowBlur = sparkleBaseBlur + (sparkleMaxBlur - sparkleBaseBlur) * pulse
          ctx.lineWidth = sparkleStrokeWidth
          ctx.beginPath()
          ctx.moveTo(0, 0)
          ctx.lineTo(0.001, 0)
          ctx.stroke()
        }

        ctx.restore()
      }

      rafRef.current = window.requestAnimationFrame(frame)
    }

    rafRef.current = window.requestAnimationFrame(frame)

    const handleResize = () => resize()
    window.addEventListener('resize', handleResize)

    return () => {
      if (rafRef.current !== null) {
        window.cancelAnimationFrame(rafRef.current)
        rafRef.current = null
      }
      window.removeEventListener('resize', handleResize)
    }
  }, [
    baseSpeed,
    cloudCount,
    collisionImpulse,
    collisionPadding,
    collisionPushRatio,
    glowBlur,
    globalChaos,
    hoverFlipChance,
    hoverNudgeBaseX,
    hoverNudgeBaseY,
    maxRadius,
    maxRightwardRatio,
    minRadius,
    mouseInfluence,
    pointsPerCloud,
    reactToHoverRadius,
    secondaryOpacity,
    secondaryStroke,
    sparkleBaseBlur,
    sparkleEnabled,
    sparkleMaxBlur,
    sparkleOpacity,
    sparklePulseHz,
    sparkleStrokeWidth,
    speedVariance,
    strokeColor,
    strokeWidth,
    verticalDrift,
  ])

  return (
    <canvas
      ref={canvasRef}
      className="glowing-clouds-overlay"
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        width: '100vw',
        height: '100vh',
        background: 'transparent',
        pointerEvents: 'none',
        zIndex,
      }}
    />
  )
}