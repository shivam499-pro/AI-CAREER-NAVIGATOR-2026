/**
 * analysis/error.test.tsx
 * Place at: frontend/app/analysis/__tests__/analysis.error.test.tsx
 *
 * Root cause of prior failure:
 *   File was placed at app/analysis/__tests__/analysis.error.test.tsx but
 *   the import used '../../../app/analysis/error' which resolves to nothing
 *   from that location.
 *   Fixed: import path is now '../error' (one level up from __tests__/).
 */

import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'

// ── Mocks ─────────────────────────────────────────────────────────────────────

jest.mock('next/link', () =>
  function MockLink({ href, children }: { href: string; children: React.ReactNode }) {
    return <a href={href}>{children}</a>
  }
)

jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, ...rest }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button onClick={onClick} {...rest}>{children}</button>
  ),
}))

jest.mock('lucide-react', () => ({
  AlertTriangle: () => <span data-testid="icon-alert" />,
  RefreshCw:     () => <span data-testid="icon-refresh" />,
  Home:          () => <span data-testid="icon-home" />,
}))

// ── Import after mocks ────────────────────────────────────────────────────────

import AnalysisError from '../error'

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeError(message = 'Something broke', digest?: string): Error & { digest?: string } {
  const err = new Error(message) as Error & { digest?: string }
  if (digest !== undefined) err.digest = digest
  return err
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('AnalysisError boundary', () => {
  let consoleErrorSpy: jest.SpyInstance

  beforeEach(() => {
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    consoleErrorSpy.mockRestore()
  })

  // ── Logging behaviour ──────────────────────────────────────────────────────

  it('logs the error to console.error on mount', () => {
    const error = makeError('network failure')
    render(<AnalysisError error={error} reset={jest.fn()} />)
    expect(consoleErrorSpy).toHaveBeenCalledWith('Analysis error:', error)
  })

  it('re-logs when the error prop changes', () => {
    const error1 = makeError('first error')
    const error2 = makeError('second error')
    const reset = jest.fn()

    const { rerender } = render(<AnalysisError error={error1} reset={reset} />)
    expect(consoleErrorSpy).toHaveBeenCalledWith('Analysis error:', error1)

    rerender(<AnalysisError error={error2} reset={reset} />)
    expect(consoleErrorSpy).toHaveBeenCalledWith('Analysis error:', error2)
    expect(consoleErrorSpy).toHaveBeenCalledTimes(2)
  })

  // ── Static UI ─────────────────────────────────────────────────────────────

  it('renders the "Analysis Failed" heading', () => {
    render(<AnalysisError error={makeError()} reset={jest.fn()} />)
    expect(screen.getByRole('heading', { name: /analysis failed/i })).toBeInTheDocument()
  })

  it('renders the AlertTriangle icon', () => {
    render(<AnalysisError error={makeError()} reset={jest.fn()} />)
    expect(screen.getByTestId('icon-alert')).toBeInTheDocument()
  })

  it('renders a helpful description mentioning the AI service', () => {
    render(<AnalysisError error={makeError()} reset={jest.fn()} />)
    expect(screen.getByText(/temporary issue with our ai service/i)).toBeInTheDocument()
  })

  // ── Reset / CTA behaviour ─────────────────────────────────────────────────

  it('calls reset() when "Try Again" is clicked', () => {
    const reset = jest.fn()
    render(<AnalysisError error={makeError()} reset={reset} />)
    fireEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(reset).toHaveBeenCalledTimes(1)
  })

  it('does not call reset on initial render', () => {
    const reset = jest.fn()
    render(<AnalysisError error={makeError()} reset={reset} />)
    expect(reset).not.toHaveBeenCalled()
  })

  it('renders the "Back to Dashboard" link pointing to /dashboard', () => {
    render(<AnalysisError error={makeError()} reset={jest.fn()} />)
    expect(screen.getByRole('link', { name: /back to dashboard/i }))
      .toHaveAttribute('href', '/dashboard')
  })

  // ── Error digest (conditional branch) ─────────────────────────────────────

  it('displays the error digest when provided', () => {
    const error = makeError('boom', 'abc-123-xyz')
    render(<AnalysisError error={error} reset={jest.fn()} />)
    expect(screen.getByText(/error id: abc-123-xyz/i)).toBeInTheDocument()
  })

  it('does not render the digest line when digest is undefined', () => {
    const error = makeError('no digest')
    render(<AnalysisError error={error} reset={jest.fn()} />)
    expect(screen.queryByText(/error id:/i)).not.toBeInTheDocument()
  })

  // ── Raw error message not leaked ───────────────────────────────────────────

  it('does not render the raw error message in the UI', () => {
    const sensitiveMsg = 'SENSITIVE_INTERNAL_STACK_TRACE_XYZ'
    render(<AnalysisError error={makeError(sensitiveMsg)} reset={jest.fn()} />)
    expect(screen.queryByText(sensitiveMsg)).not.toBeInTheDocument()
  })
})