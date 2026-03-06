import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import LoadingOverlay from '../LoadingOverlay'

describe('LoadingOverlay', () => {
  it('renders full variant with cancel callback', () => {
    const onCancel = vi.fn()

    render(
      <LoadingOverlay
        isVisible={true}
        message="Bitte warten"
        variant="full"
        onCancel={onCancel}
      />
    )

    expect(screen.getByText('Bitte warten')).toBeTruthy()
    fireEvent.click(screen.getByText('Abbrechen'))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('does not render when not visible', () => {
    const { container } = render(<LoadingOverlay isVisible={false} />)
    expect(container.firstChild).toBeNull()
  })
})
