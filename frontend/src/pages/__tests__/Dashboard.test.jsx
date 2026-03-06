import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Dashboard from '../Dashboard'
import { apiClient } from '../../services/apiClient'

function mockGetResponse(endpoint) {
  if (endpoint.startsWith('/api/profile')) {
    return {
      ok: true,
      status: 200,
      data: { user: { name: 'Test User' }, skills: [], goals: [], tools: [], pagination: {} },
    }
  }

  if (endpoint.startsWith('/api/workflow-history')) {
    return { ok: true, status: 200, data: [] }
  }

  if (endpoint.startsWith('/api/categories')) {
    return { ok: true, status: 200, data: [] }
  }

  if (endpoint.startsWith('/api/kpis/report')) {
    return { ok: true, status: 200, data: { generated_at: new Date().toISOString(), days: 30, summary: {} } }
  }

  if (endpoint.startsWith('/api/tools')) {
    return { ok: true, status: 200, data: { items: [] } }
  }

  return { ok: true, status: 200, data: {} }
}

describe('Dashboard cancel/timeout UX', () => {
  beforeEach(() => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (endpoint) => mockGetResponse(endpoint))
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows canceled message when recommendation request is aborted by user', async () => {
    vi.spyOn(apiClient, 'post').mockImplementation((_endpoint, _body, options = {}) => {
      return new Promise((_resolve, reject) => {
        if (options.signal?.aborted) {
          const abortError = new Error('Aborted')
          abortError.name = 'AbortError'
          reject(abortError)
          return
        }

        options.signal?.addEventListener(
          'abort',
          () => {
            const abortError = new Error('Aborted')
            abortError.name = 'AbortError'
            reject(abortError)
          },
          { once: true }
        )
      })
    })

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    )

    fireEvent.change(screen.getByPlaceholderText('Was willst du heute erledigen?'), {
      target: { value: 'Bitte hilf mir bei meiner Recherche.' },
    })

    fireEvent.click(screen.getByRole('button', { name: /Empfehlung anfordern/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Abbrechen' })).toBeTruthy()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }))

    await waitFor(() => {
      const alert = screen.getByRole('alert')
      expect(alert.textContent).toContain('Empfehlungsanfrage wurde abgebrochen.')
    })
  })

  it('shows timeout error message when recommendation request times out', async () => {
    vi.spyOn(apiClient, 'post').mockResolvedValue({
      ok: false,
      status: 0,
      data: null,
      error: {
        code: 'TIMEOUT',
        message: 'Request timed out',
        details: {},
      },
    })

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    )

    fireEvent.change(screen.getByPlaceholderText('Was willst du heute erledigen?'), {
      target: { value: 'Ich brauche eine Empfehlung.' },
    })

    fireEvent.click(screen.getByRole('button', { name: /Empfehlung anfordern/i }))

    await waitFor(() => {
      const alert = screen.getByRole('alert')
      expect(alert.textContent).toContain('Zeitüberschreitung bei der Anfrage. Bitte erneut versuchen.')
    })
  })
})
