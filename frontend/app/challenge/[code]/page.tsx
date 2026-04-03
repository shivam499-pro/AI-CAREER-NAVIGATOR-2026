'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import Navbar from '@/components/Navbar'
import { Button } from '@/components/ui/button'
import { Loader2 } from 'lucide-react'

interface Challenge {
  challenge_code: string
  career_path: string
  questions: string[]
  creator_name?: string
}

interface LeaderboardEntry {
  rank: number
  user_name: string
  score: number
  completed_at: string
}

export default function ChallengePage() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  
  const code = params.code as string
  const [challenge, setChallenge] = useState<Challenge | null>(null)
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)
  const [userScore, setUserScore] = useState<number | null>(null)
  
  // Check if user came from completing a challenge
  const challengeScore = searchParams.get('score')
  
  useEffect(() => {
    if (challengeScore) {
      setSubmitted(true)
      setUserScore(parseInt(challengeScore))
    }
  }, [challengeScore])
  
  // Fetch challenge data
  useEffect(() => {
    const fetchChallenge = async () => {
      try {
        setLoading(true)
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(`${apiUrl}/api/challenges/${code}`)
        
        if (!response.ok) {
          if (response.status === 404) {
            setError('This challenge doesn\'t exist or has expired')
            return
          }
          throw new Error('Failed to fetch challenge')
        }
        
        const data = await response.json()
        setChallenge(data)
        
        // Fetch leaderboard
        const leaderboardResponse = await fetch(`${apiUrl}/api/challenges/leaderboard/${code}`)
        if (leaderboardResponse.ok) {
          const leaderboardData = await leaderboardResponse.json()
          setLeaderboard(leaderboardData)
        }
      } catch (err) {
        setError('This challenge doesn\'t exist or has expired')
      } finally {
        setLoading(false)
      }
    }
    
    if (code) {
      fetchChallenge()
    }
  }, [code])
  
  const handleAcceptChallenge = () => {
    if (challenge) {
      router.push(`/interview?challenge=${code}&career_path=${encodeURIComponent(challenge.career_path)}`)
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
  
  if (error) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <div className="max-w-md mx-auto mt-20 p-6 text-center">
          <h1 className="text-2xl font-bold text-red-500 mb-4">⚠️ Challenge Not Found</h1>
          <p className="text-muted-foreground">{error}</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="max-w-2xl mx-auto p-6">
        {/* Challenge Info */}
        <div className="bg-card rounded-xl border p-6 mb-6">
          <h1 className="text-3xl font-bold text-center mb-4">
            🤜 You've been challenged!
          </h1>
          
          {challenge?.creator_name && (
            <p className="text-center text-muted-foreground mb-4">
              {challenge.creator_name} challenged you!
            </p>
          )}
          
          <div className="bg-muted rounded-lg p-4 mb-4">
            <p className="text-sm text-muted-foreground">Career Path</p>
            <p className="text-lg font-semibold">{challenge?.career_path}</p>
          </div>
          
          <p className="text-center text-muted-foreground mb-6">
            Can you beat their score? Accept the challenge and find out!
          </p>
          
          {!submitted ? (
            <div className="text-center">
              <Button 
                onClick={handleAcceptChallenge}
                className="bg-[#FF6B35] hover:bg-[#FF6B35]/90 text-lg px-8 py-3"
              >
                ⚡ Accept Challenge
              </Button>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-green-500 font-semibold text-lg mb-2">
                🎉 You completed the challenge!
              </p>
              {userScore !== null && (
                <p className="text-muted-foreground">
                  Your Score: {userScore}/50
                </p>
              )}
            </div>
          )}
        </div>
        
        {/* Leaderboard */}
        {leaderboard.length > 0 && (
          <div className="bg-card rounded-xl border p-6">
            <h2 className="text-xl font-bold text-center mb-4">🏆 Leaderboard</h2>
            
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-2 text-muted-foreground">Rank</th>
                    <th className="text-left py-3 px-2 text-muted-foreground">Name</th>
                    <th className="text-right py-3 px-2 text-muted-foreground">Score</th>
                    <th className="text-right py-3 px-2 text-muted-foreground">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((entry) => (
                    <tr key={entry.rank} className="border-b">
                      <td className="py-3 px-2">
                        <span className="text-lg">{getMedalEmoji(entry.rank)} {entry.rank}</span>
                      </td>
                      <td className="py-3 px-2 font-medium">{entry.user_name}</td>
                      <td className="py-3 px-2 text-right font-semibold">{entry.score}/50</td>
                      <td className="py-3 px-2 text-right text-muted-foreground">
                        {formatDate(entry.completed_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        
        {/* Questions Preview */}
        {challenge?.questions && challenge.questions.length > 0 && (
          <div className="bg-card rounded-xl border p-6 mt-6">
            <h3 className="font-semibold mb-3">📝 Questions to Answer ({challenge.questions.length})</h3>
            <ul className="space-y-2">
              {challenge.questions.slice(0, 3).map((q, i) => (
                <li key={i} className="text-sm text-muted-foreground">
                  Q{i + 1}: {q.substring(0, 80)}...
                </li>
              ))}
              {challenge.questions.length > 3 && (
                <li className="text-sm text-muted-foreground">
                  +{challenge.questions.length - 3} more questions
                </li>
              )}
            </ul>
          </div>
        )}
      </main>
    </div>
  )
}