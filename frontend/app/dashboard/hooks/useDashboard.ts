/**
 * useDashboard Hook (SRP Fix)
 * All state, auth, and data loading extracted from DashboardPage.
 * DashboardPage becomes a pure renderer — no fetch, no state, no logic.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import {
  dashboardClient,
  CareerBrainData,
  AppStats,
  AnalysisSummary,
  ResumeScore,
} from '@/lib/api/dashboardClient'

export interface UseDashboardReturn {
  user: { email: string; id?: string } | null
  loading: boolean
  brain: CareerBrainData | null
  brainLoading: boolean
  appStats: AppStats
  analysisSummary: AnalysisSummary | null
  roadmapCompleted: number
}

// ─── Pure parser — module level, no side effects ──────────────────────────────

function parseAnalysisSummary(record: any): AnalysisSummary {
  const analysisObj = record?.analysis || {}
  const experienceLevel =
    analysisObj.analysis?.experience_level ||
    analysisObj.experience_level ||
    record.experience_level ||
    'Beginner'

  const resumeScore: ResumeScore | null =
    record.resume_score?.overall != null
      ? record.resume_score
      : analysisObj.resume_score || null

  const careerPaths = record.career_paths || analysisObj.career_paths || []
  const bestPath = Array.isArray(careerPaths) && careerPaths.length > 0 ? careerPaths[0] : null
  const bestMatch = bestPath
    ? {
        name: bestPath.name || bestPath.career_name || bestPath.title || 'Unknown',
        percentage: bestPath.match_percentage ?? bestPath.match ?? bestPath.percentage ?? 0,
      }
    : null

  const pathDetails = record?.path_details || {}
  const pathSpecificRoadmap = bestMatch?.name ? pathDetails[bestMatch.name]?.roadmap : null
  const roadmap = pathSpecificRoadmap || analysisObj.roadmap || record.roadmap || { milestones: [] }

  const skillGaps = analysisObj.skill_gaps || analysisObj.skill_gap || record.skill_gaps || []

  return {
    experience_level: experienceLevel,
    resume_score: resumeScore,
    best_match: bestMatch,
    roadmap_total: roadmap?.milestones?.length || 0,
    roadmap_completed: 0,
    skill_gaps_count: Array.isArray(skillGaps) ? skillGaps.length : 0,
    best_career_path: bestMatch?.name || '',
  }
}

// ─── Hook ─────────────────────────────────────────────────────────────────────
export function useDashboard(): UseDashboardReturn {
  const isMountedRef = useRef(true)

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  const router = useRouter()

  const [user, setUser] = useState<{ email: string; id?: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const [brain, setBrain] = useState<CareerBrainData | null>(null)
  const [brainLoading, setBrainLoading] = useState(true)
  const [appStats, setAppStats] = useState<AppStats>({
    applied: 0,
    interview: 0,
    rejected: 0,
    offer: 0,
  })
  const [analysisSummary, setAnalysisSummary] = useState<AnalysisSummary | null>(null)
  const [roadmapCompleted, setRoadmapCompleted] = useState(0)

  const loadData = useCallback(async (token: string) => {
    setBrainLoading(true)
    
    try {
      const [brainData, stats, rawAnalysis] = await Promise.all([
        dashboardClient.getCareerBrain(token),
        dashboardClient.getApplicationStats(token),
        dashboardClient.getAnalysis(token),
      ])

      if (!isMountedRef.current) return
      let summary: AnalysisSummary | null = null
      let completed = 0
    
      if (rawAnalysis) {
        summary = parseAnalysisSummary(rawAnalysis)
        setAnalysisSummary(summary)

        if (summary.best_career_path) {
          const progressMap =
            await dashboardClient.getRoadmapProgress(
              token,
              summary.best_career_path
            )

          if (!isMountedRef.current) return

          completed = Object.values(progressMap).filter(
            s => s === 'completed'
          ).length
        }
      }
      if (!isMountedRef.current) return
      setBrain(brainData)
      setAppStats(stats)
      setAnalysisSummary(
        summary ? { ...summary, roadmap_completed: completed } : null
      )
      setRoadmapCompleted(completed)
    } catch (e) {
      router.push('/auth/login')
    } finally {
      if (isMountedRef.current) {
        setBrainLoading(false)
        setLoading(false)
      }
    }
  }, [router])

  useEffect(() => {
    const init = async () => {
      try {
        const { data: { user }, error } = await supabase.auth.getUser()

        if (error || !user?.email) {
          router.push('/auth/login')
          return
        }

        setUser({ email: user.email, id: user.id })

        const { data: { session } } = await supabase.auth.getSession()

        if (!session?.access_token) {
          router.push('/auth/login')
          return
        }

        await loadData(session.access_token)

      } catch {
        router.push('/auth/login')
      } finally {
        if (isMountedRef.current) setLoading(false)
      }
    }

    init()
  }, [router, loadData])

  return {
    user,
    loading,
    brain,
    brainLoading,
    appStats,
    analysisSummary,
    roadmapCompleted,
  }
}