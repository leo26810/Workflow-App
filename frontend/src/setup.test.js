import { afterEach, beforeAll, afterAll } from 'vitest'
import { cleanup } from '@testing-library/react'
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// MSW handlers for API mocking
export const handlers = [
  // Health check endpoint
  http.get('http://localhost:5000/api/health', () => {
    return HttpResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
    })
  }),

  // Profile endpoint
  http.get('http://localhost:5000/api/profile', () => {
    return HttpResponse.json({
      user: { id: 1, name: 'Test User' },
      skills: [{ id: 1, name: 'Python', level: 'Fortgeschritten' }],
      goals: [{ id: 1, description: 'Learn AI' }],
    })
  }),

  // Tools endpoint
  http.get('http://localhost:5000/api/tools', () => {
    return HttpResponse.json({
      items: [
        { id: 1, name: 'VS Code', category: 'Development' },
        { id: 2, name: 'Notion', category: 'Productivity' },
      ],
      total: 2,
    })
  }),

  // Categories endpoint
  http.get('http://localhost:5000/api/categories', () => {
    return HttpResponse.json([
      { category: 'Development', count: 10 },
      { category: 'Productivity', count: 8 },
    ])
  }),

  // KPIs endpoint
  http.get('http://localhost:5000/api/kpis', () => {
    return HttpResponse.json({
      total_tools: 50,
      total_categories: 10,
      avg_rating: 4.2,
    })
  }),
]

// Setup MSW server
export const server = setupServer(...handlers)

// Start server before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))

// Reset handlers after each test
afterEach(() => server.resetHandlers())

// Close server after all tests
afterAll(() => server.close())
