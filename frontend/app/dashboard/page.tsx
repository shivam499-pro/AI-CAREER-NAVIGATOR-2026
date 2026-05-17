'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { supabase } from '@/lib/supabase'
import Navbar from '@/components/Navbar'
import ProgressTracker from '@/components/ProgressTracker'
import CareerCoach from '@/components/CareerCoach'
import {
  Brain, ChevronRight, Sparkles, Target,
  Briefcase, Activity, Clock, CheckCircle,
  XCircle, MessageSquare, Zap, TrendingUp,
  ArrowRight, Star, Shield, AlertTriangle,
  Mic, FileText, Award, Code, GitBranch
} from 'lucide-react'

// ─── Types ───────────────────────────────────────────────────────────────────

interface CareerBrainData {
  job_readiness_score: number
  recommendations: string[]
  alerts: string[]
  streak: number
  rank: string
  level: number
  skill_insights: { strong: string[]; weak: string[]; missing: string[] }
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

interface AnalysisSummary {
  experience_level: string
  resume_score: ResumeScore | null
  best_match: { name: string; percentage: number } | null
  roadmap_total: number
  roadmap_completed: number
  skill_gaps_count: number
  best_career_path: string
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function parseAnalysisSummary(record: any): AnalysisSummary {
  const analysisObj = record?.analysis || {}
  const experienceLevel =
    analysisObj.analysis?.experience_level ||
    analysisObj.experience_level ||
    record.experience_level ||
    'Beginner'

  const resumeScore =
    record.resume_score?.overall != null
      ? record.resume_score
      : analysisObj.resume_score || null

  const careerPaths = record.career_paths || analysisObj.career_paths || []
  const bestPath =
    Array.isArray(careerPaths) && careerPaths.length > 0
      ? careerPaths[0]
      : null
  const bestMatch = bestPath
    ? {
      name:
        bestPath.name ||
        bestPath.career_name ||
        bestPath.title ||
        'Unknown',
      percentage:
        bestPath.match_percentage ??
        bestPath.match ??
        bestPath.percentage ??
        0,
    }
    : null

  const firstPathName = bestMatch?.name || ''

  const pathDetails = record?.path_details || {}
  const pathSpecificRoadmap = firstPathName ? pathDetails[firstPathName]?.roadmap : null
  const roadmap = pathSpecificRoadmap ||
    analysisObj.roadmap ||
    record.roadmap ||
    { milestones: [] }
  const roadmapTotal = roadmap?.milestones?.length || 0

  const skillGaps =
    analysisObj.skill_gaps ||
    analysisObj.skill_gap ||
    record.skill_gaps ||
    []

  return {
    experience_level: experienceLevel,
    resume_score: resumeScore,
    best_match: bestMatch,
    roadmap_total: roadmapTotal,
    roadmap_completed: 0, // filled after roadmap progress fetch
    skill_gaps_count: Array.isArray(skillGaps) ? skillGaps.length : 0,
    best_career_path: bestMatch?.name || '',
  }
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [user, setUser] = useState<{ email: string; id?: string } | null>(null)
  const [loading, setLoading] = useState(true)

  // Data states
  const [brain, setBrain] = useState<CareerBrainData | null>(null)
  const [brainLoading, setBrainLoading] = useState(true)
  const [appStats, setAppStats] = useState({ applied: 0, interview: 0, rejected: 0, offer: 0 })
  const [analysisSummary, setAnalysisSummary] = useState<AnalysisSummary | null>(null)
  const [roadmapCompleted, setRoadmapCompleted] = useState(0)

  const formatUsername = (email: string) => {
    const prefix = email.split('@')[0]
    const match = prefix.match(/^[a-zA-Z]+/)
    if (match) return match[0].charAt(0).toUpperCase() + match[0].slice(1).toLowerCase()
    return prefix.charAt(0).toUpperCase() + prefix.slice(1)
  }

  // ── Fetchers ──────────────────────────────────────────────────────────────

  const getAuthHeaders = async (): Promise<Record<string, string>> => {
    const { data: { session } } = await supabase.auth.getSession()
    return {
      'Content-Type': 'application/json',
      ...(session?.access_token
        ? { Authorization: `Bearer ${session.access_token}` }
        : {}),
    }
  }

  const loadCareerBrain = async () => {
    try {
      const headers = await getAuthHeaders()
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${apiUrl}/api/v1/career-brain`, { headers })
      if (res.ok) setBrain(await res.json())
    } catch { /* no brain data */ }
    finally { setBrainLoading(false) }
  }

  const loadAppStats = async () => {
    try {
      const headers = await getAuthHeaders()
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${apiUrl}/api/v1/jobs/applications`, { headers })
      if (res.ok) {
        const data = await res.json()
        setAppStats(data.status_counts || { applied: 0, interview: 0, rejected: 0, offer: 0 })
      }
    } catch { /* keep zeros */ }
  }

  const loadAnalysisSummary = async () => {
    try {
      const headers = await getAuthHeaders()
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${apiUrl}/api/v1/analysis/`, { headers })
      if (!res.ok) return
      const data = await res.json()
      if (data?.success && data?.data?.analysis) {
        const summary = parseAnalysisSummary(data.data.analysis)
        setAnalysisSummary(summary)

        // Fetch roadmap progress for best career path
        if (summary.best_career_path) {
          try {
            const progRes = await fetch(
              `${apiUrl}/api/v1/roadmap/progress/${encodeURIComponent(summary.best_career_path)}`,
              { headers }
            )
            if (progRes.ok) {
              const progData = await progRes.json()
              const progressMap: Record<number, string> = progData.progress_map || {}
              const completed = Object.values(progressMap).filter(s => s === 'completed').length
              setRoadmapCompleted(completed)
              setAnalysisSummary(prev => prev ? { ...prev, roadmap_completed: completed } : prev)
            }
          } catch { /* roadmap progress unavailable */ }
        }
      }
    } catch { /* no analysis data */ }
  }

  // ── Init ──────────────────────────────────────────────────────────────────

  useEffect(() => {
    const init = async () => {
      try {
        const { data: { user }, error } = await supabase.auth.getUser()
        if (error || !user || !user.email) {
          window.location.href = '/auth/login'
          return
        }
        setUser({ email: user.email, id: user.id })
        await Promise.all([
          loadCareerBrain(),
          loadAppStats(),
          loadAnalysisSummary(),
        ])
      } catch {
        window.location.href = '/auth/login'
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500" />
      </div>
    )
  }

  // ── Derived state ─────────────────────────────────────────────────────────

  const isNewUser = !brain && !brainLoading && !analysisSummary
  const totalApplications =
    appStats.applied + appStats.interview + appStats.rejected + appStats.offer
  const hasActivity = totalApplications > 0
  const resumeQualityZero =
    analysisSummary?.resume_score?.breakdown?.resume_quality === 0
  const roadmapPct =
    analysisSummary && analysisSummary.roadmap_total > 0
      ? Math.round((roadmapCompleted / analysisSummary.roadmap_total) * 100)
      : 0

  // ── Animation variants ────────────────────────────────────────────────────

  const stagger = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
  }
  const fadeUp = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-[#0F172A] text-white">
      <Navbar />

      <main className="container mx-auto px-4 py-10 max-w-6xl flex flex-col gap-10">

        {/* ── WELCOME ──────────────────────────────────────────────────────── */}
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
          <h1 className="text-4xl font-extrabold tracking-tight flex items-center gap-3 flex-wrap">
            Welcome,{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-violet-300">
              {user?.email ? formatUsername(user.email) : 'Explorer'}
            </span>!
          </h1>
          <p className="text-slate-400 mt-2 font-medium">
            {brain
              ? `Level ${brain.level} · ${brain.rank} · ${brain.streak} day streak 🔥`
              : 'Your AI-powered career copilot. Complete your profile to unlock insights.'}
          </p>
        </motion.div>

        {/* ── HERO STATS BAR ───────────────────────────────────────────────── */}
        {brain && (
          <motion.div variants={stagger} initial="hidden" animate="visible" className="grid grid-cols-2 md:grid-cols-4 gap-4">

            {/* Job Readiness — hero metric */}
            <motion.div variants={fadeUp} className="col-span-2 md:col-span-1">
              <div className="bg-[#1E293B] rounded-2xl p-5 border border-purple-500/30 shadow-[0_0_30px_rgba(139,92,246,0.15)] relative overflow-hidden h-full">
                <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent" />
                <p className="text-[10px] font-black text-purple-400 uppercase tracking-widest mb-1">Job Readiness</p>
                <div className="flex items-end gap-2 mb-2">
                  <span className={`text-5xl font-black ${brain.job_readiness_score >= 80 ? 'text-green-400' :
                    brain.job_readiness_score >= 60 ? 'text-yellow-400' : 'text-red-400'
                    }`}>{brain.job_readiness_score}</span>
                  <span className="text-slate-400 font-bold pb-2">/ 100</span>
                </div>
                <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-1000 ${brain.job_readiness_score >= 80 ? 'bg-green-400' :
                      brain.job_readiness_score >= 60 ? 'bg-yellow-400' : 'bg-red-400'
                      }`}
                    style={{ width: `${brain.job_readiness_score}%` }}
                  />
                </div>
              </div>
            </motion.div>

            {/* Streak */}
            <motion.div variants={fadeUp}>
              <div className="bg-[#1E293B] rounded-2xl p-5 border border-white/5 h-full">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Streak</p>
                <div className="flex items-center gap-2">
                  <Zap className="w-5 h-5 text-yellow-400" />
                  <span className="text-4xl font-black text-white">{brain.streak}</span>
                </div>
                <p className="text-xs text-slate-500 font-medium mt-1">days active</p>
              </div>
            </motion.div>

            {/* Rank */}
            <motion.div variants={fadeUp}>
              <div className="bg-[#1E293B] rounded-2xl p-5 border border-white/5 h-full">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Rank</p>
                <div className="flex items-center gap-2">
                  <Star className="w-5 h-5 text-purple-400" />
                  <span className="text-xl font-black text-white truncate">{brain.rank}</span>
                </div>
                <p className="text-xs text-slate-500 font-medium mt-1">Level {brain.level}</p>
              </div>
            </motion.div>

            {/* Top Skill */}
            <motion.div variants={fadeUp}>
              <div className="bg-[#1E293B] rounded-2xl p-5 border border-white/5 h-full">
                {brain.skill_insights.strong.length > 0 ? (
                  <>
                    <p className="text-[10px] font-black text-green-400 uppercase tracking-widest mb-1">Top Skill</p>
                    <div className="flex items-center gap-2">
                      <Shield className="w-5 h-5 text-green-400" />
                      <span className="text-base font-black text-white truncate">{brain.skill_insights.strong[0]}</span>
                    </div>
                    <p className="text-xs text-slate-500 font-medium mt-1">+{brain.skill_insights.strong.length - 1} more</p>
                  </>
                ) : (
                  <>
                    <p className="text-[10px] font-black text-red-400 uppercase tracking-widest mb-1">Gap Alert</p>
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-red-400" />
                      <span className="text-sm font-black text-white truncate">{brain.skill_insights.missing[0] || 'Skills needed'}</span>
                    </div>
                    <p className="text-xs text-slate-500 font-medium mt-1">Go to Analysis</p>
                  </>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}

        {/* ── ANALYSIS SNAPSHOT (Resume + Career Match + Roadmap) ──────────── */}
        {analysisSummary && (
          <motion.div variants={stagger} initial="hidden" animate="visible" className="grid md:grid-cols-3 gap-4">

            {/* Resume Score */}
            <motion.div variants={fadeUp}>
              <Link href="/analysis">
                <div className={`bg-[#1E293B] rounded-2xl p-5 border h-full hover:border-purple-500/40 transition-all cursor-pointer group ${resumeQualityZero ? 'border-red-500/30' : 'border-white/5'
                  }`}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${resumeQualityZero ? 'bg-red-500/20' : 'bg-yellow-500/20'
                        }`}>
                        <FileText className={`w-4 h-4 ${resumeQualityZero ? 'text-red-400' : 'text-yellow-400'}`} />
                      </div>
                      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Resume Score</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-purple-400 transition-colors" />
                  </div>

                  {analysisSummary.resume_score ? (
                    <>
                      <div className="flex items-end gap-1 mb-3">
                        <span className={`text-4xl font-black ${analysisSummary.resume_score.overall >= 70 ? 'text-green-400' :
                          analysisSummary.resume_score.overall >= 50 ? 'text-yellow-400' : 'text-red-400'
                          }`}>{analysisSummary.resume_score.overall}</span>
                        <span className="text-slate-400 font-bold pb-1">/100</span>
                      </div>

                      {/* Sub-scores strip */}
                      <div className="space-y-1.5">
                        {Object.entries(analysisSummary.resume_score.breakdown || {}).map(([key, val]) => {
                          const label: Record<string, string> = {
                            skills_match: 'Skills',
                            github_activity: 'GitHub',
                            leetcode_strength: 'LeetCode',
                            certifications: 'Certs',
                            resume_quality: 'Resume File',
                          }
                          const isZero = (val as number) === 0
                          return (
                            <div key={key} className="flex items-center gap-2">
                              <span className={`text-[9px] font-black uppercase tracking-widest w-20 flex-shrink-0 ${isZero ? 'text-red-400' : 'text-slate-500'}`}>
                                {label[key] || key}
                              </span>
                              <div className="flex-1 h-1 bg-slate-800 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${isZero ? 'bg-red-500' : 'bg-gradient-to-r from-purple-600 to-violet-400'}`}
                                  style={{ width: `${val as number}%` }}
                                />
                              </div>
                              <span className={`text-[9px] font-black w-5 text-right ${isZero ? 'text-red-400' : 'text-slate-400'}`}>
                                {val as number}
                              </span>
                            </div>
                          )
                        })}
                      </div>

                      {/* Critical alert if resume file is missing */}
                      {resumeQualityZero && (
                        <div className="mt-3 flex items-center gap-2 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg">
                          <AlertTriangle className="w-3 h-3 text-red-400 flex-shrink-0" />
                          <span className="text-[10px] font-black text-red-400">Upload your resume to fix this</span>
                        </div>
                      )}
                    </>
                  ) : (
                    <p className="text-sm text-slate-400">Run analysis to get your score</p>
                  )}
                </div>
              </Link>
            </motion.div>

            {/* Best Career Match */}
            <motion.div variants={fadeUp}>
              <Link href="/analysis">
                <div className="bg-[#1E293B] rounded-2xl p-5 border border-white/5 h-full hover:border-purple-500/40 transition-all cursor-pointer group">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
                        <Target className="w-4 h-4 text-purple-400" />
                      </div>
                      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Best Match</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-purple-400 transition-colors" />
                  </div>

                  {analysisSummary.best_match ? (
                    <>
                      <div className="flex items-end gap-1 mb-1">
                        <span className="text-4xl font-black text-purple-400">{analysisSummary.best_match.percentage}</span>
                        <span className="text-slate-400 font-bold pb-1">%</span>
                      </div>
                      <p className="text-sm font-black text-white mb-3 leading-tight">{analysisSummary.best_match.name}</p>
                      <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-purple-600 to-violet-400 rounded-full transition-all duration-1000"
                          style={{ width: `${analysisSummary.best_match.percentage}%` }}
                        />
                      </div>
                      <div className="mt-2">
                        <span className="text-[10px] font-black text-purple-400 uppercase tracking-widest">Top alignment</span>
                      </div>
                    </>
                  ) : (
                    <p className="text-sm text-slate-400">Run analysis to see career paths</p>
                  )}
                </div>
              </Link>
            </motion.div>

            {/* Roadmap Progress */}
            <motion.div variants={fadeUp}>
              <Link href="/analysis">
                <div className="bg-[#1E293B] rounded-2xl p-5 border border-white/5 h-full hover:border-purple-500/40 transition-all cursor-pointer group">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                        <TrendingUp className="w-4 h-4 text-blue-400" />
                      </div>
                      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Roadmap</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-purple-400 transition-colors" />
                  </div>

                  {analysisSummary.roadmap_total > 0 ? (
                    <>
                      <div className="flex items-end gap-1 mb-1">
                        <span className="text-4xl font-black text-blue-400">{roadmapCompleted}</span>
                        <span className="text-slate-400 font-bold pb-1">/ {analysisSummary.roadmap_total}</span>
                      </div>
                      <p className="text-xs text-slate-500 font-medium mb-3">milestones completed</p>
                      <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-blue-600 to-cyan-400 rounded-full transition-all duration-1000"
                          style={{ width: `${roadmapPct}%` }}
                        />
                      </div>
                      <div className="mt-2 flex items-center justify-between">
                        <span className="text-[10px] font-black text-blue-400 uppercase tracking-widest">{roadmapPct}% done</span>
                        {roadmapCompleted === 0 && (
                          <span className="text-[10px] font-black text-slate-500">Start your first milestone</span>
                        )}
                      </div>
                    </>
                  ) : (
                    <p className="text-sm text-slate-400">Run analysis to generate roadmap</p>
                  )}
                </div>
              </Link>
            </motion.div>
          </motion.div>
        )}

        {/* ── RESUME UPLOAD ALERT (critical — resume quality = 0) ───────────── */}
        {resumeQualityZero && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <div className="bg-red-900/20 rounded-2xl p-5 border border-red-500/30 flex items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-xl bg-red-500/20 border border-red-500/30 flex items-center justify-center flex-shrink-0">
                  <AlertTriangle className="w-5 h-5 text-red-400" />
                </div>
                <div>
                  <p className="font-black text-white text-sm">Resume file missing — score impact: critical</p>
                  <p className="text-xs text-red-300/70 font-medium mt-0.5">
                    Resume quality is 0/100. Upload your resume to fix the biggest gap in your profile.
                  </p>
                </div>
              </div>
              <Link href="/resume" className="flex-shrink-0">
                <button className="bg-red-600 hover:bg-red-700 text-white font-black text-xs px-4 py-2.5 rounded-xl transition-all whitespace-nowrap">
                  Upload Resume
                </button>
              </Link>
            </div>
          </motion.div>
        )}

        {/* ── TODAY'S FOCUS ─────────────────────────────────────────────────── */}
        {brain?.recommendations?.[0] && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <div className="bg-gradient-to-r from-purple-900/40 to-violet-900/20 rounded-2xl p-6 border border-purple-500/30 flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-5 h-5 text-purple-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-black text-purple-400 uppercase tracking-widest mb-1">Today's Focus</p>
                <p className="text-white font-bold text-base leading-snug">{brain.recommendations[0]}</p>
                {brain.alerts?.[0] && (
                  <div className="flex items-center gap-2 mt-3 text-red-400">
                    <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                    <span className="text-xs font-bold">{brain.alerts[0]}</span>
                  </div>
                )}
              </div>
              <Link href="/analysis" className="flex-shrink-0">
                <div className="flex items-center gap-1 text-purple-400 text-xs font-bold hover:text-purple-300 transition-colors">
                  Full Report <ChevronRight className="w-4 h-4" />
                </div>
              </Link>
            </div>
          </motion.div>
        )}

        {/* ── NEW USER ONBOARDING CTA ───────────────────────────────────────── */}
        {isNewUser && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <div className="bg-[#1E293B] rounded-2xl p-8 border border-purple-500/20 text-center">
              <div className="w-14 h-14 rounded-2xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center mx-auto mb-4">
                <Brain className="w-7 h-7 text-purple-400" />
              </div>
              <h3 className="text-xl font-black text-white mb-2">Unlock Your Career Insights</h3>
              <p className="text-slate-400 text-sm mb-6 max-w-md mx-auto">
                Complete your profile and run your first analysis to get a personalized job readiness score,
                skill gap report, and AI recommendations.
              </p>
              <div className="flex flex-wrap gap-3 justify-center">
                <Link href="/analysis">
                  <button className="bg-purple-600 hover:bg-purple-700 text-white font-bold px-6 py-3 rounded-xl transition-all flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" /> Run Analysis
                  </button>
                </Link>
                <Link href="/profile">
                  <button className="bg-[#0F172A] hover:bg-slate-800 text-white font-bold px-6 py-3 rounded-xl border border-slate-700 transition-all flex items-center gap-2">
                    Complete Profile <ArrowRight className="w-4 h-4" />
                  </button>
                </Link>
              </div>
            </div>
          </motion.div>
        )}

        {/* ── PROGRESS + CAREER COACH ───────────────────────────────────────── */}
        <motion.div variants={stagger} initial="hidden" animate="visible" className="grid lg:grid-cols-2 gap-8 items-start">
          <motion.div variants={fadeUp}><ProgressTracker /></motion.div>
          <motion.div variants={fadeUp}><CareerCoach compact /></motion.div>
        </motion.div>

        {/* ── JOB PIPELINE ─────────────────────────────────────────────────── */}
        <motion.div variants={stagger} initial="hidden" animate="visible">
          <div className="flex items-center gap-4 mb-6">
            <h2 className="text-sm font-black text-white uppercase tracking-widest">Job Pipeline</h2>
            <div className="flex-1 border-t border-slate-800" />
            <Link href="/applications" className="text-xs text-purple-400 font-bold hover:text-purple-300 transition-colors flex items-center gap-1">
              View All <ChevronRight className="w-3 h-3" />
            </Link>
          </div>

          {!hasActivity ? (
            <motion.div variants={fadeUp}>
              <div className="bg-[#1E293B] rounded-2xl p-8 border border-white/5 flex flex-col items-center text-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center">
                  <Briefcase className="w-6 h-6 text-slate-500" />
                </div>
                <div>
                  <p className="font-bold text-white mb-1">No applications yet</p>
                  <p className="text-sm text-slate-400">Find jobs matched to your profile and start applying.</p>
                </div>
                <Link href="/jobs">
                  <button className="bg-[#0F172A] hover:bg-slate-800 border border-slate-700 text-white font-bold px-5 py-2.5 rounded-xl text-sm transition-all flex items-center gap-2">
                    <Briefcase className="w-4 h-4" /> Browse Jobs
                  </button>
                </Link>
              </div>
            </motion.div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { status: 'applied', label: 'Applied', colorClass: 'bg-yellow-500/20 border-yellow-500/40 text-yellow-400', icon: Clock },
                { status: 'interview', label: 'Interview', colorClass: 'bg-blue-500/20 border-blue-500/40 text-blue-400', icon: MessageSquare },
                { status: 'rejected', label: 'Rejected', colorClass: 'bg-red-500/20 border-red-500/40 text-red-400', icon: XCircle },
                { status: 'offer', label: 'Offer', colorClass: 'bg-green-500/20 border-green-500/40 text-green-400', icon: CheckCircle },
              ].map((stat, i) => {
                const Icon = stat.icon
                const count = appStats[stat.status as keyof typeof appStats] || 0
                return (
                  <motion.div key={i} variants={fadeUp}>
                    <Link href={`/applications${stat.status !== 'applied' ? '?status=' + stat.status : ''}`}>
                      <div className="bg-[#1E293B] rounded-2xl p-6 border border-white/5 hover:border-purple-500/30 transition-all cursor-pointer">
                        <div className={`w-12 h-12 rounded-xl ${stat.colorClass} border flex items-center justify-center mb-4`}>
                          <Icon className="w-6 h-6" />
                        </div>
                        <div className="text-3xl font-black text-white mb-1">{count}</div>
                        <div className="text-[10px] font-black uppercase text-slate-500 tracking-widest">{stat.label}</div>
                      </div>
                    </Link>
                  </motion.div>
                )
              })}
            </div>
          )}
        </motion.div>

        {/* ── QUICK ACTIONS ─────────────────────────────────────────────────── */}
        <motion.div variants={stagger} initial="hidden" animate="visible">
          <div className="flex items-center gap-4 mb-6">
            <h2 className="text-sm font-black text-white uppercase tracking-widest">Quick Actions</h2>
            <div className="flex-1 border-t border-slate-800" />
          </div>

          <div className="grid md:grid-cols-4 gap-4">
            {[
              {
                href: '/analysis',
                icon: TrendingUp,
                label: 'Run Analysis',
                desc: 'AI skill & role insights',
                badge: analysisSummary?.skill_gaps_count
                  ? `${analysisSummary.skill_gaps_count} gaps`
                  : null,
                badgeColor: 'bg-red-500/20 text-red-400',
              },
              {
                href: '/interview',
                icon: Mic,
                label: 'Practice Interview',
                desc: 'AI mock sessions',
                badge: brain?.streak ? `${brain.streak}d streak` : null,
                badgeColor: 'bg-yellow-500/20 text-yellow-400',
              },
              {
                href: '/jobs',
                icon: Briefcase,
                label: 'Find Jobs',
                desc: 'Market recommendations',
                badge: null,
                badgeColor: '',
              },
              {
                href: '/resume',
                icon: FileText,
                label: 'Resume Builder',
                desc: 'Upload & improve',
                badge: resumeQualityZero ? 'Missing!' : null,
                badgeColor: 'bg-red-500/20 text-red-400',
              },
            ].map((action, i) => (
              <motion.div key={i} variants={fadeUp}>
                <Link href={action.href}>
                  <div className="bg-[#1E293B] group rounded-xl p-6 border border-slate-800 border-l-4 border-l-purple-600 hover:shadow-[0_0_20px_rgba(139,92,246,0.2)] hover:bg-[#243147] transition-all cursor-pointer h-full relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/5 rounded-full blur-3xl -mr-16 -mt-16 group-hover:bg-purple-500/10 transition-colors" />
                    <div className="flex items-start justify-between mb-6">
                      <div className="w-12 h-12 rounded-lg bg-purple-500/10 flex items-center justify-center group-hover:scale-110 transition-all border border-purple-500/20">
                        <action.icon className="w-6 h-6 text-purple-400" />
                      </div>
                      {action.badge && (
                        <span className={`text-[10px] font-black px-2 py-1 rounded-full ${action.badgeColor}`}>
                          {action.badge}
                        </span>
                      )}
                    </div>
                    <div className="relative z-10">
                      <h3 className="font-bold text-white text-base mb-1">{action.label}</h3>
                      <p className="text-xs text-slate-400 leading-tight font-medium">{action.desc}</p>
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </motion.div>

      </main>
    </div>
  )
}