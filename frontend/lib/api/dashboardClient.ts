/**
 * Dashboard API Client (DIP Fix)
 * All fetch calls for the dashboard feature live here.
 * useDashboard and DashboardPage never call fetch directly.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface CareerBrainData {
  job_readiness_score: number
  recommendations: string[]
  alerts: string[]
  streak: number
  rank: string
  level: number
  skill_insights: { strong: string[]; weak: string[]; missing: string[] }
}

export interface AppStats {
  applied: number
  interview: number
  rejected: number
  offer: number
}

export interface ResumeScore {
  overall: number
  breakdown: {
    skills_match: number
    github_activity: number
    leetcode_strength: number
    certifications: number
    resume_quality: number
  }
  summary: string
}

export interface AnalysisSummary {
  experience_level: string
  resume_score: ResumeScore | null
  best_match: { name: string; percentage: number } | null
  roadmap_total: number
  roadmap_completed: number
  skill_gaps_count: number
  best_career_path: string
}

// ─── Private helper ───────────────────────────────────────────────────────────

const h = (token: string): Record<string, string> => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${token}`,
})

// ─── Client ───────────────────────────────────────────────────────────────────

export const dashboardClient = {
  async getCareerBrain(token: string): Promise<CareerBrainData | null> {
    try {
      const res = await fetch(`${API_URL}/api/v1/career-brain`, { headers: h(token) })
      if (!res.ok) return null
      return res.json()
    } catch { return null }
  },

  async getApplicationStats(token: string): Promise<AppStats> {
    try {
      const res = await fetch(`${API_URL}/api/v1/jobs/applications`, { headers: h(token) })
      if (!res.ok) return { applied: 0, interview: 0, rejected: 0, offer: 0 }
      const data = await res.json()
      return data.status_counts || { applied: 0, interview: 0, rejected: 0, offer: 0 }
    } catch { return { applied: 0, interview: 0, rejected: 0, offer: 0 } }
  },

  async getAnalysis(token: string): Promise<any | null> {
    try {
      const res = await fetch(`${API_URL}/api/v1/analysis/`, { headers: h(token) })
      if (!res.ok) return null
      const data = await res.json()
      return (data?.success && data?.data?.analysis) ? data.data.analysis : null
    } catch { return null }
  },

  async getRoadmapProgress(token: string, careerPath: string): Promise<Record<number, string>> {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/roadmap/progress/${encodeURIComponent(careerPath)}`,
        { headers: h(token) }
      )
      if (!res.ok) return {}
      const data = await res.json()
      return data.progress_map || {}
    } catch { return {} }
  },
}