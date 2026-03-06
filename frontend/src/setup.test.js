import { afterEach, beforeAll, afterAll } from 'vitest'
import { cleanup } from '@testing-library/react'
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'

const apiUrls = (path) => [path, `http://localhost:5000${path}`]

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// MSW handlers for API mocking
export const handlers = [
  // Health check endpoint
  ...apiUrls('/api/health').map((url) => http.get(url, () => {
    return HttpResponse.json({
      status: 'ok',
      groq_configured: false,
      timestamp: new Date().toISOString(),
    })
  })),

  // Profile endpoint
  ...apiUrls('/api/profile').map((url) => http.get(url, () => {
    return HttpResponse.json({
      user: { id: 1, name: 'Test User' },
      skills: [{ id: 1, name: 'Python', level: 'Fortgeschritten' }],
      goals: [{ id: 1, description: 'Learn AI' }],
      tools: [],
      user_context: [],
      pagination: { page: 1, limit: 20, total: 0, pages: 1 },
    })
  })),

  ...apiUrls('/api/workflow-history').map((url) => http.get(url, () => HttpResponse.json([]))),
  ...apiUrls('/api/recommendation-feedback').map((url) => http.get(url, () => HttpResponse.json({
    items: [],
    pagination: { page: 1, limit: 20, total: 0, pages: 1 },
  }))),
  ...apiUrls('/api/research-sessions').map((url) => http.get(url, () => HttpResponse.json([]))),
  ...apiUrls('/api/telegram/status').map((url) => http.get(url, () => HttpResponse.json({ enabled: false, mode: 'disabled' }))),
  ...apiUrls('/api/user-context').map((url) => http.get(url, () => HttpResponse.json([]))),

  ...apiUrls('/api/system/stats').map((url) => http.get(url, () => HttpResponse.json({
    total_tools: 2,
    total_categories: 2,
    total_workflows: 0,
  }))),

  // Tools endpoint
  ...apiUrls('/api/tools').map((url) => http.get(url, () => {
    return HttpResponse.json({
      items: [
        { id: 1, name: 'VS Code', category: 'Development' },
        { id: 2, name: 'Notion', category: 'Productivity' },
      ],
      total: 2,
      page: 1,
      limit: 20,
      pages: 1,
    })
  })),

  // Categories endpoint
  ...apiUrls('/api/categories').map((url) => http.get(url, () => {
    return HttpResponse.json([
      { category: 'Development', count: 10 },
      { category: 'Productivity', count: 8 },
    ])
  })),

  ...apiUrls('/api/domains').map((url) => http.get(url, () => HttpResponse.json([]))),

  // KPIs endpoint
  ...apiUrls('/api/kpis').map((url) => http.get(url, () => {
    return HttpResponse.json({
      total_tools: 50,
      total_categories: 10,
      avg_rating: 4.2,
    })
  })),

  ...apiUrls('/api/kpis/report').map((url) => http.get(url, () => HttpResponse.json({
    generated_at: new Date().toISOString(),
    days: 30,
    summary: {},
  }))),

  ...apiUrls('/api/kpis/targets').map((url) => http.get(url, () => HttpResponse.json({}))),
  ...apiUrls('/api/kpis/scheduler-status').map((url) => http.get(url, () => HttpResponse.json({ enabled: false }))),
]

// Setup MSW server
export const server = setupServer(...handlers)

// Start server before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))

// Reset handlers after each test
afterEach(() => server.resetHandlers())

// Close server after all tests
afterAll(() => server.close())
