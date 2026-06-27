
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'

import '@testing-library/jest-dom'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import AnalysisPage from '../page'
// ── Always mock these in every test file ──────────────────────────────────

class MockIntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.IntersectionObserver =
  MockIntersectionObserver as any


jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children }: any) => <div>{children}</div>,
    section: ({ children }: any) => <section>{children}</section>,
    main: ({ children }: any) => <main>{children}</main>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))


jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    back: jest.fn(),
  }),
  usePathname: () => '/analysis',
  useSearchParams: () => new URLSearchParams(),
}))

jest.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: jest.fn().mockResolvedValue({
        data: {
          session: {
            access_token: 'test-token',
            user: {
              id: 'user-123',
              email: 'test@test.com',
            },
          },
        },
      }),
      getUser: jest.fn().mockResolvedValue({
        data: {
          user: {
            id: 'user-123',
            email: 'test@test.com',
          },
        },
      }),
      signOut: jest.fn().mockResolvedValue({}),
    },
    from: jest.fn(() => ({
      select: jest.fn().mockReturnThis(),
      eq: jest.fn().mockReturnThis(),
      single: jest.fn().mockResolvedValue({
        data: null,
        error: null,
      }),
    })),
  },
}))

jest.mock('@/lib/api/analysisClient', () => ({
  analysisClient: {
    checkExisting: jest.fn(),
    startAnalysis: jest.fn(),
    getJobStatus: jest.fn(),
    getFinalAnalysis: jest.fn(),
    getRoadmapProgress: jest.fn(),
    updateMilestone: jest.fn(),
  },
}))

jest.mock('../hooks/useAnalysis', () => ({
  useAnalysis: jest.fn(),
}))
const mockUseAnalysis = require('../hooks/useAnalysis').useAnalysis as jest.Mock

beforeEach(() => {
  global.fetch = jest.fn()
})

afterEach(() => {
  jest.resetAllMocks()
})

const mockAnalysisData = {
  experience_level: 'Advanced',
  strengths: ['React', 'TypeScript'],
  career_paths: [
    {
      name: 'Frontend Architect',
      match_percentage: 95,
      reason: 'Excellent frontend system design skills',
    },
    {
      name: 'Full Stack Engineer',
      match_percentage: 88,
      reason: 'Strong backend and frontend capabilities',
    },
  ],
  skill_gaps: [
    {
      skill: 'System Design',
      importance: 'High',
    },
    {
      skill: 'DevOps',
      importance: 'Medium',
    },
  ],
  roadmap: {
    target_career: 'Frontend Architect',
    duration_months: 6,
    milestones: [
      {
        week: 1,
        title: 'Learn Advanced React Patterns',
      },
      {
        week: 2,
        title: 'Master System Design',
      },
    ],
  },
}

const createMockHookReturn = (overrides = {}) => ({
  loading: false,
  analyzing: false,
  analysis: null,
  selectedPath: '',
  pathDetails: {},
  roadmapProgress: {},
  progressLoading: false,
  error: '',
  milestoneError: '',
  user: {
    id: 'user-123',
  },
  setSelectedPath: jest.fn(),
  runAnalysis: jest.fn(),
  updateMilestone: jest.fn(),
  ...overrides,
})

describe('AnalysisPage', () => {
  test('renders loading state', () => {
    mockUseAnalysis.mockReturnValue(
      createMockHookReturn({
        loading: true,
      })
    )

    render(<AnalysisPage />)

    expect(
      screen.getByText(/loading analysis/i)
    ).toBeInTheDocument()
  })

  test('renders analysis results', () => {
    mockUseAnalysis.mockReturnValue(
      createMockHookReturn({
        loading: false,
        analysis: mockAnalysisData,
      })
    )

    render(<AnalysisPage />)

    expect(
      screen.getAllByText(/advanced/i).length
    ).toBeGreaterThan(0)

    // expect(
    //   screen.getAllByText(/frontend architect/i)
    // ).toBeInTheDocument()
  })

  test('renders error state', async () => {
    mockUseAnalysis.mockReturnValue(
      createMockHookReturn({
        loading: false,
        error: 'Failed to run analysis',
      })
    )

    render(<AnalysisPage />)
    expect(
      await screen.findByText(/failed to run analysis/i)
    ).toBeInTheDocument()
  })

  test('renders run analysis button when no analysis exists', async () => {
    mockUseAnalysis.mockReturnValue(
      createMockHookReturn({
        loading: false,
        analysis: null, 
      })
    )

    render(<AnalysisPage />)
    expect(
      await screen.findByRole('button')
    ).toBeInTheDocument()
  })

  test('renders analyzing progress state', () => {
    mockUseAnalysis.mockReturnValue(
      createMockHookReturn({
        loading: false,
        analyzing: true,
      })
    )

    render(<AnalysisPage />)

    expect(
      screen.getByText(/syncing intelligence/i)
    ).toBeInTheDocument()
  })

  test('run analysis button triggers startAnalysis', async () => {
    const runAnalysis = jest.fn()

    mockUseAnalysis.mockReturnValue(
      createMockHookReturn({
        loading: false,
        analysis: null,
        runAnalysis,
      })
    )

    render(<AnalysisPage />)

    const button = await screen.findAllByRole('button')

    fireEvent.click(button[0])

    expect(runAnalysis).toHaveBeenCalled()
  })

  test('renders career path cards correctly', () => {
    mockUseAnalysis.mockReturnValue(
      createMockHookReturn({
        loading: false,
        analysis: mockAnalysisData,
      })
    )

    render(<AnalysisPage />)

    expect(
      screen.getByText(/frontend architect/i)
    ).toBeInTheDocument()

    expect(
      screen.getByText(/95/i)
    ).toBeInTheDocument()

    expect(
      screen.getByText(/full stack engineer/i)
    ).toBeInTheDocument()
  })

  test('renders skill gaps section', () => {
    mockUseAnalysis.mockReturnValue(
      createMockHookReturn({
        loading: false,
        analysis: mockAnalysisData,
      })
    )

    render(<AnalysisPage />)

    expect(
      screen.getAllByText(/system design/i).length
    ).toBeGreaterThan(0)

    // expect(
    //   screen.getByText(/devops/i)
    // ).toBeInTheDocument()
  })

  test('renders roadmap section', () => {
    mockUseAnalysis.mockReturnValue(
      createMockHookReturn({
        loading: false,
        analysis: mockAnalysisData,
      })
    )

    render(<AnalysisPage />)

    expect(
      screen.getByText(/learn advanced react patterns/i)
    ).toBeInTheDocument()

    expect(
      screen.getByText(/master system design/i)
    ).toBeInTheDocument()
  })
})
