'use client'

import React, { useState, useEffect } from 'react'
import { Target, TrendingUp, AlertCircle, Loader2 } from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { Progress } from '@/components/ui/progress'

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
    <div className="bg-white rounded-xl p-8 border shadow-sm flex items-center justify-center min-h-[250px] animate-pulse">
       <Loader2 className="w-10 h-10 animate-spin text-primary" />
    </div>
  )

  if (!data || data.error) return null

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-success'
    if (score >= 75) return 'text-primary'
    if (score >= 50) return 'text-blue-500'
    return 'text-muted-foreground'
  }

  return (
    <div className="bg-card rounded-xl p-8 border shadow-sm flex flex-col justify-between h-full">
      <div className="mb-6">
        <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
               <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Target className="w-6 h-6 text-primary" />
               </div>
               <div>
                  <h3 className="text-lg font-semibold text-foreground">Match Fit Score</h3>
                  <p className="text-xs text-muted-foreground">Compatibility for current target role</p>
               </div>
            </div>
            {data.score > 0 && (
               <div className="flex items-center gap-2 px-3 py-1 bg-success/10 rounded-full border border-success/10">
                  <TrendingUp className="w-3 h-3 text-success" />
                  <span className="text-[10px] font-medium text-success uppercase tracking-wider">High Match</span>
               </div>
            )}
        </div>

        <div className="flex flex-col gap-4 mb-4">
            <div className="flex justify-between items-end mb-2">
               <div>
                 <span className={`text-4xl font-bold ${getScoreColor(data.score)}`}>{data.score}%</span>
                 <span className="text-xs text-muted-foreground ml-2">Match</span>
               </div>
               <span className={`text-xs font-semibold ${getScoreColor(data.score)} uppercase`}>{data.label}</span>
            </div>
            <Progress value={data.score} className="h-3" />
            <p className="text-sm text-foreground font-medium mt-2">
              Target: <span className="text-primary">{data.role}</span>
            </p>
        </div>
      </div>

      <div className="bg-muted p-4 rounded-xl border">
         <div className="flex items-start gap-4">
            <AlertCircle className="w-4 h-4 text-primary shrink-0 mt-0.5" />
            <p className="text-xs text-muted-foreground leading-relaxed italic">
               "{data.reason}"
            </p>
         </div>
      </div>
    </div>
  )
}
