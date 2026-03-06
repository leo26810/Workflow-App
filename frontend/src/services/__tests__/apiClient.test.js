import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '../apiClient'

function mockJsonResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: String(status),
    headers: {
      get: () => 'application/json',
    },
    json: async () => payload,
    text: async () => JSON.stringify(payload),
  }
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('apiClient', () => {
  it('returns ok response payload for successful GET', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue(mockJsonResponse(200, { status: 'ok' }))

    const result = await apiClient.get('/api/health', { retries: 0 })

    expect(result.ok).toBe(true)
    expect(result.status).toBe(200)
    expect(result.data).toEqual({ status: 'ok' })
  })

  it('retries GET on transient network error then succeeds', async () => {
    const fetchMock = vi.spyOn(global, 'fetch')
      .mockRejectedValueOnce(new Error('network down'))
      .mockResolvedValueOnce(mockJsonResponse(200, { value: 1 }))

    const result = await apiClient.get('/api/retry-me', { retries: 2 })

    expect(result.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('does not retry 4xx responses for GET', async () => {
    const fetchMock = vi.spyOn(global, 'fetch').mockResolvedValue(mockJsonResponse(404, { error: 'missing' }))

    const result = await apiClient.get('/api/not-found', { retries: 2 })

    expect(result.ok).toBe(false)
    expect(result.error.code).toBe('HTTP_4XX')
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('marks abort errors as timeout failures', async () => {
    const abortError = new Error('aborted')
    abortError.name = 'AbortError'
    vi.spyOn(global, 'fetch').mockRejectedValue(abortError)

    const result = await apiClient.get('/api/slow', { retries: 0, timeout: 5 })

    expect(result.ok).toBe(false)
    expect(result.error.code).toBe('TIMEOUT')
  })
})
