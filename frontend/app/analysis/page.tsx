'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
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
interface ResumeScore {
  overall: number
  breakdown: {
    skills_match: number
    github_activity: number
    leetcode_strength: number
    certifications: number
    resume_quality: number
  }
  summary: string
}

interface SalaryInsights {
  currency: string
  entry_level: string
  mid_level: string
  senior_level: string
  note: string
}

interface TopCompany {
  name: string
  type: string
  why: string
}

interface Certification {
  name: string
  provider: string
  relevance: string
  url: string
  why: string
}

interface AnalysisData {
  experience_level: string
  strengths: string[]
  career_paths: CareerPath[]
  skill_gaps: SkillGap[]
  skill_gap?: SkillGap[]
  roadmap: Roadmap
  resume_score?: ResumeScore        // ADD
  salary_insights?: SalaryInsights  // ADD
  top_companies?: TopCompany[]      // ADD
  certifications?: Certification[]  // ADD
}


export default function AnalysisPage() {

  const isMountedRef = useRef(true)
  
  useEffect(() => {
    return () => { isMountedRef.current = false }
  }, [])
  
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
        resume_score: (record.resume_score?.overall != null ? record.resume_score : null) 
                      || analysisObj.resume_score || null,
        salary_insights: (record.salary_insights?.entry_level ? record.salary_insights : null) 
                         || analysisObj.salary_insights || null,
        top_companies: (Array.isArray(record.top_companies) && record.top_companies.length > 0 
                       ? record.top_companies : null) || analysisObj.top_companies || [],
        certifications: (Array.isArray(record.certifications) && record.certifications.length > 0 
                        ? record.certifications : null) || analysisObj.certifications || [],

      },
      pathDetails,
      firstPathName,
    }
  }
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [user, setUser] = useState<{ id: string } | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null)
  const [selectedPath, setSelectedPath] = useState<string>('')
  const [pathDetails, setPathDetails] = useState<Record<string, { skill_gaps: SkillGap[], roadmap: Roadmap }>>({})
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

      const runData = await response.json()
      const jobId = runData?.data?.job_id
      
      if (!jobId) throw new Error('No job ID returned from analysis start')

      // Poll for completion - up to 10 times every 3 seconds
      for (let i = 0; i < 10; i++) {
        await new Promise(resolve => setTimeout(resolve, 3000))
        if (!isMountedRef.current) return

        // CORRECT — backticks
        const jobRes = await fetch(`${apiUrl}/api/v1/analysis/job/${jobId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })

        if(!jobRes.ok) continue
        
        const jobData = await jobRes.json()
        const job = jobData?.data

        if(job?.status === 'failed'){
          setError('Analysis failed. Please try Again..')
          setAnalyzing(false)
          setLoading(false)
          return
        }
        if(job?.status === 'completed'){
          // correct
          const finalRes = await fetch(`${apiUrl}/api/v1/analysis/`, {
            headers: { 'Authorization': `Bearer ${token}` }
          })
          if(finalRes.ok) {
            const finalData = await finalRes.json()
            if(finalData?.success && finalData?.data?.analysis){
              const{ analysis, pathDetails, firstPathName } = parseAnalysisRecord(finalData.data.analysis)
              if(!isMountedRef.current) return  
              setAnalysis(analysis)
              setPathDetails(pathDetails)
              setSelectedPath(firstPathName)
            }
          }
          setAnalyzing(false)
          setLoading(false)
          return
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

      if (data?.success && data?.data?.exists && data?.data?.analysis) {
        const { analysis, pathDetails, firstPathName } = parseAnalysisRecord(data.data.analysis)
        setAnalysis(analysis)
        setPathDetails(pathDetails)
        setSelectedPath(firstPathName)
      }else {
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
    
    
    // backgroung colour


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
                  <span className="text-xs font-black uppercase tracking-widest text-primary-violet">AI Analysis</span>
                </div>
                <h2 className="text-4xl font-black text-white mb-2">
                  {analysis.experience_level}
                </h2>
                <p className="text-slate-400 font-medium">AI-estimated based on your real GitHub and LeetCode activity</p>
              </div>
              <div className={`px-8 py-4 rounded-xl border-2 font-black text-xl uppercase tracking-tighter ${getExperienceStyles(analysis.experience_level)}`}>
                {analysis.experience_level} Estimated
              </div>
            </div>
          </motion.div>
          <motion.div variants={itemVariants} className="flex justify-end">
            <button
              onClick={() => user && runAnalysis(user.id)}
              disabled={analyzing}
              className="flex items-center gap-2 px-6 py-3 bg-slate-800 hover:bg-slate-700 border border-white/10 hover:border-primary-violet/40 rounded-xl text-sm font-black text-slate-300 hover:text-white transition-all disabled:opacity-50"
            >
              <Zap className="w-4 h-4" />
              Re-analyze Profile
            </button>
          </motion.div>
              {/* Resume Score Card */}
              {analysis.resume_score && (
                <motion.div variants={itemVariants} className="space-y-6">
                  <h3 className="text-xl font-black text-white uppercase tracking-widest flex items-center gap-3">
                    <Award className="w-5 h-5 text-yellow-400" />
                    Resume Score
                  </h3>
                  <div className="bg-[#1E293B] rounded-2xl p-8 border border-white/5">
                    <div className="flex flex-col md:flex-row items-center gap-8 mb-8">
                      {/* Radial Score */}
                      <div className="relative w-32 h-32 flex-shrink-0">
                        <svg className="w-32 h-32 -rotate-90" viewBox="0 0 120 120">
                          <circle cx="60" cy="60" r="54" fill="none" stroke="#1E293B" strokeWidth="12"/>
                          <circle cx="60" cy="60" r="54" fill="none" stroke="#6C3FC8" strokeWidth="12"
                            strokeDasharray={`${(analysis.resume_score.overall / 100) * 339} 339`}
                            strokeLinecap="round"/>
                        </svg>
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                          <span className="text-3xl font-black text-white">{analysis.resume_score.overall}</span>
                          <span className="text-xs text-slate-400 font-bold">/100</span>
                        </div>
                      </div>
                      <div className="flex-1 w-full">
                        <p className="text-slate-300 font-medium mb-6 italic">"{analysis.resume_score.summary}"</p>
                        <div className="space-y-3">
                          {Object.entries(analysis.resume_score.breakdown || {}).map(([key, val]) => (
                            <div key={key} className="flex items-center gap-4">
                              <span className="text-xs font-bold text-slate-400 uppercase tracking-widest w-36 flex-shrink-0">
                                {key.replace(/_/g, ' ')}
                              </span>
                              <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-gradient-to-r from-primary-violet to-purple-400 rounded-full transition-all duration-1000"
                                  style={{ width: `${val as number}%` }}
                                />
                              </div>
                              <span className="text-xs font-black text-white w-8 text-right">{val as number}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
                
              {/* Salary Insights */}
              {analysis.salary_insights && (
                <motion.div variants={itemVariants} className="space-y-6">
                  <h3 className="text-xl font-black text-white uppercase tracking-widest flex items-center gap-3">
                    <TrendingUp className="w-5 h-5 text-green-400" />
                    Salary Insights
                  </h3>
                  <div className="grid grid-cols-3 gap-4">
                    {[
                      { label: 'Entry Level', value: analysis.salary_insights.entry_level, color: 'text-blue-400' },
                      { label: 'Mid Level', value: analysis.salary_insights.mid_level, color: 'text-primary-violet' },
                      { label: 'Senior Level', value: analysis.salary_insights.senior_level, color: 'text-yellow-400' },
                    ].map((item, i) => (
                      <div key={i} className="bg-[#1E293B] rounded-2xl p-6 border border-white/5 text-center">
                        <p className="text-xs font-black uppercase tracking-widest text-slate-400 mb-2">{item.label}</p>
                        <p className={`text-2xl font-black ${item.color}`}>{item.value}</p>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-slate-500 font-medium">{analysis.salary_insights.note}</p>
                </motion.div>
              )}
                
              {/* Top Companies */}
              {analysis.top_companies && analysis.top_companies.length > 0 && (
                <motion.div variants={itemVariants} className="space-y-6">
                  <h3 className="text-xl font-black text-white uppercase tracking-widest flex items-center gap-3">
                    <Sparkles className="w-5 h-5 text-blue-400" />
                    Top Companies For You
                  </h3>
                  <div className="grid md:grid-cols-2 gap-4">
                    {analysis.top_companies.map((company, i) => (
                      <div key={i} className="bg-[#1E293B] rounded-2xl p-6 border border-white/5 flex items-start gap-4 hover:border-primary-violet/30 transition-all">
                        <div className="w-10 h-10 rounded-xl bg-primary-violet/10 border border-primary-violet/20 flex items-center justify-center font-black text-primary-violet flex-shrink-0">
                          {company.name[0]}
                        </div>
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-black text-white">{company.name}</span>
                            <span className="text-[10px] font-black uppercase tracking-widest px-2 py-0.5 bg-slate-700 text-slate-400 rounded-full">{company.type}</span>
                          </div>
                          <p className="text-xs text-slate-400 font-medium">{company.why}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
              {/* Certifications */}
              {analysis.certifications && analysis.certifications.length > 0 && (
                <motion.div variants={itemVariants} className="space-y-6">
                  <h3 className="text-xl font-black text-white uppercase tracking-widest flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-green-400" />
                    Recommended Certifications
                  </h3>
                  <div className="grid md:grid-cols-2 gap-4">
                    {analysis.certifications.map((cert, i) => (
                      <a key={i} href={cert.url} target="_blank" rel="noopener noreferrer"
                        className="bg-[#1E293B] rounded-2xl p-6 border border-white/5 hover:border-primary-violet/30 transition-all group block">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <p className="font-black text-white group-hover:text-primary-violet transition-colors">{cert.name}</p>
                            <p className="text-xs text-slate-400 font-medium">{cert.provider}</p>
                          </div>
                          <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full ${cert.relevance === 'High' ? 'bg-green-500/10 text-green-500' : 'bg-yellow-500/10 text-yellow-500'}`}>
                            {cert.relevance}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 font-medium">{cert.why}</p>
                      </a>
                    ))}
                  </div>
                </motion.div>
              )}

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
                  <div
                    key={i}
                    onClick={() => setSelectedPath(name)}
                    className={`bg-[#1E293B] rounded-2xl p-8 border border-white/5 relative group transition-all hover:bg-[#1E293B]/80 cursor-pointer ${selectedPath === name ? 'shadow-[0_0_30px_rgba(108,63,200,0.3)] ring-2 ring-primary-violet' : i === 0 && !selectedPath ? 'shadow-[0_0_30px_rgba(108,63,200,0.15)] ring-2 ring-primary-violet/30' : ''}`}
                  >
                    {i === 0 && (
                      <div className="absolute -top-3 left-8 bg-primary-violet text-white text-[10px] font-black px-4 py-1 rounded-full animate-pulse">BEST MATCH</div>
                    )}
                    <h4 className="text-xl font-black text-white mb-4 leading-tight">{name}</h4>
                    <div className="mb-6 flex items-baseline gap-2">
                      <span className={`text-4xl font-black ${selectedPath === name || (i === 0 && !selectedPath) ? 'text-primary-violet' : 'text-white'}`}>{match}%</span>
                      <span className="text-xs text-slate-500 font-bold uppercase">Alignment</span>
                    </div>
                    {/* Gradient Bar */}
                    <div className="h-2 w-full bg-slate-800 rounded-full mb-6 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-1000 ${selectedPath === name || (i === 0 && !selectedPath) ? 'bg-gradient-to-r from-primary-violet to-purple-400' : 'bg-slate-600'}`}
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
            {selectedPath && (
              <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mb-2">
                Showing roadmap for: <span className="text-primary-violet">{selectedPath}</span>
              </p>
            )}
            <div className="bg-[#1E293B] rounded-2xl border border-white/5 overflow-hidden shadow-2xl">
              {(pathDetails[selectedPath]?.skill_gaps || analysis.skill_gaps || []).map((item, i) => {
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
              Strategic {(pathDetails[selectedPath]?.roadmap || analysis.roadmap)?.duration_months || 6}-Month Growth Path
            </h3>
            <div className="bg-[#1E293B] rounded-2xl p-10 border border-white/5 relative">
              <div className="absolute left-[3.35rem] top-24 bottom-24 w-0.5 bg-gradient-to-b from-primary-violet/50 via-primary-violet/20 to-transparent" />
              {(pathDetails[selectedPath]?.roadmap || analysis.roadmap)?.milestones?.map((m, i) => (
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
