/**
 * Badges API Client
 * All fetch calls for the badges feature live here.
 * useBadges and BadgesPage never call fetch directly.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Badge {
  badge_id: string
  name: string
  emoji: string
  description: string
  earned_at?: string
}

export interface AllBadge extends Badge {
  id: string // backend spreads {**b, "badge_id": b["id"]} so both exist
}

export interface BadgePagination {
  page: number
  limit: number
  total: number
  total_pages: number
}

export interface BadgeResponse {
  earned: Badge[]
  all_badges: AllBadge[]
  pagination: BadgePagination
}

export interface CheckBadgeResponse {
  newly_earned: Badge[]
}

// ─── Private helper ───────────────────────────────────────────────────────────

const h = (token: string): Record<string, string> => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${token}`,
})

// ─── Client ───────────────────────────────────────────────────────────────────

export const badgesClient = {
  /**
   * Fetch all badges for a user (earned + full catalogue).
   * Uses limit=50 to avoid pagination gaps — backend max is 50.
   */
  async getBadges(userId: string, token: string): Promise<BadgeResponse> {
    const res = await fetch(
      `${API_URL}/api/v1/badges/${userId}?page=1&limit=50`,
      { headers: h(token) }
    )
    if (!res.ok) throw new Error(`Badges fetch failed: ${res.status}`)
    return res.json()
  },

  /**
   * Trigger badge check after a user action.
   * Events: "session_complete" | "perfect_score" | "hard_mode" |
   *         "simulation" | "voice_used" | "challenge_created" | "challenge_won"
   */
  async checkAndAward(
    userId: string,
    token: string,
    event: string
  ): Promise<CheckBadgeResponse> {
    const res = await fetch(`${API_URL}/api/v1/badges/check`, {
      method: 'POST',
      headers: h(token),
      body: JSON.stringify({ user_id: userId, event }),
    })
    if (!res.ok) throw new Error(`Badge check failed: ${res.status}`)
    return res.json()
  },
}