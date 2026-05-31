/**
 * useBadges Hook
 * Handles all badges data fetching and derived state.
 * BadgesPage never calls fetch or supabase directly.
 */

import { useEffect, useRef, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { badgesClient, Badge, AllBadge, BadgeResponse } from '@/lib/api/badgesClient'
// ─── Types ────────────────────────────────────────────────────────────────────

export interface BadgesState {
  earnedBadges: Badge[]
  lockedBadges: AllBadge[]
  totalBadges: number
  progressPercent: number
  loading: boolean
  error: string | null
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useBadges(): BadgesState {
  const [data, setData] = useState<BadgeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const isMounted = useRef(true)

  useEffect(() => {
    isMounted.current = true

    async function fetchBadges() {
      try {
        const { data: { session } } = await supabase.auth.getSession()

        if (!session?.user) {
          if (isMounted.current) setLoading(false)
          return
        }

        const response = await badgesClient.getBadges(
          session.user.id,
          session.access_token
        )

        if (isMounted.current) setData(response)
      } catch (e) {
        if (isMounted.current) setError('Failed to load badges. Please try again.')
      } finally {
        if (isMounted.current) setLoading(false)
      }
    }

    fetchBadges()

    return () => {
      isMounted.current = false
    }
  }, [])

  // ─── Derived state ──────────────────────────────────────────────────────────

  const earnedBadges = data?.earned ?? []
  const allBadges = data?.all_badges ?? []
  const earnedIds = new Set(earnedBadges.map(b => b.badge_id))
  const lockedBadges = allBadges.filter(b => !earnedIds.has(b.badge_id))
  const totalBadges = allBadges.length
  const progressPercent = totalBadges > 0
    ? (earnedBadges.length / totalBadges) * 100
    : 0

  return {
    earnedBadges,
    lockedBadges,
    totalBadges,
    progressPercent,
    loading,
    error,
  }
}