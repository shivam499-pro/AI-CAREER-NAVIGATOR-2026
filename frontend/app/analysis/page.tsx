'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import Navbar from '@/components/Navbar'
import {
  Brain, ChevronRight, Loader2, Sparkles,
  TrendingUp, Target, Code, CheckCircle, XCircle,
  Calendar, ArrowRight, Award, Zap, AlertTriangle
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
  skill_gap?: SkillGap[]
  roadmap: Roadmap
}

export default function AnalysisPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [user, setUser] = useState<{ id: string } | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null)
  const [error, setError] = useState('')

  const runAnalysis = useCallback(async (userId: string) => {
    setAnalyzing(true)
    setError('')
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) {
        setError("User not authenticated. Please login again.")
        setLoading(false)
        return
      }
      const token = session.access_token
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/analysis/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ user_id: userId }),
      })
      if (!response.ok) throw new Error('Analysis failed to start')

      // Poll for completion - up to 10 times every 3 seconds
      for (let i = 0; i < 10; i++) {
        await new Promise(resolve => setTimeout(resolve, 3000))

        const checkRes = await fetch(`${apiUrl}/api/v1/analysis/`, {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          }
        })

        if (checkRes.ok) {
          const pollData = await checkRes.json()
          if (pollData?.success && pollData?.data?.exists && pollData?.data?.analysis) {
            const record = pollData.data.analysis
            const analysisObj = record?.analysis || {}

            const strengths = analysisObj.analysis?.strengths || analysisObj.strengths || record.strengths || []
            const careerPaths = record.career_paths || analysisObj.career_paths || []
            const skillGaps = analysisObj.skill_gaps || analysisObj.skill_gap || record.skill_gaps || []
            const roadmap = analysisObj.roadmap || record.roadmap || { target_career: '', duration_months: 6, milestones: [] }
            const experienceLevel = analysisObj.analysis?.experience_level || analysisObj.experience_level || record.experience_level || 'Beginner'

            setAnalysis({
              experience_level: experienceLevel,
              strengths: Array.isArray(strengths) ? strengths.filter((s: string) => !String(s).toLowerCase().includes('error')) : [],
              career_paths: Array.isArray(careerPaths) ? careerPaths : [],
              skill_gaps: Array.isArray(skillGaps) ? skillGaps : [],
              roadmap: roadmap,
            })
            setAnalyzing(false)
            setLoading(false)
            return
          }
        }
      }

      setError("Analysis is taking longer than expected. Please refresh the page.")
    } catch (err) {
      console.error("Analysis Error:", err)
      setError('Failed to run analysis. Please try again.')
    } finally {
      setAnalyzing(false)
      setLoading(false)
    }
  }, [])

  const checkExistingAnalysis = useCallback(async (userId: string) => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) {
        setError("User not authenticated. Please login again.")
        setLoading(false)
        return
      }
      const token = session.access_token
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/v1/analysis/`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        }
      })

      const data = await response.json()

      if (data?.sucess && data?.data?.exists && data?.data?.analysis) {
        const record = data.data.analysis
        const analysisObj = record?.analysis || {}

        console.log("SUPABASE DATA:", record)
        const strengths = analysisObj.analysis?.strengths || analysisObj.strengths || record.strengths || []
        const careerPaths = record.career_paths || analysisObj.career_paths || []
        const skillGaps = analysisObj.skill_gaps || analysisObj.skill_gap || record.skill_gaps || []
        const roadmap = analysisObj.roadmap || record.roadmap || { target_career: '', duration_months: 6, milestones: [] }
        const experienceLevel = analysisObj.analysis?.experience_level || analysisObj.experience_level || record.experience_level || 'Beginner'
        setAnalysis({
          experience_level: experienceLevel,
          strengths: Array.isArray(strengths) ? strengths.filter((s: string) => !String(s).toLowerCase().includes('error')) : [],
          career_paths: Array.isArray(careerPaths) ? careerPaths : [],
          skill_gaps: Array.isArray(skillGaps) ? skillGaps : [],
          roadmap: roadmap,
        })

      } else {
        await runAnalysis(userId)
      }
    } catch (err) {
      console.error("Check Analysis Error:", err)
      await runAnalysis(userId)
    } finally {
      setLoading(false)
    }
  }, [runAnalysis])

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
  }, [router, checkExistingAnalysis])

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary-violet mx-auto mb-4" />
          <p className="text-slate-400 font-medium tracking-wide">Loading Intelligence...</p>
        </div>
      </div>
    )
  }

  if (analyzing) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex items-center justify-center">
        <div className="text-center max-w-md p-8">
          <div className="relative mb-12">
            <div className="w-32 h-32 mx-auto">
              <div className="absolute inset-0 rounded-full border-4 border-primary-violet/20" />
              <div className="absolute inset-0 rounded-full border-4 border-primary-violet border-t-transparent animate-spin" />
              <div className="absolute inset-0 flex items-center justify-center">
                <Brain className="w-12 h-12 text-primary-violet drop-shadow-[0_0_10px_rgba(108,63,200,0.5)]" />
              </div>
            </div>
          </div>
          <h2 className="text-3xl font-black text-white mb-3 tracking-tight">Syncing Intelligence</h2>
          <p className="text-slate-400 mb-8 font-medium">Reading GitHub and LeetCode activity...</p>
          <div className="space-y-4 max-w-xs mx-auto">
            {['Fetching GitHub repos', 'Parsing LeetCode solutions', 'Generating career paths'].map((step, i) => (
              <div key={i} className="flex items-center gap-3 text-sm font-bold text-slate-300">
                <CheckCircle className={`w-5 h-5 ${i < 2 ? 'text-green-500' : 'text-slate-700'}`} />
                <span>{step}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.15 } }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  }

  const getExperienceStyles = (level: string) => {
    const l = level.toLowerCase()
    if (l.includes('beginner')) return 'bg-blue-500/10 text-blue-500 border-blue-500/30'
    if (l.includes('senior')) return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/30'
    return 'bg-primary-violet/10 text-primary-violet border-primary-violet/30'
  }

  if (!analysis) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary-violet mx-auto mb-4" />
          <p className="text-slate-400 font-medium tracking-wide">Loading analysis...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0F172A] text-white">
      <Navbar />
      <main className="container mx-auto px-4 py-12 max-w-6xl">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="space-y-12"
        >
          {/* Experience Level */}
          <motion.div variants={itemVariants} className="relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-primary-violet to-purple-600 rounded-3xl blur opacity-25 group-hover:opacity-40 transition" />
            <div className="relative bg-[#1E293B] rounded-2xl p-10 border border-white/5 flex flex-col md:flex-row items-center gap-8">
              <div className="w-20 h-20 bg-primary-violet/20 rounded-2xl flex items-center justify-center border border-primary-violet/30">
                <Award className="w-10 h-10 text-primary-violet" />
              </div>
              <div className="text-center md:text-left flex-1">
                <div className="flex items-center justify-center md:justify-start gap-2 mb-2">
                  <Sparkles className="w-5 h-5 text-primary-violet" />
                  <span className="text-xs font-black uppercase tracking-widest text-primary-violet">Analysis Baseline</span>
                </div>
                <h2 className="text-4xl font-black text-white mb-2">
                  {analysis.experience_level}
                </h2>
                <p className="text-slate-400 font-medium">Verified technical maturity across 12+ real-world indicators</p>
              </div>
              <div className={`px-8 py-4 rounded-xl border-2 font-black text-xl uppercase tracking-tighter ${getExperienceStyles(analysis.experience_level)}`}>
                {analysis.experience_level} Verified
              </div>
            </div>
          </motion.div>

          {/* Strengths */}
          <motion.div variants={itemVariants} className="space-y-6">
            <h3 className="text-xl font-black text-white uppercase tracking-widest flex items-center gap-3">
              <Zap className="w-5 h-5 text-green-500" />
              Core Technical Strengths
            </h3>
            <div className="flex flex-wrap gap-3">
              {(analysis.strengths || []).map((strength, i) => (
                <div
                  key={i}
                  className="px-6 py-3 bg-[#1E293B] border-l-4 border-l-green-500 text-white rounded-xl font-bold border border-white/5 shadow-lg group hover:scale-105 transition-all"
                >
                  {strength}
                </div>
              ))}
            </div>
          </motion.div>

          {/* Career Paths */}
          <motion.div variants={itemVariants} className="space-y-6">
            <h3 className="text-xl font-black text-white uppercase tracking-widest flex items-center gap-3">
              <Target className="w-5 h-5 text-primary-violet" />
              Strategic Career Paths
            </h3>
            <div className="grid md:grid-cols-3 gap-6">
              {(analysis.career_paths || []).slice(0, 3).map((path, i) => {
                const name = path.name || path.career_name || path.title || 'Unknown'
                const match = path.match_percentage ?? path.match ?? path.percentage ?? 0
                const desc = path.reason || path.description || path.justification || ''
                return (
                  <div key={i} className={`bg-[#1E293B] rounded-2xl p-8 border border-white/5 relative group transition-all hover:bg-[#1E293B]/80 ${i === 0 ? 'shadow-[0_0_30px_rgba(108,63,200,0.15)] ring-2 ring-primary-violet/30' : ''}`}>
                    {i === 0 && (
                      <div className="absolute -top-3 left-8 bg-primary-violet text-white text-[10px] font-black px-4 py-1 rounded-full animate-pulse">BEST MATCH</div>
                    )}
                    <h4 className="text-xl font-black text-white mb-4 leading-tight">{name}</h4>
                    <div className="mb-6 flex items-baseline gap-2">
                      <span className={`text-4xl font-black ${i === 0 ? 'text-primary-violet' : 'text-white'}`}>{match}%</span>
                      <span className="text-xs text-slate-500 font-bold uppercase">Alignment</span>
                    </div>
                    {/* Gradient Bar */}
                    <div className="h-2 w-full bg-slate-800 rounded-full mb-6 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-1000 ${i === 0 ? 'bg-gradient-to-r from-primary-violet to-purple-400' : 'bg-slate-600'}`}
                        style={{ width: `${match}%` }}
                      />
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed font-medium">{desc}</p>
                  </div>
                )
              })}
            </div>
          </motion.div>

          {/* Skill Gaps */}
          <motion.div variants={itemVariants} className="space-y-6">
            <h3 className="text-xl font-black text-white uppercase tracking-widest flex items-center gap-3">
              <Code className="w-5 h-5 text-blue-400" />
              Critical Skill Gaps
            </h3>
            <div className="bg-[#1E293B] rounded-2xl border border-white/5 overflow-hidden shadow-2xl">
              {(analysis.skill_gaps || []).map((item, i) => {
                const name = item.skill || item.skill_name || item.name || 'Skill'
                const has = item.have ?? item.has ?? item.owned ?? false
                const p = item.priority ?? item.priority_level ?? item.level ?? 0
                const accent = has ? 'border-l-green-500' : p === 1 ? 'border-l-red-500' : 'border-l-yellow-500'
                return (
                  <div key={i} className={`flex items-center justify-between p-6 border-b border-white/5 last:border-0 border-l-4 ${accent} hover:bg-white/[0.02] transition-colors`}>
                    <div className="flex items-center gap-4">
                      {has ? <CheckCircle className="w-6 h-6 text-green-500" /> : <AlertTriangle className="w-6 h-6 text-yellow-500" />}
                      <span className="font-bold text-lg text-white">{name}</span>
                    </div>
                    <span className={`px-4 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${has ? 'bg-green-500/10 text-green-500' : p === 1 ? 'bg-red-500/10 text-red-500' : 'bg-yellow-500/10 text-yellow-500'}`}>
                      {has ? 'Verified Level' : `Priority ${p}`}
                    </span>
                  </div>
                )
              })}
            </div>
          </motion.div>

          {/* Roadmap */}
          <motion.div variants={itemVariants} className="space-y-6 pb-12">
            <h3 className="text-xl font-black text-white uppercase tracking-widest flex items-center gap-3">
              <Calendar className="w-5 h-5 text-primary-violet" />
              Strategic {analysis.roadmap?.duration_months || 6}-Month Growth Path
            </h3>
            <div className="bg-[#1E293B] rounded-2xl p-10 border border-white/5 relative">
              <div className="absolute left-[3.35rem] top-24 bottom-24 w-0.5 bg-gradient-to-b from-primary-violet/50 via-primary-violet/20 to-transparent" />
              {analysis.roadmap?.milestones?.map((m, i) => (
                <div key={i} className="flex gap-8 mb-12 last:mb-0 relative group">
                  <div className="relative z-10 w-12 h-12 rounded-full bg-[#0F172A] border-4 border-primary-violet text-primary-violet flex items-center justify-center font-black text-xl shadow-[0_0_15px_rgba(108,63,200,0.4)] group-hover:scale-110 transition-transform">
                    {m.week}
                  </div>
                  <div className="flex-1 bg-slate-900/40 p-8 rounded-2xl border border-white/5 group-hover:border-primary-violet/30 transition-all hover:bg-slate-900/60">
                    <h4 className="text-xl font-black text-white mb-2 leading-tight">{m.title}</h4>
                    <p className="text-sm text-slate-400 font-medium leading-relaxed mb-6 italic opacity-80">"{m.description}"</p>
                    <div className="flex flex-wrap gap-2">
                      {m.skills?.map((s, si) => (
                        <span key={si} className="text-[10px] font-black uppercase tracking-widest px-3 py-1 bg-primary-violet/10 text-primary-violet rounded-lg border border-primary-violet/20">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* CTA */}
          <motion.div variants={itemVariants} className="text-center bg-gradient-to-b from-transparent to-primary-violet/10 rounded-3xl p-12">
            <Link href="/jobs">
              <Button className="bg-primary-violet hover:bg-primary-violet/90 text-white text-xl font-black px-12 py-8 rounded-2xl shadow-2xl hover:shadow-primary-violet/30 transition-all gap-4">
                Accelerate My Career Launch
                <ArrowRight className="w-6 h-6" />
              </Button>
            </Link>
          </motion.div>
        </motion.div>
      </main>
    </div>
  )
}
