'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { supabase } from '@/lib/supabase'
import Navbar from '@/components/Navbar'
import { Button } from '@/components/ui/button'
import { 
  Loader2, ArrowLeft, TrendingUp, Award, Flame, Target, 
  Mail, Calendar, Trophy, Zap, ChevronRight, Sparkles,
  BarChart3, LineChart as LineChartIcon, Activity
} from 'lucide-react'
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer, Area, AreaChart
} from 'recharts'

interface ProgressData {
  sessions: Array<{
    career_path: string
    total_score: number
    created_at: string
  }>
  rank: {
    xp: number
    level: number
    rank_title: string
  }
  streaks: {
    current_streak: number
    longest_streak: number
    total_sessions: number
  }
}

export default function ProgressPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [progressData, setProgressData] = useState<ProgressData | null>(null)
  const [userEmail, setUserEmail] = useState('')
  const [sendingReport, setSendingReport] = useState(false)
  const [reportSent, setReportSent] = useState(false)

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        router.push('/auth/login')
        return
      }
      if (user.email) {
        setUserEmail(user.email)
      }
      await fetchProgressData(user.id)
    }
    checkAuth()
  }, [router])

  const fetchProgressData = async (userId: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/interview/progress/${userId}`)
      if (response.ok) {
        const data = await response.json()
        setProgressData(data)
      }
    } catch (err) {
      console.error('Error fetching progress:', err)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const getChartData = () => {
    if (!progressData?.sessions) return []
    return progressData.sessions.map((session, index) => ({
      name: formatDate(session.created_at),
      score: session.total_score,
      career: session.career_path
    }))
  }

  const getCareerBreakdown = () => {
    if (!progressData?.sessions) return []
    
    const careerScores: Record<string, { total: number; count: number }> = {}
    progressData.sessions.forEach(session => {
      if (!careerScores[session.career_path]) {
        careerScores[session.career_path] = { total: 0, count: 0 }
      }
      careerScores[session.career_path].total += session.total_score
      careerScores[session.career_path].count += 1
    })
    
    return Object.entries(careerScores).map(([career, data]) => ({
      career,
      average: Math.round(data.total / data.count),
      count: data.count
    })).sort((a, b) => b.average - a.average)
  }

  const getNextLevelXP = (level: number) => {
    const levels = [0, 100, 250, 500, 900, 1400, 2000]
    return levels[level] || 2000
  }

  const sendWeeklyReport = async () => {
    if (!userEmail) return
    setSendingReport(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const { data: { user } } = await supabase.auth.getUser()
      
      const response = await fetch(`${apiUrl}/api/email/send-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          user_id: user?.id, 
          email: userEmail 
        })
      })
      
      if (response.ok) {
        setReportSent(true)
        setTimeout(() => setReportSent(false), 3000)
      }
    } catch (err) {
      console.error('Error sending report:', err)
    } finally {
      setSendingReport(false)
    }
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

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-[#6C3FC8] mx-auto mb-4" />
          <p className="text-slate-400 font-medium">Synthesizing progress metrics...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0F172A] text-white">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <motion.div 
          initial="hidden"
          animate="visible"
          variants={containerVariants}
          className="max-w-5xl mx-auto"
        >
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
            <div className="flex items-center gap-6">
              <Link href="/interview">
                <Button variant="ghost" className="bg-[#1E293B] border border-white/5 hover:bg-[#334155] rounded-xl p-3 h-auto group transition-all">
                  <ArrowLeft className="w-5 h-5 text-slate-400 group-hover:text-white group-hover:-translate-x-1 transition-transform" />
                </Button>
              </Link>
              <div>
                <motion.h1 
                  variants={itemVariants}
                  className="text-4xl font-black tracking-tight text-white flex items-center gap-3"
                >
                  My <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#6C3FC8] to-[#9333EA]">Performance</span>
                </motion.h1>
                <div className="flex items-center gap-2 text-slate-400 mt-1">
                  <Activity className="w-4 h-4 text-[#6C3FC8]" />
                  <span className="font-bold text-sm uppercase tracking-widest">Real-time career intelligence</span>
                </div>
              </div>
            </div>
            
            <motion.div variants={itemVariants} className="flex gap-2">
              <div className="bg-[#1E293B] px-4 py-2 rounded-full border border-white/10 flex items-center gap-2">
                <Calendar className="w-4 h-4 text-slate-500" />
                <span className="text-xs font-black uppercase tracking-widest text-slate-300">Updated Today</span>
              </div>
            </motion.div>
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
            {[
              { 
                label: 'Streak', 
                val: progressData?.streaks.current_streak || 0, 
                icon: Flame, 
                color: 'text-orange-400', 
                bg: 'bg-orange-500/10',
                glow: 'shadow-[0_0_15px_rgba(249,115,22,0.3)]',
                border: 'border-orange-500/20'
              },
              { 
                label: 'Rank', 
                val: progressData?.rank.rank_title || 'Fresher', 
                icon: Trophy, 
                color: 'text-purple-400', 
                bg: 'bg-purple-500/10',
                glow: 'shadow-[0_0_15px_rgba(108,63,200,0.3)]',
                border: 'border-purple-500/20'
              },
              { 
                label: 'Total XP', 
                val: progressData?.rank.xp || 0, 
                icon: Zap, 
                color: 'text-yellow-400', 
                bg: 'bg-yellow-500/10',
                glow: 'shadow-[0_0_15px_rgba(234,179,8,0.2)]',
                border: 'border-yellow-500/20'
              },
              { 
                label: 'Sessions', 
                val: progressData?.streaks.total_sessions || 0, 
                icon: Target, 
                color: 'text-blue-400', 
                bg: 'bg-blue-500/10',
                glow: 'shadow-[0_0_15px_rgba(59,130,246,0.2)]',
                border: 'border-blue-500/20'
              }
            ].map((stat, i) => (
              <motion.div 
                key={i}
                variants={itemVariants}
                whileHover={{ y: -5 }}
                className={`bg-[#1E293B] rounded-2xl border ${stat.border} p-6 relative overflow-hidden transition-all group`}
              >
                <div className={`absolute top-0 right-0 w-16 h-16 ${stat.bg} rounded-full blur-2xl -translate-y-1/2 translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity`} />
                <div className="relative z-10 flex flex-col items-center">
                  <div className={`p-3 rounded-xl ${stat.bg} ${stat.color} mb-4 ${stat.glow}`}>
                    <stat.icon className="w-6 h-6" />
                  </div>
                  <div className="text-2xl font-black text-white mb-1 group-hover:scale-110 transition-transform">
                    {typeof stat.val === 'number' ? stat.val.toLocaleString() : stat.val}
                  </div>
                  <div className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">{stat.label}</div>
                </div>
              </motion.div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Score Trend Chart */}
            <motion.div variants={itemVariants} className="lg:col-span-2 bg-[#1E293B] rounded-3xl border border-white/5 p-8 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-8 opacity-5">
                <LineChartIcon className="w-32 h-32" />
              </div>
              <div className="flex items-center justify-between mb-8 relative z-10">
                <div>
                  <h2 className="text-xl font-black uppercase tracking-widest text-white">Score Analytics</h2>
                  <p className="text-xs font-bold text-slate-500 mt-1">Growth trajectory across verified sessions</p>
                </div>
                <div className="flex gap-2">
                  <div className="flex items-center gap-2 bg-[#0F172A] px-3 py-1.5 rounded-lg border border-white/5">
                    <div className="w-2 h-2 rounded-full bg-[#6C3FC8] shadow-[0_0_8px_#6C3FC8]" />
                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Score Out of 50</span>
                  </div>
                </div>
              </div>
              
              {progressData?.sessions && progressData.sessions.length > 0 ? (
                <div className="h-[300px] w-full mt-4 relative z-10">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={getChartData()}>
                      <defs>
                        <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#6C3FC8" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#6C3FC8" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ffffff05" />
                      <XAxis 
                        dataKey="name" 
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: '#64748b', fontSize: 10, fontWeight: 700 }}
                        dy={10}
                      />
                      <YAxis 
                        domain={[0, 50]} 
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: '#64748b', fontSize: 10, fontWeight: 700 }}
                        dx={-10}
                      />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: '#0F172A', 
                          border: '1px solid rgba(255,255,255,0.1)',
                          borderRadius: '16px',
                          color: '#fff',
                          boxShadow: '0 10px 15px -3px rgba(0,0,0,0.5)'
                        }}
                        itemStyle={{ color: '#6C3FC8', fontWeight: 900 }}
                        labelStyle={{ color: '#94a3b8', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '4px' }}
                        cursor={{ stroke: '#6C3FC8', strokeWidth: 2, strokeDasharray: '5 5' }}
                        formatter={(value: number, name: string, props: any) => [
                          `${value}/50`,
                          props.payload.career
                        ]}
                      />
                      <Area
                        type="monotone"
                        dataKey="score"
                        stroke="#6C3FC8"
                        strokeWidth={4}
                        fillOpacity={1}
                        fill="url(#scoreGradient)"
                        dot={{ fill: '#FACC15', stroke: '#1E293B', strokeWidth: 2, r: 6 }}
                        activeDot={{ r: 8, fill: '#6C3FC8', stroke: '#fff' }}
                        animationDuration={1500}
                        animationBegin={300}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-[300px] flex items-center justify-center border-2 border-dashed border-white/5 rounded-2xl">
                  <div className="text-center">
                    <BarChart3 className="w-12 h-12 text-slate-800 mx-auto mb-4" />
                    <p className="text-slate-500 font-bold text-sm tracking-widest uppercase">Incubating Data Points...</p>
                  </div>
                </div>
              )}
            </motion.div>

            {/* Career Path Breakdown */}
            <motion.div variants={itemVariants} className="bg-[#1E293B] rounded-3xl border border-white/5 p-8">
              <h2 className="text-xl font-black uppercase tracking-widest text-white mb-6">Career Matrix</h2>
              {getCareerBreakdown().length > 0 ? (
                <div className="space-y-6">
                  {getCareerBreakdown().map((item, index) => (
                    <div key={index} className="group cursor-default">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-black text-slate-300 group-hover:text-white transition-colors">{item.career}</span>
                        <span className="text-sm font-bold text-yellow-400">{item.average}%</span>
                      </div>
                      <div className="h-3 bg-[#0F172A] rounded-full overflow-hidden border border-white/5">
                        <motion.div 
                          initial={{ width: 0 }}
                          animate={{ width: `${item.average}%` }}
                          transition={{ duration: 1, ease: "circOut", delay: index * 0.1 }}
                          className="h-full bg-gradient-to-r from-[#6C3FC8] to-purple-400 rounded-full shadow-[0_0_10px_rgba(108,63,200,0.3)]"
                        />
                      </div>
                      <div className="flex justify-between mt-1 text-[9px] font-black uppercase tracking-widest text-slate-500">
                        <span>Analysis: {item.count} sessions</span>
                        <span>Maturity Level</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-12 text-center text-slate-500 italic text-sm font-bold uppercase tracking-widest bg-[#0F172A] rounded-2xl border border-white/5 border-dashed">
                  No breakdown available
                </div>
              )}
            </motion.div>

            {/* XP Progress Section */}
            <motion.div variants={itemVariants} className="bg-[#1E293B] rounded-3xl border border-white/5 p-8 relative overflow-hidden group">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 via-yellow-400 to-purple-500 opacity-30" />
              <div className="flex items-center gap-4 mb-8">
                <div className="p-3 rounded-2xl bg-gradient-to-br from-purple-500/20 to-yellow-500/20 border border-white/10 group-hover:rotate-12 transition-transform shadow-xl">
                  <Sparkles className="w-6 h-6 text-yellow-400" />
                </div>
                <div>
                  <h2 className="text-xl font-black uppercase tracking-widest text-white">Maturity Arc</h2>
                  <p className="text-xs font-bold text-slate-500 mt-1">XP Progression to next Tier</p>
                </div>
              </div>
              
              <div className="relative text-center py-6">
                <div className="text-4xl font-black text-white tracking-tighter mb-1 relative z-10 drop-shadow-[0_0_15px_rgba(108,63,200,0.5)]">
                  {progressData?.rank.rank_title || '🌱 Fresher'}
                </div>
                <div className="inline-flex items-center gap-2 px-4 py-1 bg-slate-800 rounded-full border border-white/5 text-[10px] font-black uppercase tracking-widest text-[#6C3FC8] shadow-inner mb-6">
                   Tier Level {progressData?.rank.level || 1}
                </div>
                
                <div className="relative">
                  <div className="flex justify-between text-xs font-black uppercase tracking-widest text-slate-400 mb-2 px-1">
                    <span>{progressData?.rank.xp || 0} XP</span>
                    <span className="text-yellow-400">{getNextLevelXP(progressData?.rank.level || 1)} XP</span>
                  </div>
                  <div className="h-4 bg-[#0F172A] rounded-full overflow-hidden border border-white/5 p-0.5">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ 
                        width: `${Math.min(100, ((progressData?.rank.xp || 0) / getNextLevelXP(progressData?.rank.level || 1)) * 100)}%` 
                      }}
                      transition={{ duration: 1.5, ease: "circOut" }}
                      className="h-full bg-gradient-to-r from-[#6C3FC8] via-purple-400 to-[#FACC15] rounded-full relative"
                    >
                      <div className="absolute inset-0 bg-[linear-gradient(45deg,transparent_25%,rgba(255,255,255,0.1)_50%,transparent_75%)] bg-[length:20px_20px] animate-[slide_1s_linear_infinite]" />
                    </motion.div>
                  </div>
                  <div className="absolute top-1/2 left-0 w-full flex justify-center -translate-y-1/2 pointer-events-none opacity-20">
                     <div className="w-full h-6 bg-yellow-400 blur-2xl rounded-full" />
                  </div>
                </div>
              </div>

              <div className="mt-8 flex items-center justify-between p-4 bg-[#0F172A] rounded-2xl border border-white/5">
                 <div className="text-xs font-black uppercase tracking-widest text-slate-500">Next Tier</div>
                 <div className="flex items-center gap-2 text-slate-300">
                    <span className="text-xs font-black">Level {Math.min(7, (progressData?.rank.level || 1) + 1)}</span>
                    <ChevronRight className="w-4 h-4 text-slate-600" />
                 </div>
              </div>
            </motion.div>

            {/* Weekly Email Report Section */}
            <motion.div variants={itemVariants} className="lg:col-span-2 bg-[#1E293B] rounded-3xl border border-white/5 p-8 relative overflow-hidden group">
              <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-[#6C3FC8] opacity-5 rounded-full blur-[80px]" />
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
                <div className="max-w-md">
                  <h2 className="text-2xl font-black uppercase tracking-widest text-white flex items-center gap-3">
                    <Mail className="w-6 h-6 text-[#6C3FC8]" /> 
                    Intel <span className="text-slate-500">Broadcast</span>
                  </h2>
                  <p className="text-slate-400 font-medium text-sm mt-2">
                    Receive your comprehensive AI performance breakdown and skill-gap analysis via secure SMTP protocol every Monday.
                  </p>
                </div>
                
                <div className="flex-1 flex flex-col gap-4">
                  <div className="flex gap-2 p-1 bg-[#0F172A] rounded-2xl border border-white/5 shadow-inner">
                    <input
                      type="email"
                      value={userEmail}
                      onChange={(e) => setUserEmail(e.target.value)}
                      placeholder="Verified Terminal Address"
                      className="flex-1 bg-transparent px-4 py-3 text-white text-sm outline-none font-bold placeholder:text-slate-700"
                      aria-label="Email address for report"
                    />
                    <Button 
                      onClick={sendWeeklyReport}
                      disabled={sendingReport || !userEmail}
                      className="bg-[#6C3FC8] hover:bg-[#6C3FC8]/90 text-white font-black uppercase tracking-tighter text-xs px-6 rounded-xl shadow-[0_0_20px_rgba(108,63,200,0.3)] transition-all active:scale-95"
                    >
                      {sendingReport ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : 'Request Dispatch'}
                    </Button>
                  </div>
                  
                  <AnimatePresence>
                    {reportSent && (
                      <motion.div 
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className="bg-green-500/10 border border-green-500/20 p-2 rounded-xl text-center"
                      >
                        <span className="text-xs font-black uppercase tracking-widest text-green-400">✅ Intelligence Dispatched to {userEmail}</span>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
              
              <div className="flex items-center gap-3 mt-6 pt-6 border-t border-white/5 opacity-40">
                <Lightbulb className="w-4 h-4 text-yellow-400" />
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                  Encryption active: GMAIL_SERVICE_PROTOCOL_ENABLED
                </p>
              </div>
            </motion.div>
          </div>
        </motion.div>
      </main>
      
      {/* Background Orbs */}
      <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden">
        <div className="absolute top-[20%] left-[-10%] w-[500px] h-[500px] bg-purple-900/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-[#6C3FC8]/5 rounded-full blur-[100px]" />
      </div>
    </div>
  )
}

function Lightbulb(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .5 2.2 1.5 3.1.7.7 1.3 1.5 1.5 2.4" />
      <path d="M9 18h6" />
      <path d="M10 22h4" />
    </svg>
  )
}