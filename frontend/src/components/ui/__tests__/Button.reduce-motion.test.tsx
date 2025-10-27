import { render } from '@testing-library/react'
import { afterAll, describe, expect, it, vi } from 'vitest'

const captured: { current: Record<string, unknown> | null } = { current: null }

vi.mock('framer-motion', async () => {
  const React = await import('react')
  const MockMotion = React.forwardRef<HTMLButtonElement, Record<string, unknown>>((props, ref) => {
    captured.current = props
    const { children, ...rest } = props
    return (
      <button ref={ref} {...(rest as Record<string, unknown>)}>
        {children}
      </button>
    )
  })
  MockMotion.displayName = 'MockMotionButton'
  return {
    motion: { button: MockMotion, a: MockMotion },
    useReducedMotion: () => true,
  }
})

import { Button } from '../Button'

describe('Button reduced motion', () => {
  afterAll(() => {
    vi.resetModules()
  })

  it('omits hover animations when prefers-reduced-motion is enabled', () => {
    render(<Button>Test</Button>)
    expect(captured.current?.whileHover).toBeUndefined()
    expect(captured.current?.whileTap).toBeUndefined()
  })
})