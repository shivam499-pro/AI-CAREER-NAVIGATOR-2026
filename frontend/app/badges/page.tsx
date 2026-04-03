'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import Navbar from '@/components/Navbar'

interface Badge {
  id?: string
  badge_id: string
  name: string
  emoji: string
  description: string
  earned_at?: string
}

interface BadgeResponse {
  earned: Badge[]
  all_badges: Badge[]
}

export default function BadgesPage() {
  const [badges, setBadges] = useState<BadgeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [userId, setUserId] = useState<string | null>(null)

  useEffect(() => {
    async function fetchBadges() {
      const { data: { user } } = await supabase.auth.getUser()
      
      if (!user) {
        setLoading(false)
        return
      }

      setUserId(user.id)

      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/badges/${user.id}`
        )
        const data = await response.json()
        setBadges(data)
      } catch (error) {
        console.error('Error fetching badges:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchBadges()
  }, [])

  const earnedIds = new Set(badges?.earned.map(b => b.badge_id) || [])
  const earnedBadges = badges?.earned || []
  const lockedBadges = (badges?.all_badges || []).filter(b => !earnedIds.has(b.badge_id))

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900">
        <Navbar />
        <div className="flex items-center justify-center h-[calc(100vh-64px)]">
          <div className="text-white text-xl">Loading badges...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900">
      <Navbar />
      
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-2">🏅 Your Achievements</h1>
          <p className="text-xl text-gray-400">
            {earnedBadges.length} / {badges?.all_badges.length || 12} badges earned
          </p>
        </div>

        {/* Earned Badges */}
        {earnedBadges.length > 0 && (
          <div className="mb-12">
            <h2 className="text-2xl font-semibold text-white mb-6">Earned Badges</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {earnedBadges.map((badge) => (
                <div
                  key={badge.badge_id}
                  className="bg-gradient-to-br from-[#6C3FC8] to-[#4A2F8A] rounded-xl p-6 text-center shadow-lg border border-purple-500/30"
                >
                  <div className="text-5xl mb-3">{badge.emoji}</div>
                  <h3 className="text-lg font-bold text-white mb-2">{badge.name}</h3>
                  <p className="text-sm text-purple-200 mb-3">{badge.description}</p>
                  <p className="text-xs text-green-400">
                    Earned on: {formatDate(badge.earned_at)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Locked Badges */}
        {lockedBadges.length > 0 && (
          <div>
            <h2 className="text-2xl font-semibold text-white mb-6">Locked Badges</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {lockedBadges.map((badge) => (
                <div
                  key={badge.badge_id}
                  className="bg-gray-800/50 rounded-xl p-6 text-center border border-gray-700"
                >
                  <div className="text-5xl mb-3 opacity-40 grayscale">{badge.emoji}</div>
                  <h3 className="text-lg font-medium text-gray-500 mb-2">{badge.name}</h3>
                  <p className="text-sm text-gray-600 mb-3">{badge.description}</p>
                  <p className="text-xs text-gray-500">🔒 Locked</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* No badges yet */}
        {earnedBadges.length === 0 && (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">🎖️</div>
            <h3 className="text-xl text-gray-400 mb-2">No badges earned yet</h3>
            <p className="text-gray-500">Complete interview sessions to earn your first badge!</p>
          </div>
        )}
      </div>
    </div>
  )
}