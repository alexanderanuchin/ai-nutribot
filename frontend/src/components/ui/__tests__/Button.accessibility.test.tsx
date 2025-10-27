import { render } from '@testing-library/react'
import { axe } from 'vitest-axe'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const capturedClassNames: string[] = []

vi.mock('framer-motion', async () => {
  const React = await import('react')
  const MockMotion = React.forwardRef<HTMLButtonElement, Record<string, unknown>>((props, ref) => {
    const { children, className, whileHover, whileTap, transition, ...rest } = props
    capturedClassNames.push(typeof className === 'string' ? className : '')
    return (
      <button ref={ref} className={className as string} {...(rest as Record<string, unknown>)}>
        {children}
      </button>
    )
  })
  MockMotion.displayName = 'MockMotionButton'
  return {
    motion: { button: MockMotion, a: MockMotion },
    useReducedMotion: () => false,
  }
})

import { Button, type ButtonVariant } from '../Button'

const VARIANT_CASES: Array<[ButtonVariant, string | null]> = [
  ['primary', 'shadow-level-2'],
  ['secondary', 'shadow-level-1'],
  ['outline', null],
  ['ghost', null],
  ['success', 'shadow-level-2'],
  ['destructive', 'shadow-level-2'],
]

describe('Button design tokens', () => {
  beforeEach(() => {
    capturedClassNames.length = 0
  })

  afterEach(() => {
    capturedClassNames.length = 0
  })

  for (const [variant, expectedShadow] of VARIANT_CASES) {
    it(`applies token-aware ring and shadow for ${variant} variant`, () => {
      const { getByRole } = render(<Button variant={variant}>Action</Button>)
      const className = capturedClassNames.at(-1) ?? ''
      getByRole('button')
      expect(className).toContain('focus-visible:ring-ring')
      if (expectedShadow) {
        expect(className).toContain(expectedShadow)
      } else {
        expect(className).not.toContain('shadow-level-')
      }
    })
  }

  it('has no axe violations in default state', async () => {
    const { container } = render(<Button>Primary action</Button>)
    const results = await axe(container)
    expect(results.violations).toHaveLength(0)
  })

  it('has no axe violations when loading', async () => {
    const { container } = render(<Button loading>Loading action</Button>)
    const results = await axe(container)
    expect(results.violations).toHaveLength(0)
  })
})
