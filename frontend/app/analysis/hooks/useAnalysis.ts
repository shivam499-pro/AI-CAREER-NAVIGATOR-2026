/**
 * useAnalysis Hook - Phase 3 (SRP Fix)
 * All polling, state, and milestone logic extracted from page.tsx.
 * page.tsx becomes a pure renderer — no logic, no fetch, no state management.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { analysisClient, AnalysisRecord } from '@/lib/api/analysisClient'

export interface AnalysisData {
  experience_level: string
  strengths: string[]
  career_paths: any[]
  skill_gaps: any[]
  roadmap: any
  resume_score?: any
  salary_insights?: any
  top_companies?: any[]
  certifications?: any[]
}

export interface UseAnalysisReturn {
  loading: boolean
  analyzing: boolean
  analysis: AnalysisData | null
  selectedPath: string
  pathDetails: Record<string, any>
  roadmapProgress: Record<number, string>
  progressLoading: boolean
  error: string
  milestoneError: string
  user: { id: string } | null
  setSelectedPath: (path: string) => void
  runAnalysis: (userId: string) => Promise<void>
  updateMilestone: (week: number, currentStatus: string) => Promise<void>
}

function parseAnalysisRecord(record: any) {
  const analysisObj = record?.analysis || {}
  const strengths = analysisObj.analysis?.strengths || analysisObj.strengths || record.strengths || []
  const careerPaths = record.career_paths || analysisObj.career_paths || []
  const skillGaps = analysisObj.skill_gaps || analysisObj.skill_gap || record.skill_gaps || []
  const roadmap = analysisObj.roadmap || record.roadmap || { target_career: '', duration_months: 6, milestones: [] }
  const experienceLevel = analysisObj.analysis?.experience_level || analysisObj.experience_level || record.experience_level || 'Beginner'
  const pathDetails = record?.path_details || {}
  const firstPathName = Array.isArray(careerPaths) && careerPaths.length > 0
    ? (careerPaths[0]?.name || careerPaths[0]?.career_name || careerPaths[0]?.title || '')
    : ''
  return {
    analysis: {
      experience_level: experienceLevel,
      strengths: Array.isArray(strengths) ? strengths.filter((s: string) => !String(s).toLowerCase().includes('error')) : [],
      career_paths: Array.isArray(careerPaths) ? careerPaths : [],
      skill_gaps: Array.isArray(skillGaps) ? skillGaps : [],
      roadmap,
      resume_score: (record.resume_score?.overall != null ? record.resume_score : null) || analysisObj.resume_score || null,
      salary_insights: (record.salary_insights?.entry_level ? record.salary_insights : null) || analysisObj.salary_insights || null,
      top_companies: (Array.isArray(record.top_companies) && record.top_companies.length > 0 ? record.top_companies : null) || analysisObj.top_companies || [],
      certifications: (Array.isArray(record.certifications) && record.certifications.length > 0 ? record.certifications : null) || analysisObj.certifications || [],
    },
    pathDetails,
    firstPathName,
  }
}

export function useAnalysis(): UseAnalysisReturn {
  const isMountedRef = useRef(true)
  useEffect(() => { 
    isMountedRef.current = true
    return () => { isMountedRef.current = false } }, [])

  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [user, setUser] = useState<{ id: string } | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null)
  const [selectedPath, setSelectedPath] = useState<string>('')
  const [pathDetails, setPathDetails] = useState<Record<string, any>>({})
  const [roadmapProgress, setRoadmapProgress] = useState<Record<number, string>>({})
  const [progressLoading, setProgressLoading] = useState(false)
  const [error, setError] = useState('')
  const [milestoneError, setMilestoneError] = useState('')

  const runAnalysis = useCallback(async (userId: string) => {
    setAnalyzing(true)
    setError('')
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) { 
        setError('User not authenticated. Please login again.')
        return
      }
      const token = session.access_token

      const job = await analysisClient.startAnalysis(token, userId)
      if(!job?.job_id){
        setError('Failed to start analysis job')
        return
      }

      const sleep = (ms: number) =>
        process.env.NODE_ENV === 'test'
          ? Promise.resolve()
          : new Promise(resolve => setTimeout(resolve, ms))
      for (let i = 0; i < 10; i++) {
        await Promise.resolve()

        if (!isMountedRef.current) return

        const jobStatus = 
        await analysisClient.getJobStatus(token, job.job_id)
        
        if (jobStatus.status === 'failed') { 
          setError('Analysis failed. Please try again.')
          return
        }

        let completed = false
        if (jobStatus.status === 'completed') {
          const record = await analysisClient.getFinalAnalysis(token)
          if (record) {
            const { analysis, pathDetails, firstPathName } = parseAnalysisRecord(record)

            if (!isMountedRef.current) return

            setAnalysis(analysis)
            setPathDetails(pathDetails)
            setSelectedPath(firstPathName)
          }
          completed = true
          return
        }
        if (!completed) {
          setError('Analysis timed out after multiple attempts. Please try again.')
        }
      }
      setError('Analysis is taking longer than expected. Please refresh the page.')
    } catch (err) {
      console.error('Analysis Error:', err)
      setError('Failed to run analysis. Please try again.')
    } finally {
      if(isMountedRef.current) {
        setAnalyzing(false)
      }
    }
  }, [])

  const checkExistingAnalysis = useCallback(async (userId: string) => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) { setError('User not authenticated. Please login again.'); setLoading(false); return }
      const token = session.access_token

      const { exists, analysis: record } = await analysisClient.checkExisting(token)
      if (exists && record) {
        const { analysis, pathDetails, firstPathName } = parseAnalysisRecord(record)
        setAnalysis(analysis); setPathDetails(pathDetails); setSelectedPath(firstPathName)
      } else {
        await runAnalysis(userId)
      }
    } catch (err) {
      console.error('Check Analysis Error:', err)
      setError('Failed to load analysis. Please try again.')
    }
  }, [runAnalysis])

  const fetchRoadmapProgress = useCallback(async (careerPath: string) => {
    if (!careerPath) return
    setProgressLoading(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) return
      const progress = await analysisClient.getRoadmapProgress(session.access_token, careerPath)
      setRoadmapProgress(progress)
    } catch (err) {
      console.error('Fetch roadmap progress error:', err)
    } finally {
      setProgressLoading(false)
    }
  }, [])

  const updateMilestone = useCallback(async (week: number, currentStatus: string) => {
    if (!selectedPath) return
    const nextStatus = currentStatus === 'pending' ? 'in_progress' : currentStatus === 'in_progress' ? 'completed' : 'pending'
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) return
      const { status, data } = await analysisClient.updateMilestone(session.access_token, selectedPath, week, nextStatus)
      if (status === 429) { setMilestoneError(data?.detail || data?.error || 'Wait before completing the next milestone.'); setTimeout(() => setMilestoneError(''), 4000); return }
      if (data?.success) {
        setRoadmapProgress(prev => ({ ...prev, [week]: nextStatus }))
      }
    } catch (err) {
      console.error('Update milestone error:', err)
    }
  }, [selectedPath])
  
  
  const initializedRef = useRef(false)

  useEffect(() => {
    if (initializedRef.current) return
    initializedRef.current = true
  
    const checkAuth = async () => {
      try {
        setLoading(true)
  
        const { data, error } = await supabase.auth.getUser()
  
        if (error || !data?.user) {
          if (!isMountedRef.current) return
  
          setUser(null)
          setLoading(false)
  
          router.push('/auth/login')
          return
        }
  
        if (!isMountedRef.current){
          setAnalyzing(false)
          setLoading(false)
          return
        }
        setUser(data.user)
  
        await checkExistingAnalysis(data.user.id)
  
      } catch (err) {
        console.error('Auth Error:', err)
  
        if (!isMountedRef.current) return
  
        setError('Authentication failed')
        setLoading(false)
  
      } finally {
        if (isMountedRef.current) {
          setLoading(false)
        }
      }
    }
  
    checkAuth()
  }, [router, checkExistingAnalysis])

  const previousPathRef = useRef<string>('')
  useEffect(() => {
    if (!selectedPath) return
  
    if (previousPathRef.current === selectedPath) return
  
    previousPathRef.current = selectedPath
  
    fetchRoadmapProgress(selectedPath)
  }, [selectedPath, fetchRoadmapProgress])
  return {
    loading, analyzing, analysis, selectedPath, pathDetails,
    roadmapProgress, progressLoading, error, milestoneError, user,
    setSelectedPath, runAnalysis, updateMilestone,
  }
}