'use client'

import React, { useState, useEffect } from 'react'
import { Target, TrendingUp, AlertCircle, Loader2, Sparkles } from 'lucide-react'
import { motion } from 'framer-motion'
import { supabase } from '@/lib/supabase'

interface MatchFitData {
  score: number
  label: string
  role: string
  reason: string
  error?: string
}

export default function MatchFitScore() {
  const [data, setData] = useState<MatchFitData | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchMatchFit = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/profile/match-fit`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })
      const result = await response.json()
      setData(result)
    } catch (err) {
      console.error("Match fit fetch error:", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMatchFit()
  }, [])

  if (loading) return (
    <div className="bg-[#1E293B] rounded-2xl p-8 border border-slate-800 shadow-2xl flex items-center justify-center min-h-[350px] animate-pulse">
       <Loader2 className="w-10 h-10 animate-spin text-primary-violet" />
    </div>
  )

  if (!data || data.error) return null

  const isHighMatch = data.score >= 80
  const accentColor = isHighMatch ? '#FFD700' : '#6C3FC8'

  // Radial progress constants
  const radius = 60
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (data.score / 100) * circumference

  return (
    <div className="bg-[#1E293B] rounded-2xl p-8 border border-slate-800 shadow-[0_0_50px_rgba(108,63,200,0.05)] flex flex-col justify-between h-full relative overflow-hidden group">
      <div className="absolute top-0 right-0 w-full h-[2px] bg-gradient-to-l from-transparent via-primary-violet to-transparent opacity-50" />
      
      <div className="mb-6">
        <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-4">
               <div className="w-12 h-12 rounded-xl bg-primary-violet/10 flex items-center justify-center border border-primary-violet/20">
                  <Target className="w-6 h-6 text-primary-violet" />
               </div>
               <div>
                  <h3 className="text-xl font-bold text-white tracking-tight">Match Fit Score</h3>
                  <p className="text-sm text-slate-400 font-medium whitespace-nowrap">Compatibility for target role</p>
               </div>
            </div>
            {data.score > 0 && (
               <div className={`flex items-center gap-2 px-3 py-1 rounded-full border ${isHighMatch ? 'bg-yellow-500/10 border-yellow-500/20 text-[#FFD700]' : 'bg-primary-violet/10 border-primary-violet/20 text-primary-violet'}`}>
                  <TrendingUp className="w-3 h-3" />
                  <span className="text-[10px] font-bold uppercase tracking-widest">{isHighMatch ? 'Elite Match' : 'High Match'}</span>
               </div>
            )}
        </div>

        <div className="flex flex-col items-center justify-center py-4 relative">
          {/* Radial Progress Ring */}
          <div className="relative w-40 h-40 flex items-center justify-center">
            <svg className="w-full h-full -rotate-90">
              {/* Background circle */}
              <circle
                cx="80"
                cy="80"
                r={radius}
                className="stroke-slate-800"
                strokeWidth="10"
                fill="transparent"
              />
              {/* Animated Progress circle */}
              <motion.circle
                cx="80"
                cy="80"
                r={radius}
                stroke={accentColor}
                strokeWidth="10"
                fill="transparent"
                strokeDasharray={circumference}
                initial={{ strokeDashoffset: circumference }}
                animate={{ strokeDashoffset: offset }}
                transition={{ duration: 1.5, ease: "easeOut" }}
                strokeLinecap="round"
                className="drop-shadow-[0_0_10px_rgba(108,63,200,0.5)]"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <motion.span 
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.5, duration: 0.5 }}
                className={`text-4xl font-black ${isHighMatch ? 'text-[#FFD700]' : 'text-white'}`}
              >
                {data.score}%
              </motion.span>
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{data.label}</span>
            </div>
          </div>
          
          <div className="text-center mt-6">
            <p className="text-sm text-slate-300 font-medium">
              Target Career: <span className="text-primary-violet font-bold underline decoration-primary-violet/30 underline-offset-4">{data.role}</span>
            </p>
          </div>
        </div>
      </div>

      {/* AI Insight Box with Glow */}
      <div className="bg-slate-900/50 p-5 rounded-2xl border border-slate-800 shadow-[0_0_15px_rgba(108,63,200,0.05)] group-hover:shadow-[0_0_20px_rgba(108,63,200,0.1)] transition-all">
         <div className="flex items-start gap-4">
            <div className="bg-primary-violet/20 p-2 rounded-lg">
               <Sparkles className="w-4 h-4 text-primary-violet" />
            </div>
            <div>
               <p className="text-[11px] text-slate-400 leading-relaxed font-medium italic">
                  "{data.reason}"
               </p>
            </div>
         </div>
      </div>
    </div>
  )
}
