'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import { 
  Brain, ChevronRight, Loader2, Sparkles, 
  TrendingUp, Target, Code, CheckCircle, XCircle,
  Calendar, ArrowRight
} from 'lucide-react'

interface CareerPath {
  name?: string
  career_name?: string
  title?: string
  match_percentage?: number
  match?: number
  percentage?: number
  reason?: string
  description?: string
  justification?: string
}

interface SkillGap {
  skill?: string
  skill_name?: string
  name?: string
  have?: boolean
  has?: boolean
  owned?: boolean
  priority?: number
  priority_level?: number
  level?: number
  resources?: string[]
}

interface Roadmap {
  target_career: string
  duration_months: number
  milestones: Milestone[]
}

interface Milestone {
  week: number
  title: string
  description: string
  skills: string[]
  deliverable?: string
}

interface AnalysisData {
  experience_level: string
  strengths: string[]
  career_paths: CareerPath[]
  skill_gaps: SkillGap[]
  roadmap: Roadmap
}

export default function AnalysisPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [user, setUser] = useState<{ id: string } | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        router.push('/auth/login')
        return
      }
      setUser(user)
      await checkExistingAnalysis(user.id)
    }
    checkAuth()
  }, [router])

  const checkExistingAnalysis = async (userId: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/analysis/results/${userId}`)
      const data = await response.json()
      
      console.log('API Response (GET /results):', JSON.stringify(data, null, 2))

      if (data.status === 'found') {
        // Extract strengths - filter out error messages
        let strengths = data.strengths || data.analysis?.strengths || []
        if (typeof strengths === 'string') {
          strengths = [strengths]
        }
        // Filter out error messages
        strengths = strengths.filter((s: string) => !s.toLowerCase().includes('error'))
        
        // Extract career paths
        let careerPaths = data.career_paths || data.analysis?.career_paths || []
        if (typeof careerPaths === 'object' && careerPaths.career_paths) {
          careerPaths = careerPaths.career_paths
        }
        
        // Extract skill gaps
        let skillGaps = data.skill_gaps || data.analysis?.skill_gaps || []
        if (typeof skillGaps === 'object' && skillGaps.skill_gaps) {
          skillGaps = skillGaps.skill_gaps
        }
        
        // Extract roadmap
        let roadmap = data.roadmap || data.analysis?.roadmap || { target_career: '', duration_months: 6, milestones: [] }
        
        // Extract experience level
        const experienceLevel = data.experience_level || data.analysis?.experience_level || 'Intermediate'
        
        setAnalysis({
          experience_level: experienceLevel,
          strengths: strengths,
          career_paths: careerPaths,
          skill_gaps: skillGaps,
          roadmap: roadmap,
        })
      } else {
        // No analysis yet, trigger one
        await runAnalysis(userId)
      }
    } catch (err) {
      console.error('Error checking analysis:', err)
      // Try to run analysis anyway
      await runAnalysis(userId)
    } finally {
      setLoading(false)
    }
  }

  const runAnalysis = async (userId: string) => {
    setAnalyzing(true)
    setError('')

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/analysis/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: userId }),
      })

      if (!response.ok) {
        throw new Error('Analysis failed')
      }

      const data = await response.json()

      if (data.status === 'completed') {
        console.log('API Response (POST /start):', JSON.stringify(data, null, 2))
        
        // Extract strengths - filter out error messages
        let strengths = data.analysis?.strengths || data.strengths || []
        if (typeof strengths === 'string') {
          strengths = [strengths]
        }
        // Filter out error messages
        strengths = strengths.filter((s: string) => !s.toLowerCase().includes('error'))
        
        // Extract career paths
        let careerPaths = data.career_paths || []
        if (typeof careerPaths === 'object' && careerPaths.career_paths) {
          careerPaths = careerPaths.career_paths
        }
        
        // Extract skill gaps
        let skillGaps = data.skill_gaps || []
        if (typeof skillGaps === 'object' && skillGaps.skill_gaps) {
          skillGaps = skillGaps.skill_gaps
        }
        
        // Extract roadmap
        const roadmap = data.roadmap || { target_career: '', duration_months: 6, milestones: [] }
        
        // Extract experience level
        const experienceLevel = data.analysis?.experience_level || data.experience_level || 'Intermediate'
        
        setAnalysis({
          experience_level: experienceLevel,
          strengths: strengths,
          career_paths: careerPaths,
          skill_gaps: skillGaps,
          roadmap: roadmap,
        })
      }
    } catch (err) {
      console.error('Analysis error:', err)
      setError('Failed to run analysis. Please try again.')
    } finally {
      setAnalyzing(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  if (analyzing) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 flex items-center justify-center">
        <div className="text-center max-w-md p-8">
          <div className="relative mb-8">
            <div className="w-24 h-24 mx-auto">
              <div className="absolute inset-0 rounded-full border-4 border-primary/20" />
              <div className="absolute inset-0 rounded-full border-4 border-primary border-t-transparent animate-spin" />
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              <Brain className="w-10 h-10 text-primary" />
            </div>
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-2">
            Analyzing Your Profile
          </h2>
          <p className="text-muted-foreground mb-4">
            Our AI is reading your GitHub and LeetCode data...
          </p>
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-center gap-2">
              <CheckCircle className="w-4 h-4 text-success" />
              <span>Fetching GitHub data</span>
            </div>
            <div className="flex items-center justify-center gap-2">
              <CheckCircle className="w-4 h-4 text-success" />
              <span>Fetching LeetCode data</span>
            </div>
            <div className="flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
              <span>Running AI analysis...</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <XCircle className="w-16 h-16 text-error mx-auto mb-4" />
          <h2 className="text-xl font-bold text-foreground mb-2">Analysis Failed</h2>
          <p className="text-muted-foreground mb-4">{error}</p>
          <Button onClick={() => user && runAnalysis(user.id)}>
            Try Again
          </Button>
        </div>
      </div>
    )
  }

  if (!analysis) {
    return null
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center space-x-2">
            <div className="w-10 h-10 rounded-lg gradient-primary flex items-center justify-center">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-primary">AI Career Navigator</span>
          </Link>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Experience Level */}
        <div className="mb-8">
          <div className="bg-gradient-to-r from-primary to-accent-violet rounded-2xl p-8 text-white">
            <div className="flex items-center gap-4 mb-4">
              <Sparkles className="w-8 h-8" />
              <h2 className="text-2xl font-bold">Your Experience Level</h2>
            </div>
            <div className="text-5xl font-bold mb-2">
              {analysis.experience_level}
            </div>
            <p className="text-white/80">
              Based on your GitHub activity and LeetCode performance
            </p>
          </div>
        </div>

        {/* Strengths */}
        <div className="mb-8">
          <h3 className="text-xl font-bold text-foreground mb-4">Your Strengths</h3>
          <div className="flex flex-wrap gap-2">
            {analysis.strengths && analysis.strengths.length > 0 && !analysis.strengths[0]?.toLowerCase().includes('error') ? (
              analysis.strengths.map((strength, i) => (
                <span 
                  key={i}
                  className="px-4 py-2 bg-success/10 text-success rounded-full font-medium"
                >
                  {strength}
                </span>
              ))
            ) : (
              <p className="text-muted-foreground">Analysis pending...</p>
            )}
          </div>
        </div>

        {/* Career Paths */}
        <div className="mb-8">
          <h3 className="text-xl font-bold text-foreground mb-4">Recommended Career Paths</h3>
          {analysis.career_paths && analysis.career_paths.length > 0 ? (
            <div className="grid md:grid-cols-3 gap-4">
              {analysis.career_paths.slice(0, 3).map((path, i) => {
                // Handle different possible field names
                const pathName = path.name || path.career_name || path.title || 'Unknown Career'
                const matchPct = path.match_percentage ?? path.match ?? path.percentage ?? 0
                const reasonTxt = path.reason || path.description || path.justification || ''
                
                return (
                  <div 
                    key={i}
                    className={`bg-card rounded-xl p-6 border-2 ${
                      i === 0 ? 'border-primary' : ''
                    }`}
                  >
                    {i === 0 && (
                      <span className="text-xs font-bold text-primary mb-2 block">BEST MATCH</span>
                    )}
                    <h4 className="font-bold text-foreground mb-2">{pathName}</h4>
                    <div className="text-3xl font-bold text-primary mb-2">
                      {typeof matchPct === 'number' ? `${matchPct}%` : 'N/A'}
                    </div>
                    <p className="text-sm text-muted-foreground">{reasonTxt || 'No reason provided'}</p>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-muted-foreground">Analysis pending...</p>
          )}
        </div>

        {/* Skill Gaps */}
        <div className="mb-8">
          <h3 className="text-xl font-bold text-foreground mb-4">Skill Gap Analysis</h3>
          {analysis.skill_gaps && analysis.skill_gaps.length > 0 ? (
            <div className="bg-card rounded-xl border overflow-hidden">
              {analysis.skill_gaps.slice(0, 8).map((item, i) => {
                // Handle different possible field names
                const skillName = item.skill || item.skill_name || item.name || 'Unknown Skill'
                const hasSkill = item.have ?? item.has ?? item.owned ?? false
                const priorityNum = item.priority ?? item.priority_level ?? item.level ?? null
                
                return (
                  <div 
                    key={i}
                    className="flex items-center justify-between p-4 border-b last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      {hasSkill ? (
                        <CheckCircle className="w-5 h-5 text-success" />
                      ) : (
                        <XCircle className="w-5 h-5 text-warning" />
                      )}
                      <span className="font-medium text-foreground">{skillName}</span>
                    </div>
                    <span className={`text-sm ${hasSkill ? 'text-success' : 'text-warning'}`}>
                      {hasSkill ? 'Have it' : priorityNum !== null ? `Priority #${priorityNum}` : 'Needs work'}
                    </span>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="text-muted-foreground">Analysis pending...</p>
          )}
        </div>

        {/* Roadmap */}
        <div className="mb-8">
          <h3 className="text-xl font-bold text-foreground mb-4">
            Your {analysis.roadmap?.duration_months || 6}-Month Roadmap
          </h3>
          <div className="bg-card rounded-xl border p-6">
            <div className="flex items-center gap-2 mb-6">
              <Calendar className="w-5 h-5 text-primary" />
              <span className="font-semibold text-foreground">
                Target: {analysis.roadmap?.target_career || 'Full Stack Developer'}
              </span>
            </div>
            
            <div className="space-y-4">
              {analysis.roadmap?.milestones?.slice(0, 8).map((milestone, i) => (
                <div key={i} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center text-sm font-bold">
                      {milestone.week}
                    </div>
                    {i < (analysis.roadmap?.milestones?.length || 0) - 1 && (
                      <div className="w-0.5 h-12 bg-gray-200" />
                    )}
                  </div>
                  <div className="flex-1 pb-6">
                    <h4 className="font-semibold text-foreground">{milestone.title}</h4>
                    <p className="text-sm text-muted-foreground">{milestone.description}</p>
                    {milestone.deliverable && (
                      <p className="text-xs text-primary mt-1">
                        → {milestone.deliverable}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Find Jobs CTA */}
        <div className="text-center">
          <Link href="/jobs">
            <Button className="bg-primary hover:bg-primary/90 text-lg px-8 py-6">
              Find Matching Jobs
              <ArrowRight className="ml-2 w-5 h-5" />
            </Button>
          </Link>
        </div>
      </main>
    </div>
  )
}
