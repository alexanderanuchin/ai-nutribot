import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import { QuantityStepper } from '../QuantityStepper'

describe('QuantityStepper', () => {
  it('calls onChange when incrementing and decrementing', async () => {
    const user = userEvent.setup()
    const handleChange = vi.fn()

    render(<QuantityStepper value={2} onChange={handleChange} />)

    await user.click(screen.getByLabelText('Увеличить количество'))
    expect(handleChange).toHaveBeenCalledWith(3)

    await user.click(screen.getByLabelText('Уменьшить количество'))
    expect(handleChange).toHaveBeenCalledWith(1)
  })

  it('disables buttons when disabled prop is set', async () => {
    const user = userEvent.setup()
    const handleChange = vi.fn()

    render(<QuantityStepper value={1} onChange={handleChange} disabled />)

    await user.click(screen.getByLabelText('Увеличить количество'))
    await user.click(screen.getByLabelText('Уменьшить количество'))

    expect(handleChange).not.toHaveBeenCalled()
  })
})