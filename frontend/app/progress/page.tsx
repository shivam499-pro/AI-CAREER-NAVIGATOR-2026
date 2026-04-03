'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import Navbar from '@/components/Navbar'
import { Button } from '@/components/ui/button'
import { Loader2, ArrowLeft, TrendingUp, Award, Flame, Target } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface ProgressData {
  sessions: Array<{
    career_path: string
    total_score: number
    created_at: string
  }>
  rank: {
    xp: number
    level: number
    rank_title: string
  }
  streaks: {
    current_streak: number
    longest_streak: number
    total_sessions: number
  }
}

export default function ProgressPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [progressData, setProgressData] = useState<ProgressData | null>(null)

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        router.push('/auth/login')
        return
      }
      await fetchProgressData(user.id)
    }
    checkAuth()
  }, [router])

  const fetchProgressData = async (userId: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/interview/progress/${userId}`)
      if (response.ok) {
        const data = await response.json()
        setProgressData(data)
      }
    } catch (err) {
      console.error('Error fetching progress:', err)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const getChartData = () => {
    if (!progressData?.sessions) return []
    return progressData.sessions.map((session, index) => ({
      name: formatDate(session.created_at),
      score: session.total_score,
      career: session.career_path
    }))
  }

  const getCareerBreakdown = () => {
    if (!progressData?.sessions) return []
    
    const careerScores: Record<string, { total: number; count: number }> = {}
    progressData.sessions.forEach(session => {
      if (!careerScores[session.career_path]) {
        careerScores[session.career_path] = { total: 0, count: 0 }
      }
      careerScores[session.career_path].total += session.total_score
      careerScores[session.career_path].count += 1
    })
    
    return Object.entries(careerScores).map(([career, data]) => ({
      career,
      average: Math.round(data.total / data.count),
      count: data.count
    })).sort((a, b) => b.average - a.average)
  }

  const getNextLevelXP = (level: number) => {
    const levels = [0, 100, 250, 500, 900, 1400, 2000]
    return levels[level] || 2000
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading progress...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="flex items-center gap-4 mb-8">
            <Link href="/interview">
              <Button variant="outline" size="icon">
                <ArrowLeft className="w-4 h-4" />
              </Button>
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-[#1E3A5F]">My Progress</h1>
              <p className="text-muted-foreground">Track your interview performance</p>
            </div>
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-card rounded-xl border p-4 text-center">
              <Flame className="w-8 h-8 mx-auto text-orange-500 mb-2" />
              <div className="text-2xl font-bold text-[#1E3A5F]">
                {progressData?.streaks.current_streak || 0}
              </div>
              <div className="text-sm text-muted-foreground">Current Streak</div>
            </div>
            
            <div className="bg-card rounded-xl border p-4 text-center">
              <Award className="w-8 h-8 mx-auto text-purple-500 mb-2" />
              <div className="text-2xl font-bold text-[#1E3A5F]">
                {progressData?.rank.rank_title || '🌱 Fresher'}
              </div>
              <div className="text-sm text-muted-foreground">Current Rank</div>
            </div>
            
            <div className="bg-card rounded-xl border p-4 text-center">
              <TrendingUp className="w-8 h-8 mx-auto text-blue-500 mb-2" />
              <div className="text-2xl font-bold text-[#1E3A5F]">
                {progressData?.rank.xp || 0}
              </div>
              <div className="text-sm text-muted-foreground">Total XP</div>
            </div>
            
            <div className="bg-card rounded-xl border p-4 text-center">
              <Target className="w-8 h-8 mx-auto text-green-500 mb-2" />
              <div className="text-2xl font-bold text-[#1E3A5F]">
                {progressData?.streaks.total_sessions || 0}
              </div>
              <div className="text-sm text-muted-foreground">Total Sessions</div>
            </div>
          </div>

          {/* Score Trend Chart */}
          <div className="bg-card rounded-xl border p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">Score Trend</h2>
            {progressData?.sessions && progressData.sessions.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={getChartData()}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} stroke="#6b7280" />
                  <YAxis domain={[0, 50]} tick={{ fontSize: 12 }} stroke="#6b7280" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#fff', 
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px'
                    }}
                    formatter={(value: number, name: string, props: any) => [
                      `${value}/50 - ${props.payload.career}`,
                      'Score'
                    ]}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="score" 
                    stroke="url(#gradient)" 
                    strokeWidth={3}
                    dot={{ fill: '#6C3FC8', strokeWidth: 2, r: 6 }}
                    activeDot={{ r: 8 }}
                  />
                  <defs>
                    <linearGradient id="gradient" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#1E3A5F" />
                      <stop offset="100%" stopColor="#6C3FC8" />
                    </linearGradient>
                  </defs>
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                No interview sessions yet. Start practicing to see your progress!
              </div>
            )}
          </div>

          {/* Career Path Breakdown */}
          <div className="bg-card rounded-xl border p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">Career Path Breakdown</h2>
            {getCareerBreakdown().length > 0 ? (
              <div className="space-y-4">
                {getCareerBreakdown().map((item, index) => (
                  <div key={index} className="flex items-center gap-4">
                    <div className="w-40 text-sm font-medium truncate">{item.career}</div>
                    <div className="flex-1">
                      <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-[#1E3A5F] to-[#6C3FC8] rounded-full"
                          style={{ width: `${(item.average / 50) * 100}%` }}
                        />
                      </div>
                    </div>
                    <div className="w-16 text-sm text-right">{item.average}%</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No career path data available yet.
              </div>
            )}
          </div>

          {/* XP Progress */}
          <div className="bg-card rounded-xl border p-6">
            <h2 className="text-xl font-semibold mb-4">XP Progress</h2>
            <div className="text-center mb-4">
              <span className="text-2xl font-bold text-[#1E3A5F]">
                {progressData?.rank.rank_title || '🌱 Fresher'}
              </span>
              <span className="text-muted-foreground"> — Level {progressData?.rank.level || 1}</span>
            </div>
            <div className="mb-2">
              <div className="flex justify-between text-sm text-muted-foreground mb-1">
                <span>{progressData?.rank.xp || 0} XP</span>
                <span>{getNextLevelXP(progressData?.rank.level || 1)} XP</span>
              </div>
              <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
                  style={{ 
                    width: `${Math.min(100, ((progressData?.rank.xp || 0) / getNextLevelXP(progressData?.rank.level || 1)) * 100)}%` 
                  }}
                />
              </div>
            </div>
            <p className="text-sm text-center text-muted-foreground mt-4">
              Keep practicing to earn more XP and level up!
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}