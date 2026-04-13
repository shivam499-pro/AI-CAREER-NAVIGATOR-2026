'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  Brain, AlertTriangle, Sparkles, TrendingUp, 
  Target, CheckCircle, Clock, Zap, Loader2
} from 'lucide-react'

interface CareerBrainData {
  job_readiness_score: number
  skill_insights: {
    strong: string[]
    weak: string[]
    missing: string[]
  }
  behavioral_insights: string[]
  recommendations: string[]
  alerts: string[]
  progress_summary: {
    total_applications: number
    total_interviews: number
    total_offers: number
    total_rejections: number
    saved_jobs: number
    interview_sessions: number
  }
  streak: number
  rank: string
  level: number
}

interface CareerCoachProps {
  compact?: boolean
}

export default function CareerCoach({ compact = false }: CareerCoachProps) {
  const [brain, setBrain] = useState<CareerBrainData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadCareerBrain()
  }, [])

  const loadCareerBrain = async () => {
    try {
      const supabase = await import('@/lib/supabase')
      const { data: { session } } = await supabase.supabase.auth.getSession()
      
      const headers: Record<string, string> = {}
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/career-brain`, { headers })

      if (response.ok) {
        const data = await response.json()
        setBrain(data)
      } else {
        setError('Failed to load career data')
      }
    } catch (err) {
      setError('Unable to connect to career service')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-[#1E293B] rounded-3xl p-6 border border-white/5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
            <Brain className="w-5 h-5 text-purple-400" />
          </div>
          <h3 className="font-black text-white uppercase tracking-widest text-sm">AI Career Coach</h3>
        </div>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
        </div>
      </div>
    )
  }

  if (error || !brain) {
    return (
      <div className="bg-[#1E293B] rounded-3xl p-6 border border-white/5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
            <Brain className="w-5 h-5 text-purple-400" />
          </div>
          <h3 className="font-black text-white uppercase tracking-widest text-sm">AI Career Coach</h3>
        </div>
        <p className="text-slate-400 text-sm">Complete your profile to get personalized insights.</p>
      </div>
    )
  }

  // Color based on score
  const scoreColor = brain.job_readiness_score >= 80 ? 'text-green-400' :
                     brain.job_readiness_score >= 60 ? 'text-yellow-400' :
                     'text-red-400'

  const scoreBg = brain.job_readiness_score >= 80 ? 'bg-green-500/20 border-green-500/40' :
                  brain.job_readiness_score >= 60 ? 'bg-yellow-500/20 border-yellow-500/40' :
                  'bg-red-500/20 border-red-500/40'

  if (compact) {
    // Compact view for dashboard
    return (
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-[#1E293B] rounded-3xl p-6 border border-white/5 hover:border-purple-500/30 transition-all"
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
              <Brain className="w-5 h-5 text-purple-400" />
            </div>
            <h3 className="font-black text-white uppercase tracking-widest text-sm">AI Career Coach</h3>
          </div>
          <div className={`text-2xl font-black ${scoreColor}`}>
            {brain.job_readiness_score}%
          </div>
        </div>

        {/* Top Recommendation */}
        {brain.recommendations[0] && (
          <div className="p-3 bg-purple-500/10 rounded-xl border border-purple-500/20 mb-3">
            <div className="flex items-start gap-2">
              <Sparkles className="w-4 h-4 text-purple-400 mt-0.5" />
              <p className="text-xs font-bold text-white leading-tight">
                {brain.recommendations[0]}
              </p>
            </div>
          </div>
        )}

        {/* Alerts */}
        {brain.alerts.length > 0 && (
          <div className="flex items-center gap-2 text-red-400">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-[10px] font-bold">{brain.alerts[0]}</span>
          </div>
        )}

        {/* Streak & Rank */}
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/5">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-yellow-400" />
            <span className="text-xs font-black text-slate-400">{brain.streak} day streak</span>
          </div>
          <span className="text-[10px] font-black text-purple-400 uppercase">{brain.rank}</span>
        </div>
      </motion.div>
    )
  }

  // Full view
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-[#1E293B] rounded-[2.5rem] p-8 border border-white/5"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-purple-500/20 flex items-center justify-center border border-purple-500/30">
            <Brain className="w-7 h-7 text-purple-400" />
          </div>
          <div>
            <h2 className="text-2xl font-black text-white uppercase tracking-tight">Your AI Career Coach</h2>
            <p className="text-slate-400 text-sm">Personalized insights and recommendations</p>
          </div>
        </div>
        
        {/* Score */}
        <div className={`w-24 h-24 rounded-3xl ${scoreBg} border-2 flex flex-col items-center justify-center`}>
          <span className={`text-3xl font-black ${scoreColor}`}>{brain.job_readiness_score}</span>
          <span className="text-[8px] font-black text-slate-500 uppercase tracking-widest">Ready</span>
        </div>
      </div>

      {/* Alerts */}
      {brain.alerts.length > 0 && (
        <div className="mb-6 space-y-2">
          {brain.alerts.map((alert, i) => (
            <div key={i} className="flex items-center gap-3 p-4 bg-red-500/10 rounded-xl border border-red-500/20">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              <span className="text-sm font-bold text-red-300">{alert}</span>
            </div>
          ))}
        </div>
      )}

      {/* Recommendations */}
      <div className="mb-8">
        <h3 className="text-xs font-black text-purple-400 uppercase tracking-widest mb-4 flex items-center gap-2">
          <Sparkles className="w-4 h-4" /> Top Recommendations
        </h3>
        <div className="space-y-3">
          {brain.recommendations.slice(0, 3).map((rec, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              className="flex items-start gap-3 p-4 bg-[#0F172A]/50 rounded-xl border border-white/5"
            >
              <div className="w-6 h-6 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0">
                <span className="text-[10px] font-black text-purple-400">{i + 1}</span>
              </div>
              <p className="text-sm font-bold text-white">{rec}</p>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Skill Insights */}
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        {/* Strong Skills */}
        <div className="p-4 bg-green-500/10 rounded-xl border border-green-500/20">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle className="w-4 h-4 text-green-400" />
            <span className="text-[10px] font-black text-green-400 uppercase tracking-widest">Your Strengths</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {brain.skill_insights.strong.slice(0, 5).map((skill, i) => (
              <span key={i} className="px-2 py-1 bg-green-500/20 rounded-full text-[10px] font-bold text-green-300">
                {skill}
              </span>
            ))}
          </div>
        </div>

        {/* Missing Skills */}
        <div className="p-4 bg-red-500/10 rounded-xl border border-red-500/20">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <span className="text-[10px] font-black text-red-400 uppercase tracking-widest">Skills to Learn</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {brain.skill_insights.missing.slice(0, 5).map((skill, i) => (
              <span key={i} className="px-2 py-1 bg-red-500/20 rounded-full text-[10px] font-bold text-red-300">
                {skill}
              </span>
            ))}
          </div>
        </div>

        {/* Weak Skills */}
        <div className="p-4 bg-yellow-500/10 rounded-xl border border-yellow-500/20">
          <div className="flex items-center gap-2 mb-3">
            <Target className="w-4 h-4 text-yellow-400" />
            <span className="text-[10px] font-black text-yellow-400 uppercase tracking-widest">Needs Practice</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {brain.skill_insights.weak.slice(0, 5).map((skill, i) => (
              <span key={i} className="px-2 py-1 bg-yellow-500/20 rounded-full text-[10px] font-bold text-yellow-300">
                {skill}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Progress Summary */}
      <div className="grid grid-cols-3 md:grid-cols-6 gap-4 p-6 bg-[#0F172A]/50 rounded-2xl border border-white/5">
        <div className="text-center">
          <div className="text-2xl font-black text-white">{brain.progress_summary.total_applications}</div>
          <div className="text-[8px] font-black text-slate-500 uppercase">Applied</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-black text-blue-400">{brain.progress_summary.total_interviews}</div>
          <div className="text-[8px] font-black text-slate-500 uppercase">Interviews</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-black text-green-400">{brain.progress_summary.total_offers}</div>
          <div className="text-[8px] font-black text-slate-500 uppercase">Offers</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-black text-red-400">{brain.progress_summary.total_rejections}</div>
          <div className="text-[8px] font-black text-slate-500 uppercase">Rejected</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-black text-yellow-400">{brain.streak}</div>
          <div className="text-[8px] font-black text-slate-500 uppercase">Streak</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-black text-purple-400">{brain.level}</div>
          <div className="text-[8px] font-black text-slate-500 uppercase">Level</div>
        </div>
      </div>
    </motion.div>
  )
}