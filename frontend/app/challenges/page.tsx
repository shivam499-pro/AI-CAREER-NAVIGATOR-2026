'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Navbar from '@/components/Navbar'
import { Button } from '@/components/ui/button'
import { Loader2, Trophy, Calendar, Clock } from 'lucide-react'
import { supabase } from '@/lib/supabase'

interface WeeklyChallenge {
  week_number: number
  year: number
  theme: string
  career_path: string
  questions: string[]
  starts_at: string
  ends_at: string
}

interface LeaderboardEntry {
  rank: number
  user_email: string
  score: number
  completed_at: string
}

export default function ChallengesPage() {
  const router = useRouter()
  
  const [challenge, setChallenge] = useState<WeeklyChallenge | null>(null)
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState<any>(null)
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Get current user
        const { data: { user } } = await supabase.auth.getUser()
        setUser(user)
        
        // Fetch challenge and leaderboard
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        
        const [challengeRes, leaderboardRes] = await Promise.all([
          fetch(`${apiUrl}/api/weekly/current`),
          fetch(`${apiUrl}/api/weekly/leaderboard`)
        ])
        
        if (challengeRes.ok) {
          const data = await challengeRes.json()
          setChallenge(data)
        }
        
        if (leaderboardRes.ok) {
          const data = await leaderboardRes.json()
          setLeaderboard(data)
        }
      } catch (err) {
        console.error('Error fetching data:', err)
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
  }, [])
  
  const handleAcceptChallenge = () => {
    if (challenge) {
      router.push(`/interview?mode=weekly&career_path=${encodeURIComponent(challenge.career_path)}`)
    }
  }
  
  const getDaysRemaining = (endsAt: string) => {
    try {
      const endDate = new Date(endsAt)
      const now = new Date()
      const diff = Math.ceil((endDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
      return diff > 0 ? diff : 0
    } catch {
      return 0
    }
  }
  
  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    } catch {
      return 'N/A'
    }
  }
  
  const getMedalEmoji = (rank: number) => {
    if (rank === 1) return '🥇'
    if (rank === 2) return '🥈'
    if (rank === 3) return '🥉'
    return ''
  }
  
  const isCurrentUser = (email: string) => {
    return user?.email === email
  }
  
  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="flex items-center justify-center min-h-[60vh]">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </div>
    )
  }
  
  const daysRemaining = challenge ? getDaysRemaining(challenge.ends_at) : 0
  
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="max-w-4xl mx-auto p-6">
        {/* SECTION 1: Weekly Challenge Banner */}
        <div className="bg-gradient-to-r from-[#1E3A5F] to-[#6C3FC8] rounded-xl p-8 mb-8 text-white">
          <div className="flex items-center gap-3 mb-4">
            <Trophy className="w-8 h-8" />
            <h1 className="text-3xl font-bold">Weekly Challenge</h1>
          </div>
          
          {challenge && (
            <>
              <div className="flex flex-wrap gap-3 mb-4">
                <span className="bg-white/20 px-3 py-1 rounded-full text-sm">
                  📖 This Week: {challenge.theme}
                </span>
                <span className="bg-white/20 px-3 py-1 rounded-full text-sm">
                  ⏰ Ends in {daysRemaining} day{daysRemaining !== 1 ? 's' : ''}
                </span>
                <span className="bg-white/20 px-3 py-1 rounded-full text-sm">
                  💼 Category: {challenge.career_path}
                </span>
              </div>
              
              <Button 
                onClick={handleAcceptChallenge}
                className="bg-[#FF6B35] hover:bg-[#FF6B35]/90 text-lg px-8 py-3"
              >
                🚀 Accept Weekly Challenge
              </Button>
            </>
          )}
        </div>
        
        {/* SECTION 2: Leaderboard */}
        <div className="bg-card rounded-xl border p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">🏆 This Week's Leaderboard</h2>
          
          {leaderboard.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-3 text-muted-foreground">Rank</th>
                    <th className="text-left py-3 px-3 text-muted-foreground">Player</th>
                    <th className="text-right py-3 px-3 text-muted-foreground">Score</th>
                    <th className="text-right py-3 px-3 text-muted-foreground">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((entry) => (
                    <tr 
                      key={entry.rank} 
                      className={`border-b ${isCurrentUser(entry.user_email) ? 'bg-blue-50 dark:bg-blue-900/20' : ''}`}
                    >
                      <td className="py-3 px-3">
                        <span className="text-lg">{getMedalEmoji(entry.rank)} {entry.rank}</span>
                      </td>
                      <td className="py-3 px-3 font-medium">
                        {entry.user_email}
                        {isCurrentUser(entry.user_email) && (
                          <span className="ml-2 text-xs text-blue-500">(You)</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right font-semibold">{entry.score}/50</td>
                      <td className="py-3 px-3 text-right text-muted-foreground">
                        {formatDate(entry.completed_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">
              No submissions yet. Be the first to complete this week's challenge!
            </p>
          )}
        </div>
        
        {/* SECTION 3: How It Works */}
        <div>
          <h2 className="text-xl font-bold mb-4">How It Works</h2>
          <div className="grid md:grid-cols-3 gap-4">
            <div className="bg-card rounded-xl border p-6 text-center">
              <Calendar className="w-10 h-10 mx-auto mb-3 text-[#6C3FC8]" />
              <h3 className="font-semibold mb-2">New challenge every Monday</h3>
              <p className="text-sm text-muted-foreground">
                A fresh set of questions awaits you at the start of each week.
              </p>
            </div>
            
            <div className="bg-card rounded-xl border p-6 text-center">
              <Clock className="w-10 h-10 mx-auto mb-3 text-[#FF6B35]" />
              <h3 className="font-semibold mb-2">One week to complete</h3>
              <p className="text-sm text-muted-foreground">
                Take your time to prepare and submit your best answers.
              </p>
            </div>
            
            <div className="bg-card rounded-xl border p-6 text-center">
              <Trophy className="w-10 h-10 mx-auto mb-3 text-yellow-500" />
              <h3 className="font-semibold mb-2">Top scorer wins the week</h3>
              <p className="text-sm text-muted-foreground">
                Compete with others and climb the weekly leaderboard!
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}