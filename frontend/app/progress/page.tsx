'use client'

import { useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { supabase } from '@/lib/supabase'
import Navbar from '@/components/Navbar'
import { Button } from '@/components/ui/button'
import { 
  Loader2, ArrowLeft, Flame, Target, 
  Mail, Calendar, Trophy, Zap, ChevronRight, Sparkles,
  BarChart3, LineChart as LineChartIcon, Activity,
  Brain,
  AlertTriangle, TrendingUp, TrendingDown, Minus,
  Rocket, CheckCircle, Lightbulb, MessageSquare, Briefcase,
  Bot
} from 'lucide-react'
import { 
  XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer, Area, AreaChart
} from 'recharts'

// STEP 3: Use unified career-safe layer
import { 
  safeNumber, 
  safeString, 
  safeArray,
  safeProgress,
  safeEvolution,
  fetchCareerIntelligence,
  CareerLoadingState,
  isLoading,
  isReady,
  hasError,
  EMPTY_PROGRESS_DATA,
  EMPTY_EVOLUTION_DATA,
  type ProgressData,
  type EvolutionData
} from '@/lib/career-safe'

// STEP 5: Use unified career-orchestrator (single source of truth)
import { 
  getCareerBrain,
  getRecommendations,
  isJobReady,
  getBrainSummary,
  type CareerBrain,
  type Recommendation
} from '@/lib/career-orchestrator'

// ============================================
// PHASE 5: TYPE DEFINITIONS + SAFE HELPERS
// ============================================

interface WeaknessEntry {
  category: string
  avgScore: number
  level: 'Weak' | 'Moderate' | 'Strong'
}

// Safe data accessors - PREVENT NULL CRASHES
function getSafeSessions(sessions: any): any[] {
  return Array.isArray(sessions) ? sessions : []
}
function getSafeNum(val: any, fallback = 0): number {
  return typeof val === 'number' && !isNaN(val) ? val : fallback
}
function getSafeStr(val: any, fallback = '—'): string {
  return typeof val === 'string' && val.trim() ? val : fallback
}
function safeDate(val: any): number {
  const d = new Date(getSafeStr(val))
  return isNaN(d.getTime()) ? 0 : d.getTime()
}

interface InsightResult {
  weaknessMap: WeaknessEntry[]
  trend: 'Improving' | 'Stable' | 'Declining'
  readinessScore: number
  aiSummary: string
}

interface CopilotResult {
  nextAction: string
  roadmap: {
    mustImprove: string[]
    goodToHave: string[]
  }
  jobReadiness: {
    status: 'Not Ready' | 'Almost Ready' | 'Ready'
    confidence: number
  }
  summary: string
}

// Career Copilot AI Decision Layer - Action generator system
function generateCopilotInsights(analysis: InsightResult, sessionCount: number): CopilotResult {
  const { weaknessMap, trend, readinessScore, aiSummary } = analysis
  
  // FEATURE 1: NEXT ACTION ENGINE
  let nextAction: string
  if (readinessScore < 40) {
    nextAction = 'Focus on fundamentals and basics practice. Start with core Data Structures and Algorithms.'
  } else if (readinessScore < 70) {
    nextAction = 'Improve weak areas with consistent structured practice and daily problem-solving.'
  } else {
    nextAction = 'Attempt advanced mock interviews and system design practice to refine performance.'
  }
  
  // Additional action based on trend if improving or declining
  if (trend === 'Declining' && sessionCount >= 3) {
    nextAction = 'Address declining performance. Review fundamentals and schedule more frequent practice.'
  } else if (trend === 'Improving' && readinessScore >= 50) {
    nextAction = 'Maintain momentum. Build on improvements with targeted advanced practice.'
  }
  
  // FEATURE 2: SKILL GAP ROADMAP ENGINE
  const mustImprove: string[] = []
  const goodToHave: string[] = []
  
  weaknessMap.forEach(entry => {
    if (entry.level === 'Weak') {
      mustImprove.push(entry.category)
    } else if (entry.level === 'Moderate') {
      goodToHave.push(entry.category)
    }
  })
  
  // FEATURE 3: JOB READINESS ENGINE
  let jobStatus: 'Not Ready' | 'Almost Ready' | 'Ready'
  let confidence: number
  
  if (readinessScore < 40) {
    jobStatus = 'Not Ready'
    confidence = Math.max(0, readinessScore)
  } else if (readinessScore < 70) {
    jobStatus = 'Almost Ready'
    confidence = Math.min(70, readinessScore + 15)
  } else {
    jobStatus = 'Ready'
    confidence = Math.min(95, readinessScore + (trend === 'Improving' ? 5 : 0))
  }
  
  // Adjust confidence based on trend
  if (trend === 'Improving') {
    confidence = Math.min(100, confidence + 10)
  } else if (trend === 'Declining') {
    confidence = Math.max(0, confidence - 10)
  }
  
  // Require minimum sessions for higher readiness
  if (sessionCount < 5 && jobStatus === 'Ready') {
    jobStatus = 'Almost Ready'
    confidence = Math.min(65, confidence)
  }
  
  // FEATURE 4: CAREER COPILOT SUMMARY
  let summary: string
  const weakCount = weaknessMap.filter(w => w.level === 'Weak').length
  
  if (jobStatus === 'Not Ready' || (trend === 'Declining' && weakCount >= 2)) {
    summary = 'You are not yet job-ready. Focus on structured practice in weak areas and maintain consistency.'
  } else if (jobStatus === 'Almost Ready') {
    if (trend === 'Improving') {
      summary = 'You are improving steadily. Keep building consistency to reach full job-readiness.'
    } else {
      summary = 'You are close to job-readiness. Focus on consistency and fill remaining skill gaps.'
    }
  } else {
    summary = 'Strong performance detected. You are job-ready. Continue practicing to maintain readiness level.'
  }
  
  return {
    nextAction,
    roadmap: { mustImprove, goodToHave },
    jobReadiness: { status: jobStatus, confidence: Math.min(100, Math.max(0, confidence)) },
    summary
  }
}

// AI Intelligence Layer - Analyzes session data to generate career insights
// PHASE 5: Uses safe accessors, no inline logic, debug logging
function generateInsights(sessions: ProgressData['sessions']): InsightResult {
  const safe = getSafeSessions(sessions)
  
  // Debug logging (temporary, easily removable)
  if (typeof window !== 'undefined') {
    console.log('[AI Progress] Sessions:', safe.length)
  }
  
  if (safe.length === 0) {
    return {
      weaknessMap: [],
      trend: 'Stable',
      readinessScore: 0,
      aiSummary: 'Start your first interview to unlock career insights.'
    }
  }

  // FEATURE 1: WEAKNESS DETECTION ENGINE
  const careerScores: Record<string, { total: number; count: number }> = {}
  
  safe.forEach(session => {
    const careerPath = getSafeStr(session?.career_path)
    if (!careerPath) return
    if (!careerScores[careerPath]) {
      careerScores[careerPath] = { total: 0, count: 0 }
    }
    careerScores[careerPath].total += getSafeNum(session?.total_score)
    careerScores[careerPath].count += 1
  })

  const weaknessMap: WeaknessEntry[] = Object.entries(careerScores)
    .filter(([_, data]) => data.count > 0)
    .map(([career, data]) => {
      const avgScore = Math.round((data.total / data.count) * 2) // Convert to 0-100 scale (score is out of 50)
      let level: 'Weak' | 'Moderate' | 'Strong'
      if (avgScore < 40) {
        level = 'Weak'
      } else if (avgScore <= 70) {
        level = 'Moderate'
      } else {
        level = 'Strong'
      }
      return { category: career, avgScore, level }
    })
    .sort((a, b) => a.avgScore - b.avgScore)

  // FEATURE 2: SKILL TREND ANALYSIS
  const sortedSessions = [...safe].sort(
    (a, b) => safeDate(a?.created_at) - safeDate(b?.created_at)
  )
  const midpoint = Math.floor(sortedSessions.length / 2)
  
  const firstHalf = sortedSessions.slice(0, midpoint)
  const secondHalf = sortedSessions.slice(midpoint)
  
  let trend: 'Improving' | 'Stable' | 'Declining' = 'Stable'
  
  if (firstHalf.length > 0 && secondHalf.length > 0) {
    const firstHalfAvg = firstHalf.reduce((sum, s) => sum + getSafeNum(s?.total_score), 0) / firstHalf.length
    const secondHalfAvg = secondHalf.reduce((sum, s) => sum + getSafeNum(s?.total_score), 0) / secondHalf.length
    
    if (secondHalfAvg > firstHalfAvg + 2) {
      trend = 'Improving'
    } else if (secondHalfAvg < firstHalfAvg - 2) {
      trend = 'Declining'
    }
  } else if (safe.length >= 4) {
    const recentSessions = sortedSessions.slice(-2)
    const oldestSessions = sortedSessions.slice(0, 2)
    const recentAvg = recentSessions.reduce((sum, s) => sum + (s.total_score ?? 0), 0) / recentSessions.length
    const oldestAvg = oldestSessions.reduce((sum, s) => sum + (s.total_score ?? 0), 0) / oldestSessions.length
    
    if (recentAvg > oldestAvg + 2) {
      trend = 'Improving'
    } else if (recentAvg < oldestAvg - 2) {
      trend = 'Declining'
    }
  }

  // FEATURE 3: CAREER READINESS SCORE
  // Compute a single score (0-100) using avg score, streak, and consistency
  const avgScoreAll = sessions.reduce((sum, s) => sum + (s.total_score ?? 0), 0) / sessions.length
  const avgScoreNormalized = (avgScoreAll / 50) * 100 // Normalize to 0-100
  
  // Use session count as consistency factor (max at 10 sessions)
  const consistencyFactor = Math.min(sessions.length, 10) * 5 // 0-50 points
  
  // Calculate readiness score with weighted factors
  const readinessScore = Math.round(
    (avgScoreNormalized * 0.5) + // 50% weight on average score
    (consistencyFactor) + // 0-50 points from consistency
    (Math.min(sessions.length, 5) * 2) // Bonus for having 5+ sessions
  )
  // Cap at 100
  const finalReadinessScore = Math.min(100, Math.max(0, readinessScore))

  // Determine label based on score
  let readinessLabel: string
  if (finalReadinessScore < 40) {
    readinessLabel = 'Beginner'
  } else if (finalReadinessScore < 70) {
    readinessLabel = 'Intermediate'
  } else {
    readinessLabel = 'Advanced'
  }

  // FEATURE 4: AI INSIGHT SUMMARY (RULE-BASED)
  // Generate insight based on weaknessMap, trend, and readiness
  let aiSummary: string
  
  if (sessions.length < 3) {
    aiSummary = 'Keep practicing to generate career insights. Complete more interviews to unlock personalized recommendations.'
  } else {
    // Count weak categories
    const weakCategories = weaknessMap.filter(w => w.level === 'Weak')
    const strongCategories = weaknessMap.filter(w => w.level === 'Strong')
    
    if (weakCategories.length >= 2 && trend === 'Declining') {
      aiSummary = `Your performance shows declining results with ${weakCategories.length} areas needing attention. Focus on consistent practice and revisit fundamentals in ${weakCategories[0].category}.`
    } else if (weakCategories.length >= 2) {
      aiSummary = `You have ${weakCategories.length} areas to strengthen: ${weakCategories.map(w => w.category).join(', ')}. Consider focused practice in these categories.`
    } else if (trend === 'Improving' && strongCategories.length >= 2) {
      aiSummary = 'Strong growth detected across multiple categories. Your consistent effort is paying off. Maintain this momentum for best results.'
    } else if (trend === 'Improving') {
      aiSummary = 'You are improving steadily. Keep focusing on regular practice sessions to build on this positive momentum.'
    } else if (trend === 'Declining') {
      aiSummary = 'Your performance is showing a slight decline. Consider revisiting core concepts and scheduling more frequent practice sessions.'
    } else if (sessions.length < 5) {
      aiSummary = 'Your foundation is developing well. Complete more sessions to get accurate trend analysis and personalized recommendations.'
    } else {
      aiSummary = 'Your performance is stable. Focus on consistency and try expanding into new career paths for well-rounded growth.'
    }
  }

  return {
    weaknessMap,
    trend,
    readinessScore: finalReadinessScore,
    aiSummary
  }
}

function SkeletonCard({ delay }: { delay: number }) {
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay }}
      className="bg-[#1E293B] rounded-2xl border border-white/5 p-6 relative overflow-hidden"
    >
      <div className="animate-pulse">
        <div className="w-12 h-12 rounded-xl bg-slate-700/50 mb-4 mx-auto" />
        <div className="h-8 w-20 bg-slate-700/50 rounded mx-auto mb-2" />
        <div className="h-3 w-16 bg-slate-700/30 rounded mx-auto" />
      </div>
    </motion.div>
  )
}

function SkeletonChart() {
  return (
    <div className="h-[300px] w-full bg-[#0F172A]/50 rounded-2xl p-8">
      <div className="animate-pulse space-y-4">
        <div className="flex justify-between items-center">
          <div className="h-6 w-32 bg-slate-700/50 rounded" />
          <div className="h-4 w-24 bg-slate-700/30 rounded" />
        </div>
        <div className="h-[200px] flex items-end gap-2 px-4">
          {[...Array(10)].map((_, i) => (
            <div 
              key={i} 
              className="flex-1 bg-slate-700/30 rounded-t"
              style={{ height: `${Math.random() * 60 + 40}%` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

function SkeletonCareerMatrix() {
  return (
    <div className="bg-[#1E293B] rounded-3xl border border-white/5 p-8">
      <div className="h-6 w-40 bg-slate-700/50 rounded mb-6" />
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse">
            <div className="flex justify-between mb-2">
              <div className="h-4 w-24 bg-slate-700/50 rounded" />
              <div className="h-4 w-12 bg-slate-700/30 rounded" />
            </div>
            <div className="h-3 bg-slate-700/30 rounded-full" />
          </div>
        ))}
      </div>
    </div>
  )
}

function SkeletonXPProgress() {
  return (
    <div className="bg-[#1E293B] rounded-3xl border border-white/5 p-8">
      <div className="flex items-center gap-4 mb-8">
        <div className="w-12 h-12 rounded-2xl bg-slate-700/50" />
        <div className="space-y-2">
          <div className="h-6 w-28 bg-slate-700/50 rounded" />
          <div className="h-3 w-20 bg-slate-700/30 rounded" />
        </div>
      </div>
      <div className="animate-pulse space-y-4">
        <div className="h-10 w-32 bg-slate-700/50 rounded mx-auto" />
        <div className="h-4 bg-slate-700/30 rounded-full" />
      </div>
    </div>
  )
}

export default function ProgressPage() {
  const router = useRouter()
  const [loadingState, setLoadingState] = useState<CareerLoadingState>('idle')
  const [retrying, setRetrying] = useState(false)
  // STEP 5: Single source of truth - careerBrain
  const [careerBrain, setCareerBrain] = useState<CareerBrain | null>(null)
  const [userEmail, setUserEmail] = useState('')
  const [sendingReport, setSendingReport] = useState(false)
  const [reportSent, setReportSent] = useState(false)

  // Helper to determine if we have an error state
  const hasErrorState = loadingState === 'error'
  const isLoadingState = loadingState === 'loading'

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        router.push('/auth/login')
        return
      }
      if (user.email) {
        setUserEmail(user.email)
      }
      await fetchProgressData(user.id, false)
    }
    checkAuth()
  }, [router])

  // STEP 5: Use unified getCareerBrain (single source of truth)
  const fetchProgressData = async (userId: string, isRetry: boolean) => {
    if (isRetry) {
      setRetrying(true)
    }
    setLoadingState('loading')
    
    try {
      // Single brain fetch - replaces all scattered logic
      const brain = await getCareerBrain(userId)
      
      // Debug logging
      console.log('[Progress] CareerBrain received:', JSON.stringify({
        totalSessions: brain.totalSessions,
        hasRawProgress: !!brain.raw.progress,
        hasRawEvolution: !!brain.raw.evolution,
        rawProgressSessions: brain.raw.progress?.sessions?.length || 0,
        rawEvolutionPaths: brain.raw.evolution?.career_paths?.length || 0
      }, null, 2))
      
      setCareerBrain(brain)
      
      // Determine if there's an error vs empty state
      // Empty state (new user): have careerBrain but no sessions yet
      // Error state: API failed completely
      const hasNoProgressData = brain.totalSessions === 0
      const hasNoEvolutionData = !brain.raw.evolution?.career_paths?.length
      const isTrulyEmpty = hasNoProgressData && hasNoEvolutionData
      
      // If we have some data OR we got a valid brain response (even empty), it's ready
      if (brain && !isTrulyEmpty) {
        console.log('[Progress] Data found - setting ready state')
        setLoadingState('ready')
      } else if (brain && isTrulyEmpty) {
        // New user with no sessions - this is a VALID empty state, not an error
        console.log('[Progress] Empty state (new user) - setting ready state')
        setLoadingState('ready')
      } else {
        // No brain response at all - this is a real error
        console.log('[Progress] No data found - setting error state')
        setLoadingState('error')
      }
    } catch (err) {
      console.error('Error fetching career brain:', err)
      setLoadingState('error')
    } finally {
      setRetrying(false)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  // Extract progress and evolution data from careerBrain (single source of truth)
  const progressData = careerBrain?.raw?.progress || null
  const careerEvolution = careerBrain?.raw?.evolution || null

  // Debug: Log extracted data
  if (typeof window !== 'undefined' && careerBrain) {
    console.log('[Progress] Extracted progressData:', progressData?.sessions?.length || 0, 'sessions')
    console.log('[Progress] Extracted careerEvolution:', careerEvolution?.career_paths?.length || 0, 'paths')
  }

  const chartData = useMemo(() => {
    if (!progressData?.sessions?.length) return []
    return progressData.sessions
      .filter(session => session.total_score != null && session.total_score !== undefined)
      .map((session) => ({
        name: formatDate(session.created_at),
        score: session.total_score,
        career: session.career_path
      }))
  }, [progressData?.sessions])

  const careerBreakdown = useMemo(() => {
    if (!progressData?.sessions?.length) return []
    
    const careerScores: Record<string, { total: number; count: number }> = {}
    progressData.sessions.forEach(session => {
      if (!session.career_path || session.career_path.trim() === '') return
      if (!careerScores[session.career_path]) {
        careerScores[session.career_path] = { total: 0, count: 0 }
      }
      careerScores[session.career_path].total += (session.total_score ?? 0)
      careerScores[session.career_path].count += 1
    })
    
    return Object.entries(careerScores)
      .filter(([_, data]) => data.count > 0)
      .map(([career, data]) => ({
        career,
        average: Math.round(data.total / data.count),
        count: data.count
      }))
      .sort((a, b) => b.average - a.average)
  }, [progressData?.sessions])

  // AI Intelligence Layer - Compute insights from session data
  const analysis = useMemo(() => {
    return generateInsights(progressData?.sessions || [])
  }, [progressData?.sessions])


  // Career Copilot Layer - Generate action recommendations from analysis
  const copilot = useMemo(() => {
    return generateCopilotInsights(analysis, progressData?.sessions?.length || 0)
  }, [analysis, progressData?.sessions?.length])

  // Career Intelligence Score - Combined metric from readiness, evolution confidence, and trend stability
  const intelligenceScore = useMemo(() => {
    const readiness = analysis.readinessScore
    
    // Get evolution metrics if available
    let evolutionConfidence = 0
    let trendStability = 50 // Default to middle (50%)
    
    if (careerEvolution?.career_paths && careerEvolution.career_paths.length > 0) {
      // Average confidence from all career paths
      evolutionConfidence = (careerEvolution.career_paths.reduce(
        (sum, path) => sum + (path.confidence || 0), 0
      ) / careerEvolution.career_paths.length) * 100
      
      // Overall growth state: growing = 100, stagnating = 50, declining = 0
      const growthState = careerEvolution.overall_growth_state || 'stagnating'
      if (growthState === 'growing') trendStability = 100
      else if (growthState === 'declining') trendStability = 0
      else trendStability = 50
    }
    
    // Weighted average calculation
    const score = Math.round(
      (readiness * 0.4) +
      (evolutionConfidence * 0.35) +
      (trendStability * 0.25)
    )
    
    return Math.min(100, Math.max(0, score))
  }, [analysis.readinessScore, careerEvolution])

  // ============================================
  // TASK 1: CAREER MODE SYSTEM
  // Derive UI mode from readinessScore
  // ============================================
  const careerMode = useMemo(() => {
    if (!progressData) return 'loading'
    
    const score = analysis.readinessScore ?? 0
    
    if (score < 40) return 'foundation'
    if (score < 70) return 'growth'
    return 'job_ready'
  }, [progressData, analysis.readinessScore])

  // ============================================
  // TASK 3: AI NEXT BEST ACTION ENGINE
  // ============================================
  const nextBestAction = useMemo(() => {
    const score = analysis.readinessScore ?? 0
    const growthState = careerEvolution?.overall_growth_state || 'stagnating'
    
    if (score < 40) {
      return 'Focus on fundamentals: Data Structures, Problem Solving'
    }
    
    if (score < 70) {
      return 'Practice mock interviews + improve weak categories'
    }
    
    return 'Apply for internships + advanced interview rounds'
  }, [analysis.readinessScore, careerEvolution])

  // ============================================
  // TASK 5: INTELLIGENCE SCORE LABEL
  // ============================================
  const intelligenceLabel = useMemo(() => {
    switch (careerMode) {
      case 'foundation':
        return 'Building Core Skills'
      case 'growth':
        return 'Improving Consistently'
      case 'job_ready':
        return 'Interview Ready'
      default:
        return 'Analyzing...'
    }
  }, [careerMode])

  const getNextLevelXP = (level: number) => {
    const levels = [0, 100, 250, 500, 900, 1400, 2000]
    return levels[level] || 2000
  }

  const sendWeeklyReport = async () => {
    if (!userEmail) return
    setSendingReport(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const { data: { user } } = await supabase.auth.getUser()
      
      const response = await fetch(`${apiUrl}/api/email/send-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          user_id: user?.id, 
          email: userEmail 
        })
      })
      
      if (response.ok) {
        setReportSent(true)
        setTimeout(() => setReportSent(false), 3000)
      }
    } catch (err) {
      console.error('Error sending report:', err)
    } finally {
      setSendingReport(false)
    }
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  }

  // Loading state with skeleton UI - FIX: use loadingState
  if (loadingState === 'loading' || loadingState === 'idle') {
    return (
      <div className="min-h-screen bg-[#0F172A] text-white">
        <Navbar />
        <main className="container mx-auto px-4 py-8">
          <div className="max-w-5xl mx-auto">
            {/* Header skeleton */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
              <div className="flex items-center gap-6">
                <div className="w-10 h-10 bg-slate-700/50 rounded-xl" />
                <div className="space-y-2">
                  <div className="h-8 w-48 bg-slate-700/50 rounded" />
                  <div className="h-4 w-40 bg-slate-700/30 rounded" />
                </div>
              </div>
            </div>

            {/* Stats row skeleton */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
              <SkeletonCard delay={0} />
              <SkeletonCard delay={0.1} />
              <SkeletonCard delay={0.2} />
              <SkeletonCard delay={0.3} />
            </div>

            {/* Chart skeleton */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="lg:col-span-2">
                <SkeletonChart />
              </div>
              <SkeletonCareerMatrix />
            </div>
          </div>
        </main>
      </div>
    )
  }

  // Error state - FIX: use loadingState
  if (loadingState === 'error') {
    return (
      <div className="min-h-screen bg-[#0F172A] text-white">
        <Navbar />
        <main className="container mx-auto px-4 py-8">
          <div className="max-w-5xl mx-auto">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
              <div className="flex items-center gap-6">
                <Link href="/interview">
                  <Button variant="ghost" className="bg-[#1E293B] border border-white/5 hover:bg-[#334155] rounded-xl p-3 h-auto group transition-all">
                    <ArrowLeft className="w-5 h-5 text-slate-400 group-hover:text-white group-hover:-translate-x-1 transition-transform" />
                  </Button>
                </Link>
                <div>
                  <h1 className="text-4xl font-black tracking-tight text-white flex items-center gap-3">
                    My <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#6C3FC8] to-[#9333EA]">Performance</span>
                  </h1>
                  <div className="flex items-center gap-2 text-slate-400 mt-1">
                    <Activity className="w-4 h-4 text-[#6C3FC8]" />
                    <span className="font-bold text-sm uppercase tracking-widest">Real-time career intelligence</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-center py-20">
              <div className="text-center">
                {retrying ? (
                  <>
                    <Loader2 className="w-12 h-12 animate-spin text-[#6C3FC8] mx-auto mb-4" />
                    <p className="text-slate-400 font-medium">Retrying...</p>
                  </>
                ) : (
                  <>
                    <p className="text-red-400 font-bold text-lg mb-4">We couldn't fetch your progress data</p>
                    <Button 
                      onClick={() => {
                        supabase.auth.getUser().then(({ data: { user } }) => {
                          if (user) fetchProgressData(user.id, true)
                        })
                      }}
                      className="bg-[#6C3FC8] hover:bg-[#6C3FC8]/90 text-white font-black uppercase tracking-tighter text-xs px-6 rounded-xl"
                    >
                      Retry
                    </Button>
                  </>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>
    )
  }

  // Empty state - no interview data yet
  const hasNoData = !progressData || !progressData.sessions || progressData.sessions.length === 0

  // ============================================
  // TASK 2: ADAPTIVE HEADER BANNER
  // Dynamic header based on career mode
  // ============================================
  const renderAdaptiveBanner = () => {
    if (!progressData || hasNoData) return null

    const bannerConfig = {
      foundation: {
        title: 'Foundation Building Phase',
        subtitle: 'Focus on core skills before advanced challenges',
        gradient: 'from-red-600 to-orange-600',
        Icon: AlertTriangle,
        iconColor: 'text-red-400',
        bgGlow: 'bg-red-500/20',
        borderColor: 'border-red-500/30'
      },
      growth: {
        title: 'Skill Growth Phase',
        subtitle: 'You are improving steadily. Keep consistency.',
        gradient: 'from-yellow-500 to-orange-500',
        Icon: TrendingUp,
        iconColor: 'text-yellow-400',
        bgGlow: 'bg-yellow-500/20',
        borderColor: 'border-yellow-500/30'
      },
      job_ready: {
        title: 'Job Ready Phase 🚀',
        subtitle: 'You are ready for real interview opportunities',
        gradient: 'from-green-500 to-emerald-600',
        Icon: Rocket,
        iconColor: 'text-green-400',
        bgGlow: 'bg-green-500/20',
        borderColor: 'border-green-500/30'
      }
    }

    const config = bannerConfig[careerMode as keyof typeof bannerConfig] || bannerConfig.foundation
    const BannerIcon = config.Icon

    return (
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className={`mb-8 p-6 rounded-3xl border ${config.borderColor} bg-gradient-to-r ${config.gradient} relative overflow-hidden`}
      >
        <div className={`absolute -top-20 -right-20 w-64 h-64 ${config.bgGlow} rounded-full blur-[100px]`} />
        <div className="relative z-10 flex items-center gap-4">
          <div className={`p-4 rounded-2xl ${config.bgGlow}`}>
            <BannerIcon className={`w-8 h-8 ${config.iconColor}`} />
          </div>
          <div>
            <h2 className="text-2xl font-black text-white">{config.title}</h2>
            <p className="text-white/80 font-medium">{config.subtitle}</p>
          </div>
        </div>
      </motion.div>
    )
  }


  if (hasNoData) {
    return (
      <div className="min-h-screen bg-[#0F172A] text-white">
        <Navbar />
        <main className="container mx-auto px-4 py-8">
          <div className="max-w-5xl mx-auto">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
              <div className="flex items-center gap-6">
                <Link href="/interview">
                  <Button variant="ghost" className="bg-[#1E293B] border border-white/5 hover:bg-[#334155] rounded-xl p-3 h-auto group transition-all">
                    <ArrowLeft className="w-5 h-5 text-slate-400 group-hover:text-white group-hover:-translate-x-1 transition-transform" />
                  </Button>
                </Link>
                <div>
                  <h1 className="text-4xl font-black tracking-tight text-white flex items-center gap-3">
                    My <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#6C3FC8] to-[#9333EA]">Performance</span>
                  </h1>
                  <div className="flex items-center gap-2 text-slate-400 mt-1">
                    <Activity className="w-4 h-4 text-[#6C3FC8]" />
                    <span className="font-bold text-sm uppercase tracking-widest">Real-time career intelligence</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex flex-col items-center justify-center py-20">
              <h2 className="text-2xl font-black text-white mb-2">You haven't completed any interviews yet.</h2>
              <p className="text-slate-400 font-medium mb-6">Your progress analytics will appear after your first interview.</p>
              <Button 
                onClick={() => router.push('/interview')}
                className="bg-[#6C3FC8] hover:bg-[#6C3FC8]/90 text-white font-black uppercase tracking-tighter text-sm px-8 py-3 rounded-xl"
              >
                Start Interview
              </Button>
            </div>
          </div>
        </main>
      </div>
    )
  }

  // Safe data access with optional chaining
  const currentStreak = progressData?.streaks?.current_streak ?? 0
  const rankTitle = progressData?.rank?.rank_title ?? '—'
  const xp = progressData?.rank?.xp ?? 0
  const level = progressData?.rank?.level ?? 1
  const totalSessions = progressData?.streaks?.total_sessions ?? 0

  // Chart validation - need at least 3 sessions for trends
  const hasEnoughDataForChart = chartData.length >= 3

  return (
    <div className="min-h-screen bg-[#0F172A] text-white">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <motion.div 
          initial="hidden"
          animate="visible"
          variants={containerVariants}
          className="max-w-5xl mx-auto"
        >
          {/* Adaptive Header Banner */}
          {renderAdaptiveBanner()}

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
            <div className="flex items-center gap-6">
              <Link href="/interview">
                <Button variant="ghost" className="bg-[#1E293B] border border-white/5 hover:bg-[#334155] rounded-xl p-3 h-auto group transition-all">
                  <ArrowLeft className="w-5 h-5 text-slate-400 group-hover:text-white group-hover:-translate-x-1 transition-transform" />
                </Button>
              </Link>
              <div>
                <motion.h1 
                  variants={itemVariants}
                  className="text-4xl font-black tracking-tight text-white flex items-center gap-3"
                >
                  My <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#6C3FC8] to-[#9333EA]">Performance</span>
                </motion.h1>
                <div className="flex items-center gap-2 text-slate-400 mt-1">
                  <Activity className="w-4 h-4 text-[#6C3FC8]" />
                  <span className="font-bold text-sm uppercase tracking-widest">Real-time career intelligence</span>
                </div>
              </div>
            </div>
            
            <motion.div variants={itemVariants} className="flex gap-2">
              <div className="bg-[#1E293B] px-4 py-2 rounded-full border border-white/10 flex items-center gap-2">
                <Calendar className="w-4 h-4 text-slate-500" />
                <span className="text-xs font-black uppercase tracking-widest text-slate-300">Updated Today</span>
              </div>
            </motion.div>
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
            {[
              { 
                label: 'Streak', 
                val: currentStreak, 
                icon: Flame, 
                color: 'text-orange-400', 
                bg: 'bg-orange-500/10',
                glow: 'shadow-[0_0_15px_rgba(249,115,22,0.3)]',
                border: 'border-orange-500/20'
              },
              { 
                label: 'Rank', 
                val: rankTitle, 
                icon: Trophy, 
                color: 'text-purple-400', 
                bg: 'bg-purple-500/10',
                glow: 'shadow-[0_0_15px_rgba(108,63,200,0.3)]',
                border: 'border-purple-500/20'
              },
              { 
                label: 'Total XP', 
                val: xp, 
                icon: Zap, 
                color: 'text-yellow-400', 
                bg: 'bg-yellow-500/10',
                glow: 'shadow-[0_0_15px_rgba(234,179,8,0.2)]',
                border: 'border-yellow-500/20'
              },
              {
                label: 'Sessions',
                val: totalSessions,
                icon: Target,
                color: 'text-blue-400',
                bg: 'bg-blue-500/10',
                glow: 'shadow-[0_0_15px_rgba(59,130,246,0.2)]',
                border: 'border-blue-500/20'
              },
              {
                label: 'Intelligence',
                val: intelligenceScore,
                icon: Brain,
                sublabel: intelligenceLabel,
                color: intelligenceScore >= 70 ? 'text-green-400' : intelligenceScore >= 40 ? 'text-yellow-400' : 'text-red-400',
                bg: intelligenceScore >= 70 ? 'bg-green-500/10' : intelligenceScore >= 40 ? 'bg-yellow-500/10' : 'bg-red-500/10',
                glow: intelligenceScore >= 70 ? 'shadow-[0_0_15px_rgba(34,197,94,0.3)]' : intelligenceScore >= 40 ? 'shadow-[0_0_15px_rgba(234,179,8,0.3)]' : 'shadow-[0_0_15px_rgba(239,68,68,0.3)]',
                border: intelligenceScore >= 70 ? 'border-green-500/20' : intelligenceScore >= 40 ? 'border-yellow-500/20' : 'border-red-500/20'
              }
            ].map((stat, i) => (
              <motion.div 
                key={i}
                variants={itemVariants}
                whileHover={{ y: -5 }}
                className={`bg-[#1E293B] rounded-2xl border ${stat.border} p-6 relative overflow-hidden transition-all group`}
              >
                <div className={`absolute top-0 right-0 w-16 h-16 ${stat.bg} rounded-full blur-2xl -translate-y-1/2 translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity`} />
                <div className="relative z-10 flex flex-col items-center">
                  <div className={`p-3 rounded-xl ${stat.bg} ${stat.color} mb-4 ${stat.glow}`}>
                    <stat.icon className="w-6 h-6" />
                  </div>
                  <div className="text-2xl font-black text-white mb-1 group-hover:scale-110 transition-transform">
                    {typeof stat.val === 'number' ? stat.val.toLocaleString() : stat.val}
                  </div>
                  <div className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">{stat.label}</div>
                  {/* Task 5: Intelligence Label - displayed below score */}
                  {(stat as any).sublabel && (
                    <div className="text-[9px] font-medium text-slate-400 mt-1">{(stat as any).sublabel}</div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>

          {/* AI Career Action Engine - NEW TASK 4 */}
          {progressData?.sessions && progressData.sessions.length > 0 && (
            <motion.div
              variants={itemVariants}
              className="bg-gradient-to-r from-cyan-600/20 to-blue-600/20 rounded-3xl border border-cyan-500/30 p-6 mb-8 relative overflow-hidden"
            >
              <div className="absolute -top-10 -right-10 w-32 h-32 bg-cyan-500 opacity-10 rounded-full blur-[60px]" />
              <div className="flex items-center gap-3 mb-4 relative z-10">
                <div className="p-2 rounded-xl bg-cyan-500/20 border border-cyan-500/30">
                  <Zap className="w-5 h-5" />
                </div>
                <h2 className="text-lg font-black uppercase tracking-widest text-white">AI Career Action Engine</h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 relative z-10">
                {/* Next Best Action */}
                <div className="bg-[#0F172A] rounded-xl border border-white/5 p-4 col-span-1 md:col-span-2">
                  <div className="text-xs font-black uppercase tracking-widest text-cyan-400 mb-2">Next Best Action</div>
                  <p className="text-white font-medium text-sm">{nextBestAction}</p>
                </div>
                {/* Current Mode */}
                <div className="bg-[#0F172A] rounded-xl border border-white/5 p-4">
                  <div className="text-xs font-black uppercase tracking-widest text-slate-400 mb-2">Current Mode</div>
                  <div className={`text-lg font-black ${
                    careerMode === 'foundation' ? 'text-red-400' :
                    careerMode === 'growth' ? 'text-yellow-400' : 'text-green-400'
                  }`}>
                    {careerMode === 'foundation' && '🏗️ Foundation'}
                    {careerMode === 'growth' && '📈 Growth'}
                    {careerMode === 'job_ready' && '🚀 Job Ready'}
                  </div>
                </div>
                {/* Growth State */}
                <div className="bg-[#0F172A] rounded-xl border border-white/5 p-4">
                  <div className="text-xs font-black uppercase tracking-widest text-slate-400 mb-2">Growth State</div>
                  <div className={`text-lg font-black ${
                    careerBrain?.trend === 'Improving' ? 'text-green-400' :
                    careerBrain?.trend === 'Declining' ? 'text-red-400' : 'text-yellow-400'
                  }`}>
                    {careerBrain?.trend === 'Improving' && '↗️ Growing'}
                    {careerBrain?.trend === 'Declining' && '↘️ Declining'}
                    {(!careerBrain?.trend || careerBrain?.trend === 'Stable') && '➡️ Stagnating'}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Career Intelligence Panel - AI Insights */}
          {progressData?.sessions && progressData.sessions.length > 0 && (
            <motion.div 
              variants={itemVariants}
              className={`bg-[#1E293B] rounded-3xl border p-8 relative overflow-hidden mb-12 transition-all ${
                careerMode === 'foundation' && progressData.sessions.length > 0
                  ? 'border-red-500/50 ring-2 ring-red-500/20'
                  : 'border-white/5'
              }`}
            >
              <div className="absolute top-0 right-0 p-8 opacity-5">
                <Sparkles className="w-32 h-32" />
              </div>
              
              <div className="flex items-center gap-3 mb-8 relative z-10">
                <div className="p-3 rounded-xl bg-gradient-to-br from-[#6C3FC8]/20 to-purple-500/20 border border-[#6C3FC8]/30">
                  <BrainIcon className="w-6 h-6 text-[#6C3FC8]" />
                </div>
                <div>
                  <h2 className="text-xl font-black uppercase tracking-widest text-white">Career Intelligence</h2>
                  <p className="text-xs font-bold text-slate-500 mt-1">AI-powered insights derived from your interview history</p>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8 relative z-10">
                {/* Readiness Score */}
                <div className="bg-[#0F172A] rounded-2xl border border-white/5 p-6">
                  <div className="flex items-center gap-2 mb-3">
                    <Target className="w-4 h-4 text-[#6C3FC8]" />
                    <span className="text-xs font-black uppercase tracking-widest text-slate-400">Readiness</span>
                  </div>
                  <div className="text-4xl font-black text-white mb-1">
                    {analysis.readinessScore}
                    <span className="text-lg text-slate-500 ml-1">/100</span>
                  </div>
                  <div className={`text-xs font-black uppercase tracking-widest ${
                    analysis.readinessScore >= 70 ? 'text-green-400' : 
                    analysis.readinessScore >= 40 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {analysis.readinessScore >= 70 ? 'Advanced' : 
                     analysis.readinessScore >= 40 ? 'Intermediate' : 'Beginner'}
                  </div>
                </div>
                
                {/* Trend Indicator */}
                <div className="bg-[#0F172A] rounded-2xl border border-white/5 p-6">
                  <div className="flex items-center gap-2 mb-3">
                    <TrendingUpIcon className="w-4 h-4 text-[#6C3FC8]" />
                    <span className="text-xs font-black uppercase tracking-widest text-slate-400">Trend</span>
                  </div>
                  <div className="text-3xl font-black text-white mb-1 flex items-center gap-2">
                    {analysis.trend === 'Improving' && <><TrendingUpIcon className="w-8 h-8 text-green-400" /> Improving</>}
                    {analysis.trend === 'Stable' && <><MinusIcon className="w-8 h-8 text-yellow-400" /> Stable</>}
                    {analysis.trend === 'Declining' && <><TrendingDownIcon className="w-8 h-8 text-red-400" /> Declining</>}
                  </div>
                  <div className="text-xs font-black uppercase tracking-widest text-slate-500">
                    Based on {progressData.sessions.length} sessions
                  </div>
                </div>
                
                {/* Weak Categories Count */}
                <div className="bg-[#0F172A] rounded-2xl border border-white/5 p-6">
                  <div className="flex items-center gap-2 mb-3">
                    <AlertTriangleIcon className="w-4 h-4 text-[#6C3FC8]" />
                    <span className="text-xs font-black uppercase tracking-widest text-slate-400">Focus Areas</span>
                  </div>
                  <div className="text-4xl font-black text-white mb-1">
                    {analysis.weaknessMap.filter(w => w.level === 'Weak').length}
                  </div>
                  <div className="text-xs font-black uppercase tracking-widest text-slate-500">
                    Categories need attention
                  </div>
                </div>
                
                {/* Strong Categories Count */}
                <div className="bg-[#0F172A] rounded-2xl border border-white/5 p-6">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircleIcon className="w-4 h-4 text-green-400" />
                    <span className="text-xs font-black uppercase tracking-widest text-slate-400">Strengths</span>
                  </div>
                  <div className="text-4xl font-black text-white mb-1">
                    {analysis.weaknessMap.filter(w => w.level === 'Strong').length}
                  </div>
                  <div className="text-xs font-black uppercase tracking-widest text-slate-500">
                    Categories strong in
                  </div>
                </div>
              </div>
              
              {/* AI Summary Card */}
              <div className="bg-gradient-to-r from-[#6C3FC8]/10 to-purple-500/10 rounded-2xl border border-[#6C3FC8]/20 p-6 relative overflow-hidden">
                <div className="absolute -top-10 -right-10 w-32 h-32 bg-[#6C3FC8] opacity-10 rounded-full blur-[60px]" />
                <div className="flex items-start gap-4 relative z-10">
                  <div className="p-3 rounded-xl bg-[#6C3FC8]/20 border border-[#6C3FC8]/30 shrink-0">
                    <LightbulbIcon className="w-6 h-6 text-yellow-400" />
                  </div>
                  <div>
                    <h3 className="text-sm font-black uppercase tracking-widest text-white mb-2">AI Insight</h3>
                    <p className="text-slate-300 font-medium leading-relaxed">
                      {analysis.aiSummary}
                    </p>
                  </div>
                </div>
              </div>
              
              {/* Weakness Breakdown */}
              {analysis.weaknessMap.length > 0 && (
                <div className="mt-8">
                  <h3 className="text-sm font-black uppercase tracking-widest text-slate-400 mb-4">Category Analysis</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {analysis.weaknessMap.map((entry, idx) => (
                      <div 
                        key={idx}
                        className={`p-4 rounded-xl border ${
                          entry.level === 'Weak' ? 'bg-red-500/5 border-red-500/20' :
                          entry.level === 'Moderate' ? 'bg-yellow-500/5 border-yellow-500/20' :
                          'bg-green-500/5 border-green-500/20'
                        }`}
                      >
                        <div className="flex justify-between items-center mb-2">
                          <span className="text-sm font-black text-white">{entry.category}</span>
                          <span className={`text-xs font-black uppercase tracking-widest ${
                            entry.level === 'Weak' ? 'text-red-400' :
                            entry.level === 'Moderate' ? 'text-yellow-400' :
                            'text-green-400'
                          }`}>
                            {entry.level}
                          </span>
                        </div>
                        <div className="h-2 bg-[#0F172A] rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${
                              entry.level === 'Weak' ? 'bg-red-500' :
                              entry.level === 'Moderate' ? 'bg-yellow-500' :
                              'bg-green-500'
                            }`}
                            style={{ width: `${entry.avgScore}%` }}
                          />
                        </div>
                        <div className="text-xs font-black text-slate-500 mt-1 text-right">{entry.avgScore}%</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {/* Career Copilot Panel - AI Action Generator */}
          {progressData?.sessions && progressData.sessions.length > 0 && (
            <motion.div 
              variants={itemVariants}
              className={`bg-[#1E293B] rounded-3xl border p-8 relative overflow-hidden mb-12 transition-all ${
                careerMode === 'growth' && progressData.sessions.length > 0
                  ? 'border-yellow-500/50 ring-2 ring-yellow-500/20'
                  : 'border-white/5'
              }`}
            >
              <div className="absolute top-0 right-0 p-8 opacity-5">
                <Bot className="w-32 h-32" />
              </div>
              
              <div className="flex items-center gap-3 mb-8 relative z-10">
                <div className="p-3 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 border border-blue-500/30">
                  <Bot className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <h2 className="text-xl font-black uppercase tracking-widest text-white">Career Copilot</h2>
                  <p className="text-xs font-bold text-slate-500 mt-1">AI action generator based on your performance</p>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 relative z-10">
                {/* Next Action Card */}
                <div className="bg-gradient-to-r from-blue-600/20 to-cyan-600/20 rounded-2xl border border-blue-500/30 p-6">
                  <div className="flex items-center gap-2 mb-3">
                    <Zap className="w-4 h-4 text-blue-400" />
                    <span className="text-xs font-black uppercase tracking-widest text-slate-400">Next Action</span>
                  </div>
                  <p className="text-white font-medium leading-relaxed">
                    {copilot.nextAction}
                  </p>
                </div>
                
                {/* Job Readiness Card */}
                <div className={`rounded-2xl border p-6 ${
                  copilot.jobReadiness.status === 'Ready' ? 'bg-green-500/10 border-green-500/30' :
                  copilot.jobReadiness.status === 'Almost Ready' ? 'bg-yellow-500/10 border-yellow-500/30' :
                  'bg-red-500/10 border-red-500/30'
                }`}>
                  <div className="flex items-center gap-2 mb-3">
                    <BriefcaseIcon className={`w-4 h-4 ${
                      copilot.jobReadiness.status === 'Ready' ? 'text-green-400' :
                      copilot.jobReadiness.status === 'Almost Ready' ? 'text-yellow-400' :
                      'text-red-400'
                    }`} />
                    <span className="text-xs font-black uppercase tracking-widest text-slate-400">Job Readiness</span>
                  </div>
                  <div className="text-3xl font-black text-white mb-1">
                    {copilot.jobReadiness.status}
                  </div>
                  <div className="text-xs font-black text-slate-500">
                    {copilot.jobReadiness.confidence}% confidence
                  </div>
                </div>
              </div>
              
              {/* Skill Gap Roadmap */}
              {(copilot.roadmap.mustImprove.length > 0 || copilot.roadmap.goodToHave.length > 0) && (
                <div className="mb-8">
                  <h3 className="text-sm font-black uppercase tracking-widest text-slate-400 mb-4">Skill Gap Roadmap</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Must Improve */}
                    <div className="bg-red-500/5 rounded-xl border border-red-500/20 p-4">
                      <div className="text-xs font-black uppercase tracking-widest text-red-400 mb-3">Must Improve</div>
                      {copilot.roadmap.mustImprove.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {copilot.roadmap.mustImprove.map((skill, idx) => (
                            <span key={idx} className="px-3 py-1 bg-red-500/20 rounded-full text-xs font-medium text-red-300">
                              {skill}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-500">No critical gaps</p>
                      )}
                    </div>
                    
                    {/* Good to Have */}
                    <div className="bg-yellow-500/5 rounded-xl border border-yellow-500/20 p-4">
                      <div className="text-xs font-black uppercase tracking-widest text-yellow-400 mb-3">Good to Have</div>
                      {copilot.roadmap.goodToHave.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {copilot.roadmap.goodToHave.map((skill, idx) => (
                            <span key={idx} className="px-3 py-1 bg-yellow-500/20 rounded-full text-xs font-medium text-yellow-300">
                              {skill}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-500">No moderate gaps</p>
                      )}
                    </div>
                  </div>
                </div>
              )}
              
              {/* Copilot Summary */}
              <div className="bg-gradient-to-r from-blue-500/10 to-cyan-500/10 rounded-2xl border border-blue-500/20 p-6 relative overflow-hidden">
                <div className="absolute -top-10 -right-10 w-32 h-32 bg-blue-500 opacity-10 rounded-full blur-[60px]" />
                <div className="flex items-start gap-4 relative z-10">
                  <div className="p-3 rounded-xl bg-blue-500/20 border border-blue-500/30 shrink-0">
                    <MessageSquareIcon className="w-6 h-6 text-blue-400" />
                  </div>
                  <div>
                    <h3 className="text-sm font-black uppercase tracking-widest text-white mb-2">Copilot Summary</h3>
                    <p className="text-slate-300 font-medium leading-relaxed">
                      {copilot.summary}
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* STEP 5: Career Evolution Engine Panel - Using careerBrain.raw.evolution */}
          {(careerBrain?.raw.evolution?.career_paths && careerBrain.raw.evolution.career_paths.length > 0) ? (
            <motion.div 
              variants={itemVariants}
              className={`bg-[#1E293B] rounded-3xl border p-8 relative overflow-hidden mb-12 transition-all ${
                careerMode === 'job_ready' && careerBrain?.raw.evolution && careerBrain.raw.evolution.career_paths.length > 0
                  ? 'border-green-500/50 ring-2 ring-green-500/20'
                  : 'border-white/5'
              }`}
            >
              <div className="absolute top-0 right-0 p-8 opacity-5">
                <TrendingUpIcon className="w-32 h-32" />
              </div>
              
              <div className="flex items-center gap-3 mb-8 relative z-10">
                <div className="p-3 rounded-xl bg-gradient-to-br from-green-500/20 to-emerald-500/20 border border-green-500/30">
                  <TrendingUpIcon className="w-6 h-6 text-green-400" />
                </div>
                <div>
                  <h2 className="text-xl font-black uppercase tracking-widest text-white">Career Evolution Engine</h2>
                  <p className="text-xs font-bold text-slate-500 mt-1">Long-term skill growth tracking and predictions</p>
                </div>
              </div>
              
              {/* Growth State Badge - Using careerBrain.trend */}
              <div className="mb-8 relative z-10">
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-xs font-black uppercase tracking-widest text-slate-400">Growth State</span>
                </div>
                <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-lg font-black ${
                  careerBrain.trend === 'Improving' ? 'bg-green-500/20 text-green-400 border border-green-500/30' :
                  careerBrain.trend === 'Declining' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                  'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                }`}>
                  {careerBrain.trend === 'Improving' && <><TrendingUpIcon className="w-5 h-5" /> Growing</>}
                  {careerBrain.trend === 'Declining' && <><TrendingDownIcon className="w-5 h-5" /> Declining</>}
                  {careerBrain.trend === 'Stable' && <><MinusIcon className="w-5 h-5" /> Stagnating</>}
                </div>
              </div>
              
              {/* Career Path Breakdown - Using careerBrain.raw.evolution.career_paths */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 relative z-10">
                {careerBrain.raw.evolution.career_paths.map((path, idx) => (
                  <div key={idx} className="bg-[#0F172A] rounded-2xl border border-white/5 p-4">
                    <div className="flex justify-between items-start mb-3">
                      <span className="text-sm font-black text-white">{path.career_path}</span>
                      <span className={`text-xs ${
                        path.trend === 'improving' ? 'text-green-400' :
                        path.trend === 'declining' ? 'text-red-400' : 'text-yellow-400'
                      }`}>
                        {path.trend === 'improving' ? '📈' : path.trend === 'declining' ? '📉' : '➖'} {path.trend}
                      </span>
                    </div>
                    <div className="text-2xl font-black text-white mb-2">{path.avg_score}<span className="text-sm text-slate-500">/100</span></div>
                    {/* Volatility Bar */}
                    <div className="mb-2">
                      <div className="flex justify-between text-[10px] mb-1">
                        <span className="text-slate-500">Volatility</span>
                        <span className={path.volatility <= 0.2 ? 'text-green-400' : path.volatility <= 0.5 ? 'text-yellow-400' : 'text-red-400'}>
                          {path.volatility <= 0.2 ? 'Stable' : path.volatility <= 0.5 ? 'Moderate' : 'Inconsistent'}
                        </span>
                      </div>
                      <div className="h-2 bg-[#1E293B] rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${
                            path.volatility <= 0.2 ? 'bg-green-500' :
                            path.volatility <= 0.5 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${path.volatility * 100}%` }}
                        />
                      </div>
                    </div>
                    <div className="flex justify-between text-[10px]">
                      <span className="text-slate-500">{path.total_sessions} sessions</span>
                      <span className="text-slate-400">{Math.round(path.confidence * 100)}% conf.</span>
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Intelligence Summary - Using careerBrain.trend */}
              <div className="mt-8 bg-gradient-to-r from-green-500/10 to-emerald-500/10 rounded-2xl border border-green-500/20 p-6 relative overflow-hidden">
                <div className="absolute -top-10 -right-10 w-32 h-32 bg-green-500 opacity-10 rounded-full blur-[60px]" />
                <div className="flex items-start gap-4 relative z-10">
                  <div className="p-3 rounded-xl bg-green-500/20 border border-green-500/30 shrink-0">
                    <LightbulbIcon className="w-6 h-6 text-green-400" />
                  </div>
                  <div>
                    <h3 className="text-sm font-black uppercase tracking-widest text-white mb-2">Evolution Insight</h3>
                    <p className="text-slate-300 font-medium leading-relaxed">
                      {careerBrain.trend === 'Improving' && "You are in a strong growth phase. Keep building on this momentum!"}
                      {careerBrain.trend === 'Declining' && "Your performance is declining. Focus on stabilizing skills before advancing."}
                      {careerBrain.trend === 'Stable' && "Your performance is stable. Push yourself to break through to the next level."}
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>
          ) : (
            /* Fallback when no evolution data available */
            <motion.div 
              variants={itemVariants}
              className="bg-[#1E293B] rounded-3xl border border-white/5 p-8 relative overflow-hidden mb-12"
            >
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-xl bg-slate-800 border border-white/5">
                  <TrendingUpIcon className="w-6 h-6 text-slate-500" />
                </div>
                <div>
                  <h2 className="text-xl font-black uppercase tracking-widest text-white">Career Evolution Engine</h2>
                  <p className="text-xs font-bold text-slate-500 mt-1">Evolution data not available yet. Complete more interviews to unlock.</p>
                </div>
              </div>
            </motion.div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Score Trend Chart */}
            <motion.div variants={itemVariants} className="lg:col-span-2 bg-[#1E293B] rounded-3xl border border-white/5 p-8 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-8 opacity-5">
                <LineChartIcon className="w-32 h-32" />
              </div>
              <div className="flex items-center justify-between mb-8 relative z-10">
                <div>
                  <h2 className="text-xl font-black uppercase tracking-widest text-white">Score Analytics</h2>
                  <p className="text-xs font-bold text-slate-500 mt-1">Growth trajectory across verified sessions</p>
                </div>
                <div className="flex gap-2">
                  <div className="flex items-center gap-2 bg-[#0F172A] px-3 py-1.5 rounded-lg border border-white/5">
                    <div className="w-2 h-2 rounded-full bg-[#6C3FC8] shadow-[0_0_8px_#6C3FC8]" />
                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Score Out of 50</span>
                  </div>
                </div>
              </div>
              
              {hasEnoughDataForChart ? (
                <div className="h-[300px] w-full mt-4 relative z-10">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#6C3FC8" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#6C3FC8" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ffffff05" />
                      <XAxis 
                        dataKey="name" 
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: '#64748b', fontSize: 10, fontWeight: 700 }}
                        dy={10}
                      />
                      <YAxis 
                        domain={[0, 50]} 
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: '#64748b', fontSize: 10, fontWeight: 700 }}
                        dx={-10}
                      />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: '#0F172A', 
                          border: '1px solid rgba(255,255,255,0.1)',
                          borderRadius: '16px',
                          color: '#fff',
                          boxShadow: '0 10px 15px -3px rgba(0,0,0,0.5)'
                        }}
                        itemStyle={{ color: '#6C3FC8', fontWeight: 900 }}
                        labelStyle={{ color: '#94a3b8', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '4px' }}
                        cursor={{ stroke: '#6C3FC8', strokeWidth: 2, strokeDasharray: '5 5' }}
                        formatter={(value: number, name: string, props: any) => [
                          `${value}/50`,
                          props.payload.career
                        ]}
                      />
                      <Area
                        type="monotone"
                        dataKey="score"
                        stroke="#6C3FC8"
                        strokeWidth={4}
                        fillOpacity={1}
                        fill="url(#scoreGradient)"
                        dot={{ fill: '#FACC15', stroke: '#1E293B', strokeWidth: 2, r: 6 }}
                        activeDot={{ r: 8, fill: '#6C3FC8', stroke: '#fff' }}
                        animationDuration={1500}
                        animationBegin={300}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-[300px] flex items-center justify-center">
                  <p className="text-slate-500 font-bold text-sm tracking-widest uppercase">Not enough data for trends</p>
                </div>
              )}
            </motion.div>

            {/* Career Path Breakdown */}
            {careerBreakdown.length > 0 ? (
              <motion.div variants={itemVariants} className="bg-[#1E293B] rounded-3xl border border-white/5 p-8">
                <h2 className="text-xl font-black uppercase tracking-widest text-white mb-6">Career Matrix</h2>
                <div className="space-y-6">
                  {careerBreakdown.map((item, index) => (
                    <div key={index} className="group cursor-default">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-black text-slate-300 group-hover:text-white transition-colors">{item.career}</span>
                        <span className="text-sm font-bold text-yellow-400">{item.average}%</span>
                      </div>
                      <div className="h-3 bg-[#0F172A] rounded-full overflow-hidden border border-white/5">
                        <motion.div 
                          initial={{ width: 0 }}
                          animate={{ width: `${item.average}%` }}
                          transition={{ duration: 1, ease: "circOut", delay: index * 0.1 }}
                          className="h-full bg-gradient-to-r from-[#6C3FC8] to-purple-400 rounded-full shadow-[0_0_10px_rgba(108,63,200,0.3)]"
                        />
                      </div>
                      <div className="flex justify-between mt-1 text-[9px] font-black uppercase tracking-widest text-slate-500">
                        <span>Analysis: {item.count} sessions</span>
                        <span>Maturity Level</span>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            ) : null}

            {/* XP Progress Section */}
            <motion.div variants={itemVariants} className="bg-[#1E293B] rounded-3xl border border-white/5 p-8 relative overflow-hidden group">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 via-yellow-400 to-purple-500 opacity-30" />
              <div className="flex items-center gap-4 mb-8">
                <div className="p-3 rounded-2xl bg-gradient-to-br from-purple-500/20 to-yellow-500/20 border border-white/10 group-hover:rotate-12 transition-transform shadow-xl">
                  <Sparkles className="w-6 h-6 text-yellow-400" />
                </div>
                <div>
                  <h2 className="text-xl font-black uppercase tracking-widest text-white">Maturity Arc</h2>
                  <p className="text-xs font-bold text-slate-500 mt-1">XP Progression to next Tier</p>
                </div>
              </div>
              
              <div className="relative text-center py-6">
                <div className="text-4xl font-black text-white tracking-tighter mb-1 relative z-10 drop-shadow-[0_0_15px_rgba(108,63,200,0.5)]">
                  {rankTitle}
                </div>
                <div className="inline-flex items-center gap-2 px-4 py-1 bg-slate-800 rounded-full border border-white/5 text-[10px] font-black uppercase tracking-widest text-[#6C3FC8] shadow-inner mb-6">
                   Tier Level {level}
                </div>
                
                <div className="relative">
                  <div className="flex justify-between text-xs font-black uppercase tracking-widest text-slate-400 mb-2 px-1">
                    <span>{xp} XP</span>
                    <span className="text-yellow-400">{getNextLevelXP(level)} XP</span>
                  </div>
                  <div className="h-4 bg-[#0F172A] rounded-full overflow-hidden border border-white/5 p-0.5">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ 
                        width: `${Math.min(100, (xp / getNextLevelXP(level)) * 100)}%` 
                      }}
                      transition={{ duration: 1.5, ease: "circOut" }}
                      className="h-full bg-gradient-to-r from-[#6C3FC8] via-purple-400 to-[#FACC15] rounded-full relative"
                    >
                      <div className="absolute inset-0 bg-[linear-gradient(45deg,transparent_25%,rgba(255,255,255,0.1)_50%,transparent_75%)] bg-[length:20px_20px] animate-[slide_1s_linear_infinite]" />
                    </motion.div>
                  </div>
                  <div className="absolute top-1/2 left-0 w-full flex justify-center -translate-y-1/2 pointer-events-none opacity-20">
                     <div className="w-full h-6 bg-yellow-400 blur-2xl rounded-full" />
                  </div>
                </div>
              </div>

              <div className="mt-8 flex items-center justify-between p-4 bg-[#0F172A] rounded-2xl border border-white/5">
                 <div className="text-xs font-black uppercase tracking-widest text-slate-500">Next Tier</div>
                 <div className="flex items-center gap-2 text-slate-300">
                     <span className="text-xs font-black">Level {Math.min(7, level + 1)}</span>
                     <ChevronRight className="w-4 h-4 text-slate-600" />
                 </div>
              </div>
            </motion.div>

            {/* Weekly Email Report Section */}
            <motion.div variants={itemVariants} className="lg:col-span-2 bg-[#1E293B] rounded-3xl border border-white/5 p-8 relative overflow-hidden group">
              <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-[#6C3FC8] opacity-5 rounded-full blur-[80px]" />
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
                <div className="max-w-md">
                  <h2 className="text-2xl font-black uppercase tracking-widest text-white flex items-center gap-3">
                    <Mail className="w-6 h-6 text-[#6C3FC8]" /> 
                    Intel <span className="text-slate-500">Broadcast</span>
                  </h2>
                  <p className="text-slate-400 font-medium text-sm mt-2">
                    Receive your comprehensive AI performance breakdown and skill-gap analysis via secure SMTP protocol every Monday.
                  </p>
                </div>
                
                <div className="flex-1 flex flex-col gap-4">
                  <div className="flex gap-2 p-1 bg-[#0F172A] rounded-2xl border border-white/5 shadow-inner">
                    <input
                      type="email"
                      value={userEmail}
                      onChange={(e) => setUserEmail(e.target.value)}
                      placeholder="Verified Terminal Address"
                      className="flex-1 bg-transparent px-4 py-3 text-white text-sm outline-none font-bold placeholder:text-slate-700"
                      aria-label="Email address for report"
                    />
                    <Button 
                      onClick={sendWeeklyReport}
                      disabled={sendingReport || !userEmail}
                      className="bg-[#6C3FC8] hover:bg-[#6C3FC8]/90 text-white font-black uppercase tracking-tighter text-xs px-6 rounded-xl shadow-[0_0_20px_rgba(108,63,200,0.3)] transition-all active:scale-95"
                    >
                      {sendingReport ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : 'Request Dispatch'}
                    </Button>
                  </div>
                  
                  <AnimatePresence>
                    {reportSent && (
                      <motion.div 
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className="bg-green-500/10 border border-green-500/20 p-2 rounded-xl text-center"
                      >
                        <span className="text-xs font-black uppercase tracking-widest text-green-400">✅ Intelligence Dispatched to {userEmail}</span>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
              
              <div className="flex items-center gap-3 mt-6 pt-6 border-t border-white/5 opacity-40">
                <LightbulbIcon className="w-4 h-4 text-yellow-400" />
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                  Encryption active: GMAIL_SERVICE_PROTOCOL_ENABLED
                </p>
              </div>
            </motion.div>
          </div>
        </motion.div>
      </main>
      
      {/* Background Orbs */}
      <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden">
        <div className="absolute top-[20%] left-[-10%] w-[500px] h-[500px] bg-purple-900/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-[#6C3FC8]/5 rounded-full blur-[100px]" />
      </div>
    </div>
  )
}

// Brain icon component used in Career Intelligence Panel
function BrainIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 1.5 4 4 0 0 0 .222 5.855 3 3 0 1 0 .745 4.958 3 3 0 1 0 3.94-5.292.5.5 0 0 0-.14.327A3.996 3.996 0 1 1 12 5Z" />
      <path d="M12 12a4 4 0 1 1 4-4 .5.5 0 0 0-.5.5 3.5 3.5 0 0 1 0 7Z" />
    </svg>
  )
}

// TrendingUp icon (up arrow for improving trend)
function TrendingUpIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
      <polyline points="17 6 23 6 23 12" />
    </svg>
  )
}

// TrendingDown icon (down arrow for declining trend)
function TrendingDownIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" />
      <polyline points="17 18 23 18 23 12" />
    </svg>
  )
}

// Minus icon (for stable trend)
function MinusIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  )
}

// AlertTriangle icon (for warning/focus areas)
function AlertTriangleIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  )
}

// CheckCircle icon (for success/strengths)
function CheckCircleIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  )
}

// Lightbulb icon (for AI Insight)
function LightbulbIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .5 2.2 1.5 3.1.7.7 1.3 1.5 1.5 2.4" />
      <path d="M9 18h6" />
      <path d="M10 22h4" />
    </svg>
  )
}

// Robot icon (for Career Copilot)
function RobotIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="11" width="18" height="10" rx="2" />
      <circle cx="12" cy="5" r="2" />
      <path d="M12 7v4" />
      <line x1="8" y1="16" x2="8" y2="16" />
      <line x1="16" y1="16" x2="16" y2="16" />
    </svg>
  )
}

// Briefcase icon (for job readiness)
function BriefcaseIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </svg>
  )
}

// MessageSquare icon (for copilot summary)
function MessageSquareIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  )
}