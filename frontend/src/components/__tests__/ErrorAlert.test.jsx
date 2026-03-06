import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import ErrorAlert from '../ErrorAlert'

describe('ErrorAlert', () => {
  it('renders message and callbacks', () => {
    const onRetry = vi.fn()
    const onDismiss = vi.fn()

    render(
      <ErrorAlert
        error="Fehlertext"
        onRetry={onRetry}
        onDismiss={onDismiss}
        variant="inline"
      />
    )

    expect(screen.getByRole('alert').textContent).toContain('Fehlertext')

    fireEvent.click(screen.getByText('Retry'))
    fireEvent.click(screen.getByText('Schliessen'))

    expect(onRetry).toHaveBeenCalledTimes(1)
    expect(onDismiss).toHaveBeenCalledTimes(1)
  })

  it('does not render when no error is provided', () => {
    const { container } = render(<ErrorAlert error={null} />)
    expect(container.firstChild).toBeNull()
  })
})
