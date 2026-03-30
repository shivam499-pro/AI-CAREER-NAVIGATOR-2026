'use client'

import React, { useState, useEffect } from 'react'
import { CheckCircle2, Circle, Shield } from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { Progress } from '@/components/ui/progress'

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
    <div className="bg-card rounded-xl p-6 border shadow-sm animate-pulse">
       <div className="h-6 w-32 bg-muted rounded mb-4" />
       <div className="h-2 w-full bg-muted rounded" />
    </div>
  )

  if (!data) return null

  return (
    <div className="bg-card rounded-xl p-8 border shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Your Progress</h3>
          <p className="text-sm text-muted-foreground">Overall completion of your career journey</p>
        </div>
        <div className="bg-primary/10 text-primary px-3 py-1 rounded-full text-xs font-medium">
          {data.status}
        </div>
      </div>

      <div className="mb-8">
        <div className="flex justify-between items-end mb-2">
           <span className="text-2xl font-bold text-foreground">{data.total}%</span>
           <span className="text-xs text-muted-foreground">Complete</span>
        </div>
        <Progress value={data.total} className="h-2" />
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        {data.steps.map((step, i) => (
          <div 
            key={i} 
            className={`flex items-start gap-3 p-4 rounded-lg border transition-colors ${
              step.status === 'complete' 
              ? 'bg-primary/5 border-primary/10' 
              : 'bg-muted/30 border-transparent opacity-60'
            }`}
          >
            {step.status === 'complete' ? (
              <CheckCircle2 className="w-5 h-5 text-primary shrink-0" />
            ) : (
              <Circle className="w-5 h-5 text-muted-foreground shrink-0" />
            )}
            <div>
              <p className="text-sm font-medium text-foreground">{step.label}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{step.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
