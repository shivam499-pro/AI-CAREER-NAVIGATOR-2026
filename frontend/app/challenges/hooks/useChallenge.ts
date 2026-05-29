/**
 * useChallenge Hook (SRP Fix)
 * Auth, data loading, and attempt status extracted from ChallengesPage.
 * ChallengesPage keeps only UI concerns: countdown, formatting, rendering.
 */
import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import {
  challengesClient,
  WeeklyChallenge,
  LeaderboardEntry,
  AttemptStatus,
} from '@/lib/api/challengesClient'

export interface UseChallengeReturn {
  user: any
  challenge: WeeklyChallenge | null
  leaderboard: LeaderboardEntry[]
  loading: boolean
  error: string | null
  isStarting: boolean
  attemptStatus: AttemptStatus
  refetch: () => void
  handleAcceptChallenge: () => Promise<void>
}

export function useChallenge(): UseChallengeReturn {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [challenge, setChallenge] = useState<WeeklyChallenge | null>(null)
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [attemptStatus, setAttemptStatus] = useState<AttemptStatus>('none')

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data: { user } } = await supabase.auth.getUser()
      const { data: { session } } = await supabase.auth.getSession()
      const token = session?.access_token

      if (!token) {
        alert('Please log in to start the challenge.')
        setLoading(false)
        return
      }

      setUser(user)

      const [challengeData, freshLeaderboard] = await Promise.all([
        challengesClient.getCurrentChallenge(),
        challengesClient.getLeaderboard(),
      ])

      setChallenge(challengeData)
      setLeaderboard(freshLeaderboard)

      if (user && challengeData) {
        const attempt = await challengesClient.getAttemptStatus(
          token,
          challengeData.week_number,
          challengeData.year
        )

        if (attempt) {
          setAttemptStatus(
            attempt.status === 'completed' ? 'completed' :
            attempt.status === 'started' ? 'started' : 'none'
          )
        } else {
          const inLeaderboard = freshLeaderboard.find(e => e.user_email === user.email)
          setAttemptStatus(inLeaderboard ? 'completed' : 'none')
        }
      }
    } catch (err) {
      console.error('Error fetching data:', err)
      setError('Failed to load challenge data. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const handleAcceptChallenge = useCallback(async () => {
    if (!challenge || !user) return
    setIsStarting(true)

    if (attemptStatus === 'started') {
      router.push(
        `/interview?mode=weekly&week_number=${challenge.week_number}&year=${challenge.year}&career_path=${encodeURIComponent(challenge.career_path)}`
      )
      return
    }

    try {
      const { data: { session } } = await supabase.auth.getSession()
      const token = session?.access_token
      if (!token) { alert('Please log in to start the challenge.'); setIsStarting(false); return }

      const result = await challengesClient.startChallenge(token, challenge.week_number, challenge.year)

      if (result) {
        router.push(
          `/interview?mode=weekly&week_number=${challenge.week_number}&year=${challenge.year}&career_path=${encodeURIComponent(challenge.career_path)}`
        )
      } else {
        alert('Failed to start challenge. Try again.')
        setIsStarting(false)
      }
    } catch (err) {
      console.error('Error starting challenge:', err)
      alert('Failed to start challenge. Try again.')
      setIsStarting(false)
    }
  }, [challenge, user, attemptStatus, router])

  return {
    user, challenge, leaderboard, loading,
    error, isStarting, attemptStatus,
    refetch: fetchData,
    handleAcceptChallenge,
  }
}