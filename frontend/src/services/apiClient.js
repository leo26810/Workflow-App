const DEFAULT_TIMEOUT_MS = 5000
const RETRY_BACKOFF_BASE_MS = 300

export class ApiClientError extends Error {
  constructor(message, meta = {}) {
    super(message)
    this.name = 'ApiClientError'
    this.code = meta.code || 'UNKNOWN'
    this.status = meta.status || 0
    this.endpoint = meta.endpoint || ''
    this.statusText = meta.statusText || ''
    this.details = meta.details || {}
  }
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function mergeSignals(externalSignal, internalController) {
  if (!externalSignal) return
  if (externalSignal.aborted) {
    internalController.abort()
    return
  }
  externalSignal.addEventListener('abort', () => internalController.abort(), { once: true })
}

function toErrorCode(status, timeoutTriggered) {
  if (timeoutTriggered) return 'TIMEOUT'
  if (status >= 500) return 'HTTP_5XX'
  if (status >= 400) return 'HTTP_4XX'
  return 'NETWORK'
}

function shouldRetry(method, status, timeoutTriggered, isNetworkError, attempt, maxRetries) {
  if (attempt >= maxRetries) return false

  const upper = method.toUpperCase()
  if (upper === 'GET') {
    if (status >= 500) return true
    if (timeoutTriggered) return true
    if (isNetworkError) return true
    return false
  }

  if (timeoutTriggered || isNetworkError) {
    return true
  }

  return false
}

async function readResponseData(response) {
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return response.json()
  }
  return response.text()
}

async function request(method, endpoint, options = {}) {
  const {
    body,
    headers,
    signal,
    timeout = DEFAULT_TIMEOUT_MS,
    retries = method.toUpperCase() === 'GET' ? 2 : 1,
  } = options

  let attempt = 0

  while (attempt <= retries) {
    const controller = new AbortController()
    mergeSignals(signal, controller)

    const timeoutId = setTimeout(() => controller.abort(), timeout)
    let timeoutTriggered = false

    try {
      const response = await fetch(endpoint, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...(headers || {}),
        },
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      })

      clearTimeout(timeoutId)
      const data = await readResponseData(response)

      if (response.ok) {
        return {
          ok: true,
          status: response.status,
          data,
          error: null,
        }
      }

      const errorCode = toErrorCode(response.status, false)
      const error = {
        code: errorCode,
        message: `Request failed with status ${response.status}`,
        endpoint,
        statusText: response.statusText,
        details: {
          retry_count: attempt,
          timeout_ms: timeout,
          response_data: data,
        },
      }

      if (!shouldRetry(method, response.status, false, false, attempt, retries)) {
        return {
          ok: false,
          status: response.status,
          data: null,
          error,
        }
      }
    } catch (err) {
      clearTimeout(timeoutId)
      timeoutTriggered = err?.name === 'AbortError'
      const isNetworkError = !timeoutTriggered
      const errorCode = toErrorCode(0, timeoutTriggered)

      const error = {
        code: errorCode,
        message: timeoutTriggered ? 'Request timed out' : (err?.message || 'Network request failed'),
        endpoint,
        statusText: '',
        details: {
          retry_count: attempt,
          timeout_ms: timeout,
          original_error: err?.message || String(err),
        },
      }

      if (!shouldRetry(method, 0, timeoutTriggered, isNetworkError, attempt, retries)) {
        return {
          ok: false,
          status: 0,
          data: null,
          error,
        }
      }
    }

    const backoff = Math.round(RETRY_BACKOFF_BASE_MS * Math.pow(1.5, attempt))
    await delay(backoff)
    attempt += 1
  }

  return {
    ok: false,
    status: 0,
    data: null,
    error: {
      code: 'RETRY_EXHAUSTED',
      message: 'Request retries exhausted',
      endpoint,
      statusText: '',
      details: {},
    },
  }
}

export const apiClient = {
  get(endpoint, options = {}) {
    return request('GET', endpoint, options)
  },
  post(endpoint, body, options = {}) {
    return request('POST', endpoint, { ...options, body })
  },
  put(endpoint, body, options = {}) {
    return request('PUT', endpoint, { ...options, body })
  },
  delete(endpoint, options = {}) {
    return request('DELETE', endpoint, options)
  },
}

export const apiDefaults = {
  timeoutMs: DEFAULT_TIMEOUT_MS,
  backoffMs: RETRY_BACKOFF_BASE_MS,
}
