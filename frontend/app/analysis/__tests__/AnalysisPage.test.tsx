process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';

import { render, screen, waitFor, act } from '@testing-library/react';
import AnalysisPage from '../page';

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getUser: jest.fn().mockResolvedValue({
        data: { user: { id: 'test-user' } }
      }),
      getSession: jest.fn().mockResolvedValue({
        data: { session: { access_token: 'test-token' } }
      }),
    },
  },
}));

global.fetch = jest.fn();

describe('AnalysisPage polling behavior (Characterization)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('polls until job is complete and transitions through loading -> success states', async () => {
    /**
     * Actual fetch sequence (confirmed via debug logging):
     * 1. GET  /api/v1/analysis/       ← checkExistingAnalysis (may run twice in strict mode)
     * 2. GET  /api/v1/analysis/       ← second call due to React strict mode / useEffect double invoke
     * 3. POST /api/v1/analysis/run    ← runAnalysis starts job
     * 4. GET  /api/v1/analysis/job/.. ← poll 1 (pending)
     * 5. GET  /api/v1/analysis/job/.. ← poll 2 (completed)
     * 6. GET  /api/v1/analysis/       ← fetch final result
     */
    (global.fetch as jest.Mock)
      // 1. First checkExistingAnalysis — no existing analysis
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, data: { exists: false } }),
      })
      // 2. Second checkExistingAnalysis (strict mode double invoke)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, data: { exists: false } }),
      })
      // 3. POST /run — returns job_id
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: { job_id: 'job-123', status: 'pending', message: 'Analysis job created' }
        }),
      })
      // 4. Poll 1 — pending
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: { status: 'pending', id: 'job-123' } }),
      })
      // 5. Poll 2 — completed
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: { status: 'completed', id: 'job-123' } }),
      })
      // 6. Fetch final analysis
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: {
            analysis: {
              analysis: { experience_level: 'Advanced', strengths: [] },
              career_paths: [{ name: 'Architect', match_percentage: 95, reason: 'Great fit' }],
              skill_gaps: [],
              roadmap: { target_career: 'Architect', duration_months: 6, milestones: [] },
            }
          }
        }),
      });

    jest.useFakeTimers();
    render(<AnalysisPage />);

    // Initially loading
    expect(screen.getByText(/Loading analysis/i)).toBeInTheDocument();

    // Trigger checkExistingAnalysis + runAnalysis POST
    await act(async () => {
      jest.advanceTimersByTime(100);
    });

    // Should transition to analyzing state
    await waitFor(() => {
      expect(screen.getByText(/Syncing Intelligence/i)).toBeInTheDocument();
    });

    // Advance 3s for poll 1 (pending)
    await act(async () => {
      jest.advanceTimersByTime(3000);
    });

    // Advance 3s for poll 2 (completed) + fetch final
    await act(async () => {
      jest.advanceTimersByTime(3000);
    });

    // Final state — analysis rendered
    await waitFor(() => {
      expect(screen.getByText('Advanced')).toBeInTheDocument();
      expect(screen.getByText('Architect')).toBeInTheDocument();
    });

    jest.useRealTimers();
  });
});