'use client'

import React, { useState, useEffect } from 'react'
import { CheckCircle2, Circle, Shield, TrendingUp } from 'lucide-react'
import { supabase } from '@/lib/supabase'

interface ProgressStep {
  id: string
  label: string
  desc: string
  status: 'complete' | 'pending'
  value: number
}

interface ProgressData {
  total: number
  steps: ProgressStep[]
  status: string
}

export default function ProgressTracker() {
  const [data, setData] = useState<ProgressData | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchProgress = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/profile/progress`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })
      const result = await response.json()
      setData(result)
    } catch (err) {
      console.error("Progress fetch error:", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProgress()
    const interval = setInterval(fetchProgress, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return (
    <div className="bg-[#1E293B] rounded-2xl p-8 border border-slate-800 shadow-2xl animate-pulse h-[350px]">
       <div className="h-6 w-32 bg-slate-800 rounded mb-6" />
       <div className="h-4 w-full bg-slate-800 rounded mb-8" />
       <div className="grid grid-cols-2 gap-4">
         <div className="h-20 bg-slate-800 rounded-xl" />
         <div className="h-20 bg-slate-800 rounded-xl" />
       </div>
    </div>
  )

  if (!data) return null

  return (
    <div className="bg-[#1E293B] rounded-2xl p-8 border border-slate-800 shadow-[0_0_50px_rgba(108,63,200,0.1)] relative overflow-hidden group">
      <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-primary-violet to-transparent opacity-50" />
      
      <div className="flex items-center justify-between mb-8">
        <div>
          <h3 className="text-xl font-bold text-white tracking-tight">Your Progress</h3>
          <p className="text-sm text-slate-400 font-medium">Overall completion of your career journey</p>
        </div>
        <div className="bg-primary-violet/20 text-primary-violet px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border border-primary-violet/30">
          {data.status}
        </div>
      </div>

      <div className="mb-8">
        <div className="flex justify-between items-end mb-3">
           <div className="flex items-baseline gap-1">
             <span className="text-4xl font-black text-white">{data.total}%</span>
             <span className="text-slate-500 font-bold text-sm uppercase">Complete</span>
           </div>
           {data.total > 0 && (
             <div className="flex items-center gap-1 text-primary-violet text-xs font-bold">
               <TrendingUp className="w-3 h-3" />
               <span>TRACKING LIVE</span>
             </div>
           )}
        </div>
        {/* Gradient Progress Bar */}
        <div className="h-3 w-full bg-slate-800 rounded-full overflow-hidden border border-slate-700/50">
          <div 
            className="h-full bg-gradient-to-r from-[#1E3A5F] via-[#6C3FC8] to-[#9F7AEA] transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(108,63,200,0.5)]"
            style={{ width: `${data.total}%` }}
          />
        </div>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        {data.steps.map((step, i) => (
          <div 
            key={i} 
            className={`flex items-start gap-3 p-4 rounded-xl border transition-all duration-300 ${
              step.status === 'complete' 
              ? 'bg-primary-violet/5 border-primary-violet/20 hover:bg-primary-violet/10' 
              : 'bg-slate-800/40 border-slate-800/50 opacity-50 grayscale hover:grayscale-0 hover:opacity-100'
            }`}
          >
            <div className={`mt-0.5 ${step.status === 'complete' ? 'text-primary-violet' : 'text-slate-600'}`}>
              {step.status === 'complete' ? (
                <CheckCircle2 className="w-5 h-5 drop-shadow-[0_0_5px_rgba(108,63,200,0.5)]" />
              ) : (
                <Circle className="w-5 h-5" />
              )}
            </div>
            <div>
              <p className={`text-sm font-bold ${step.status === 'complete' ? 'text-white' : 'text-slate-400'}`}>
                {step.label}
              </p>
              <p className="text-[11px] text-slate-500 font-medium mt-0.5 leading-tight">{step.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
