'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { supabase } from '@/lib/supabase'
import Navbar from '@/components/Navbar'
import ProgressTracker from '@/components/ProgressTracker'
import MatchFitScore from '@/components/MatchFitScore'
import { Brain, LogOut, ChevronRight, Sparkles, Target, TrendingUp, ShieldCheck, Briefcase, Activity, Mail, Loader2, Clock, CheckCircle, XCircle, MessageSquare } from 'lucide-react'
import CareerCoach from '@/components/CareerCoach'

export default function DashboardPage() {
  const [user, setUser] = useState<{ email: string; id?: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const [emailStatus, setEmailStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [emailMessage, setEmailMessage] = useState('')
  const [appStats, setAppStats] = useState<any>({ applied: 0, interview: 0, rejected: 0, offer: 0 })

  const formatUsername = (email: string) => {
    // Extract first word before any dot or number and capitalize
    const prefix = email.split('@')[0]
    const match = prefix.match(/^[a-zA-Z]+/)
    if (match) {
      return match[0].charAt(0).toUpperCase() + match[0].slice(1).toLowerCase()
    }
    return prefix.charAt(0).toUpperCase() + prefix.slice(1)
  }

  useEffect(() => {
    const getUser = async () => {
      try {
        const { data: { user }, error } = await supabase.auth.getUser()
        if (error || !user || !user.email) {
          window.location.href = '/auth/login'
          return
        }
        setUser({ email: user.email, id: user.id })
        
        // Load application stats
        await loadAppStats()
      } catch (err) {
        window.location.href = '/auth/login'
      } finally {
        setLoading(false)
      }
    }
    getUser()
  }, [])

  const loadAppStats = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const headers: Record<string, string> = {}
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
      }
      
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/jobs/applications`, { headers })
      
      if (response.ok) {
        const data = await response.json()
        setAppStats(data.status_counts || { applied: 0, interview: 0, rejected: 0, offer: 0 })
      }
    } catch (err) {
      console.error('Failed to load app stats:', err)
    }
  }

  const sendProgressReport = async () => {
    if (!user?.id) return
    setEmailStatus('loading')
    setEmailMessage('')
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/email-report/send-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: user.id })
      })
      
      if (response.ok) {
        setEmailStatus('success')
        setEmailMessage('Progress report sent successfully!')
      } else {
        const data = await response.json().catch(() => ({}))
        setEmailStatus('error')
        setEmailMessage(data.detail || 'Failed to send progress report')
      }
    } catch (err) {
      setEmailStatus('error')
      setEmailMessage('Failed to send progress report')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-violet" />
      </div>
    )
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  }

  return (
    <div className="min-h-screen bg-[#0F172A] text-white selection:bg-primary-violet/30">
      <Navbar />
      <main className="container mx-auto px-4 py-12 flex flex-col gap-8 max-w-6xl">
        {/* Welcome */}
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="mb-8"
        >
           <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-3">
             Welcome, <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-violet to-purple-400">
               {user?.email ? formatUsername(user.email) : 'Explorer'}
             </span>!
           </h1>
           <p className="text-slate-400 mt-2 font-medium">
             Monitor your AI-powered career journey and role compatibility
           </p>
        </motion.div>

        {/* Analytics Grid */}
        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid lg:grid-cols-2 gap-8 items-start mb-8"
        >
          <motion.div variants={itemVariants}>
            <ProgressTracker />
          </motion.div>
          <motion.div variants={itemVariants}>
            <CareerCoach compact />
          </motion.div>
        </motion.div>

        {/* Application Stats */}
        <motion.div variants={itemVariants} className="mb-8">
          <div className="flex items-center gap-4 mb-6">
            <h2 className="text-xl font-bold text-white uppercase tracking-widest text-sm">Job Pipeline</h2>
            <div className="flex-1 border-t border-slate-800" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { status: 'applied', label: 'Applied', color: 'bg-yellow-500/20 border-yellow-500/40 text-yellow-400', icon: Clock },
              { status: 'interview', label: 'Interview', color: 'bg-blue-500/20 border-blue-500/40 text-blue-400', icon: MessageSquare },
              { status: 'rejected', label: 'Rejected', color: 'bg-red-500/20 border-red-500/40 text-red-400', icon: XCircle },
              { status: 'offer', label: 'Offer', color: 'bg-green-500/20 border-green-500/40 text-green-400', icon: CheckCircle }
            ].map((stat, i) => {
              const Icon = stat.icon
              const count = appStats[stat.status] || 0
              return (
                <Link key={i} href={`/applications${stat.status !== 'applied' ? '?status=' + stat.status : ''}`}>
                  <div className="bg-[#1E293B] rounded-2xl p-6 border border-white/5 hover:border-purple-500/30 transition-all group">
                    <div className={`w-12 h-12 rounded-xl ${stat.color} border flex items-center justify-center mb-4`}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <div className="text-3xl font-black text-white mb-1">{count}</div>
                    <div className="text-[10px] font-black uppercase text-slate-500 tracking-widest">{stat.label}</div>
                  </div>
                </Link>
              )
            })}
          </div>
        </motion.div>

        {/* Quick Actions */}
        <motion.div
           variants={containerVariants}
           initial="hidden"
           animate="visible"
        >
           <div className="flex items-center gap-4 mb-8">
              <h2 className="text-xl font-bold text-white uppercase tracking-widest text-sm">Quick Actions</h2>
              <div className="flex-1 border-t border-slate-800" />
           </div>
           
           <div className="grid md:grid-cols-4 gap-4">
             {[
               { href: '/onboarding', icon: Target, label: 'Connect Profiles', desc: 'Sync LinkedIn & GitHub' },
               { href: '/analysis', icon: Brain, label: 'View Analysis', desc: 'See AI insights' },
               { href: '/jobs', icon: Briefcase, label: 'Find Jobs', desc: 'Market recommendations' },
               { href: '/profile', icon: Activity, label: 'Profile Management', desc: 'Update your assets' }
             ].map((action, i) => (
               <motion.div key={i} variants={itemVariants}>
                 <Link href={action.href}>
                   <div className="bg-[#1E293B] group rounded-xl p-6 border border-slate-800 border-l-primary-violet border-l-4 hover:shadow-[0_0_20px_rgba(108,63,200,0.2)] hover:bg-[#243147] transition-all cursor-pointer h-full relative overflow-hidden">
                       <div className="absolute top-0 right-0 w-32 h-32 bg-primary-violet/5 rounded-full blur-3xl -mr-16 -mt-16 group-hover:bg-primary-violet/10 transition-colors" />
                       <div className="w-12 h-12 rounded-lg bg-primary-violet/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-all border border-primary-violet/20">
                         <action.icon className="w-6 h-6 text-primary-violet" />
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

        {/* Email Report Section */}
        <motion.div variants={itemVariants}>
          <div className="bg-[#1E293B] rounded-xl p-6 border border-slate-800">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center border border-green-500/20">
                <Mail className="w-5 h-5 text-green-400" />
              </div>
              <h3 className="font-bold text-white text-lg">Email Progress Report</h3>
            </div>
            <p className="text-sm text-slate-400 mb-4">Get your career progress sent to your inbox.</p>
            
            <button
              onClick={sendProgressReport}
              disabled={emailStatus === 'loading'}
              className="bg-green-600 hover:bg-green-700 disabled:bg-green-800 text-white font-bold px-6 py-3 rounded-lg transition-all flex items-center gap-2"
            >
              {emailStatus === 'loading' ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Mail className="w-5 h-5" />
                  Send Progress Report
                </>
              )}
            </button>
            
            {emailStatus === 'success' && (
              <div className="mt-4 p-3 bg-green-500/10 border border-green-500/30 rounded-lg text-green-400 text-sm font-medium">
                ✓ {emailMessage}
              </div>
            )}
            
            {emailStatus === 'error' && (
              <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm font-medium">
                ✗ {emailMessage}
              </div>
            )}
          </div>
        </motion.div>
      </main>
    </div>
  )
}
