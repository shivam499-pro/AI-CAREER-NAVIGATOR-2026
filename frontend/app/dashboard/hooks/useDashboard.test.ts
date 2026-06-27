import { renderHook, waitFor } from '@testing-library/react'
import { useDashboard } from './useDashboard'
import { supabase } from '@/lib/supabase'
import { dashboardClient } from '@/lib/api/dashboardClient'

jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}))

jest.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getUser: jest.fn(),
      getSession: jest.fn(),
    },
  },
}))

jest.mock('@/lib/api/dashboardClient', () => ({
  dashboardClient: {
    getCareerBrain: jest.fn(),
    getApplicationStats: jest.fn(),
    getAnalysis: jest.fn(),
    getRoadmapProgress: jest.fn(),
  },
}))

import { useRouter } from 'next/navigation'

const mockPush = jest.fn()

const mockBrain = {
  job_readiness_score: 75,
  recommendations: ['Learn Docker'],
  alerts: [],
  streak: 5,
  rank: 'Senior',
  level: 3,
  skill_insights: { strong: ['React'], weak: [], missing: [] },
}

const mockStats = { applied: 5, interview: 2, rejected: 1, offer: 0 }

const mockAnalysis = {
  career_paths: [{ name: 'Full Stack Developer', match_percentage: 85 }],
  experience_level: 'Mid',
  roadmap: { milestones: [{}, {}, {}] },
  skill_gaps: ['Docker', 'K8s'],
}

const mockUser = { id: 'user-1', email: 'test@test.com' }
const mockSession = { access_token: 'token-123' }

function setupValidAuth() {
  ;(supabase.auth.getUser as jest.Mock).mockResolvedValue({
    data: { user: mockUser },
    error: null,
  })
  ;(supabase.auth.getSession as jest.Mock).mockResolvedValue({
    data: { session: mockSession },
  })
}

function setupDefaultClients() {
  ;(dashboardClient.getCareerBrain as jest.Mock).mockResolvedValue(mockBrain)
  ;(dashboardClient.getApplicationStats as jest.Mock).mockResolvedValue(mockStats)
  ;(dashboardClient.getAnalysis as jest.Mock).mockResolvedValue(null)
  ;(dashboardClient.getRoadmapProgress as jest.Mock).mockResolvedValue({})
}

beforeEach(() => {
  jest.clearAllMocks()
  ;(useRouter as jest.Mock).mockReturnValue({ push: mockPush })
  setupDefaultClients()
})

describe('useDashboard', () => {
  test('initial state: loading=true, user=null, brain=null', () => {
    ;(supabase.auth.getUser as jest.Mock).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useDashboard())

    expect(result.current.loading).toBe(true)
    expect(result.current.user).toBeNull()
    expect(result.current.brain).toBeNull()
  })

  test('redirects to /auth/login when no user', async () => {
    ;(supabase.auth.getUser as jest.Mock).mockResolvedValue({
      data: { user: null },
      error: null,
    })

    renderHook(() => useDashboard())

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/auth/login')
    })
  })

  test('redirects when no session token', async () => {
    ;(supabase.auth.getUser as jest.Mock).mockResolvedValue({
      data: { user: mockUser },
      error: null,
    })
    ;(supabase.auth.getSession as jest.Mock).mockResolvedValue({
      data: { session: null },
    })

    renderHook(() => useDashboard())

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/auth/login')
    })
  })

  test('sets user after successful auth', async () => {
    setupValidAuth()

    const { result } = renderHook(() => useDashboard())

    await waitFor(() => {
      expect(result.current.user?.email).toBe('test@test.com')
    })
  })

  test('loads brain data from dashboardClient.getCareerBrain', async () => {
    setupValidAuth()

    const { result } = renderHook(() => useDashboard())

    await waitFor(() => {
      expect(result.current.brain?.job_readiness_score).toBe(75)
    })
  })

  test('loads appStats from dashboardClient.getApplicationStats', async () => {
    setupValidAuth()

    const { result } = renderHook(() => useDashboard())

    await waitFor(() => {
      expect(result.current.appStats.applied).toBe(5)
    })
  })

  test('parses analysisSummary from getAnalysis result', async () => {
    setupValidAuth()
    ;(dashboardClient.getAnalysis as jest.Mock).mockResolvedValue(mockAnalysis)
    ;(dashboardClient.getRoadmapProgress as jest.Mock).mockResolvedValue({})

    const { result } = renderHook(() => useDashboard())

    await waitFor(() => {
      expect(result.current.analysisSummary?.experience_level).toBe('Mid')
    })
    expect(result.current.analysisSummary?.skill_gaps_count).toBe(2)
  })

  test('calls getRoadmapProgress when best_career_path exists', async () => {
    setupValidAuth()
    ;(dashboardClient.getAnalysis as jest.Mock).mockResolvedValue(mockAnalysis)
    ;(dashboardClient.getRoadmapProgress as jest.Mock).mockResolvedValue({
      1: 'completed',
      2: 'pending',
    })

    const { result } = renderHook(() => useDashboard())

    await waitFor(() => {
      expect(result.current.roadmapCompleted).toBe(1)
    })
    expect(dashboardClient.getRoadmapProgress).toHaveBeenCalledWith(
      'token-123',
      'Full Stack Developer'
    )
  })

  test('redirects to /auth/login when dashboardClient calls fail', async () => {
    setupValidAuth()
    ;(dashboardClient.getCareerBrain as jest.Mock).mockRejectedValue(
      new Error('network error')
    )

    const { result } = renderHook(() => useDashboard())

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/auth/login')
    })
    expect(result.current.loading).toBe(false)
  })

  test('brainLoading starts true, becomes false after brain loads', async () => {
    setupValidAuth()

    const { result } = renderHook(() => useDashboard())

    expect(result.current.brainLoading).toBe(true)

    await waitFor(() => {
      expect(result.current.brainLoading).toBe(false)
    })
  })

  test('analysisSummary remains null when getAnalysis returns null', async () => {
    setupValidAuth()
    ;(dashboardClient.getAnalysis as jest.Mock).mockResolvedValue(null)

    const { result } = renderHook(() => useDashboard())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })
    expect(result.current.analysisSummary).toBeNull()
    expect(dashboardClient.getRoadmapProgress).not.toHaveBeenCalled()
  })
})