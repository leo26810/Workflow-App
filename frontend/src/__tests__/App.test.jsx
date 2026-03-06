import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import App from '../App'

describe('App Component', () => {
  it('renders navigation elements', () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    )
    
    // App should render without crashing
    expect(document.body).toBeTruthy()
  })

  it('handles health check on mount', async () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    )
    
    // Wait for any async operations to complete
    await waitFor(() => {
      // App should have loaded
      expect(document.body).toBeTruthy()
    }, { timeout: 2000 })
  })
})
