/**
 * Challenges API Client (DIP Fix)
 * All fetch calls for the challenges feature live here.
 * useChallenge and ChallengesPage never call fetch directly.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface WeeklyChallenge {
  week_number: number
  year: number
  theme: string
  career_path: string
  questions: string[]
  starts_at: string
  ends_at: string
}

export interface LeaderboardEntry {
  rank: number
  user_email: string
  score: number
  completed_at: string
}

export type AttemptStatus = 'none' | 'started' | 'completed'

const h = (token: string): Record<string, string> => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${token}`,
})

export const challengesClient = {
  async getCurrentChallenge(): Promise<WeeklyChallenge | null> {
    try {
      const res = await fetch(`${API_URL}/api/v1/weekly-challenge/current`)
      if (!res.ok) return null
      return res.json()
    } catch { return null }
  },

  async getLeaderboard(): Promise<LeaderboardEntry[]> {
    try {
      const res = await fetch(`${API_URL}/api/v1/weekly-challenge/leaderboard`)
      if (!res.ok) return []
      return res.json()
    } catch { return [] }
  },

  async getAttemptStatus(
    token: string,
    weekNumber: number,
    year: number
  ): Promise<{ status: string } | null> {
    try {
      const res = await fetch(
        `${API_URL}/api/v1/weekly-challenge/attempt?week_number=${weekNumber}&year=${year}`,
        { headers: h(token) }
      )
      if (!res.ok) return null
      return res.json()
    } catch { return null }
  },

  async startChallenge(
    token: string,
    weekNumber: number,
    year: number
  ): Promise<{ attempt_id?: string } | null> {
    try {
      const res = await fetch(`${API_URL}/api/v1/weekly-challenge/start`, {
        method: 'POST',
        headers: h(token),
        body: JSON.stringify({ week_number: weekNumber, year }),
      })
      if (!res.ok) return null
      return res.json()
    } catch { return null }
  },
}