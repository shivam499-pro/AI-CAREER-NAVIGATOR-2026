'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Navbar from '@/components/Navbar'
import { Button } from '@/components/ui/button'
import { 
  Loader2, Trophy, Calendar, Clock, 
  Target, Zap, Flame, Crown, Star, 
  ChevronRight, Sparkles, Medal, Award
} from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { motion, AnimatePresence } from 'framer-motion'

interface WeeklyChallenge {
  week_number: number
  year: number
  theme: string
  career_path: string
  questions: string[]
  starts_at: string
  ends_at: string
}

interface LeaderboardEntry {
  rank: number
  user_email: string
  score: number
  completed_at: string
}

export default function ChallengesPage() {
  const router = useRouter()
  
  const [challenge, setChallenge] = useState<WeeklyChallenge | null>(null)
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState<any>(null)
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        const { data: { user } } = await supabase.auth.getUser()
        setUser(user)
        
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        
        const [challengeRes, leaderboardRes] = await Promise.all([
          fetch(`${apiUrl}/api/weekly/current`),
          fetch(`${apiUrl}/api/weekly/leaderboard`)
        ])
        
        if (challengeRes.ok) {
          const data = await challengeRes.json()
          setChallenge(data)
        }
        
        if (leaderboardRes.ok) {
          const data = await leaderboardRes.json()
          setLeaderboard(data)
        }
      } catch (err) {
        console.error('Error fetching data:', err)
      } finally {
        setLoading(false)
      }
    }
    
    fetchData()
  }, [])
  
  const handleAcceptChallenge = () => {
    if (challenge) {
      router.push(`/interview?mode=weekly&career_path=${encodeURIComponent(challenge.career_path)}`)
    }
  }
  
  const getDaysRemaining = (endsAt: string) => {
    try {
      const endDate = new Date(endsAt)
      const now = new Date()
      const diff = Math.ceil((endDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
      return diff > 0 ? diff : 0
    } catch {
      return 0
    }
  }
  
  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    } catch {
      return 'N/A'
    }
  }
  
  const getMedalEmoji = (rank: number) => {
    if (rank === 1) return '🥇'
    if (rank === 2) return '🥈'
    if (rank === 3) return '🥉'
    return null
  }

  const getRankColor = (rank: number) => {
    if (rank === 1) return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
    if (rank === 2) return 'bg-slate-300/20 text-slate-300 border-slate-300/30'
    if (rank === 3) return 'bg-orange-600/20 text-orange-400 border-orange-600/30'
    return 'bg-slate-800/40 text-slate-500 border-white/5'
  }
  
  const isCurrentUser = (email: string) => {
    return user?.email === email
  }
  
  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-purple-500 mx-auto mb-4" />
          <p className="text-slate-400 font-bold tracking-widest uppercase text-xs">Syncing Global Intelligence...</p>
        </div>
      </div>
    )
  }
  
  const daysRemaining = challenge ? getDaysRemaining(challenge.ends_at) : 0

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { 
        staggerChildren: 0.1,
        delayChildren: 0.2
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  }
  
  return (
    <div className="min-h-screen bg-[#0F172A] text-white">
      <Navbar />
      
      <main className="max-w-5xl mx-auto p-6 md:p-12">
        <motion.div
           initial="hidden"
           animate="visible"
           variants={containerVariants}
        >
          {/* SECTION 1: Weekly Challenge Banner */}
          <motion.div 
            variants={itemVariants}
            className="relative bg-gradient-to-br from-[#0F172A] to-[#1E293B] rounded-[2.5rem] p-10 mb-12 border border-white/10 overflow-hidden group shadow-[0_20px_50px_-20px_rgba(108,63,200,0.3)]"
          >
            {/* Background Polish */}
            <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-purple-500/10 to-transparent pointer-events-none" />
            <div className="absolute -top-24 -right-24 w-64 h-64 bg-purple-500/20 rounded-full blur-[100px] pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-purple-500 to-transparent opacity-50" />

            <div className="relative z-10">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-8">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-3 bg-purple-500/20 rounded-2xl border border-purple-500/30 group-hover:rotate-12 transition-transform">
                      <Zap className="w-8 h-8 text-[#6C3FC8]" />
                    </div>
                    <div>
                      <h1 className="text-4xl font-black text-white tracking-tighter uppercase italic">Weekly <span className="text-purple-400">Phase</span></h1>
                      <div className="flex items-center gap-2 mt-1">
                        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Live Operation Active</span>
                      </div>
                    </div>
                  </div>
                  
                  {challenge && (
                    <div className="space-y-6">
                      <div>
                        <div className="inline-flex items-center gap-2 px-3 py-1 bg-purple-500/10 rounded-full border border-purple-500/20 text-[#6C3FC8] font-black uppercase tracking-widest text-[10px] mb-3">
                           Active Objective
                        </div>
                        <h2 className="text-2xl font-black text-white tracking-tight leading-none group-hover:text-purple-300 transition-colors">
                          {challenge.theme}
                        </h2>
                      </div>
                      
                      <div className="flex flex-wrap gap-4 items-center">
                        <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 rounded-xl border border-white/5">
                           <Target className="w-4 h-4 text-blue-400" />
                           <span className="text-xs font-black uppercase tracking-widest text-slate-300">{challenge.career_path}</span>
                        </div>
                        <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 rounded-xl border border-white/5">
                           <Clock className="w-4 h-4 text-yellow-400" />
                           <span className="text-xs font-black uppercase tracking-widest text-yellow-400">
                             {daysRemaining} Days <span className="text-slate-500">Left</span>
                           </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex flex-col gap-4">
                  <Button 
                    onClick={handleAcceptChallenge}
                    className="bg-[#6C3FC8] hover:bg-[#6C3FC8]/90 text-white font-black uppercase tracking-tighter text-lg px-10 py-8 rounded-2xl shadow-[0_0_30px_rgba(108,63,200,0.4)] transition-all active:scale-95 group/btn"
                  >
                    🚀 Accept Protocol 
                    <ChevronRight className="w-5 h-5 ml-2 group-hover/btn:translate-x-1 transition-transform" />
                  </Button>
                  <p className="text-[9px] font-black uppercase tracking-[0.2em] text-center text-slate-500 opacity-60">Rewards: 50 XP | Rare Badge</p>
                </div>
              </div>
            </div>
          </motion.div>
          
          {/* SECTION 2: Leaderboard */}
          <motion.div variants={itemVariants} className="grid lg:grid-cols-3 gap-8 mb-12">
            <div className="lg:col-span-2">
              <div className="bg-[#1E293B] rounded-[2rem] border border-white/5 p-8 relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-8 opacity-5">
                   <Trophy className="w-32 h-32" />
                </div>
                
                <div className="flex items-center justify-between mb-8">
                  <h2 className="text-xl font-black uppercase tracking-widest text-white flex items-center gap-3">
                    <Crown className="w-6 h-6 text-yellow-400" /> High <span className="text-slate-500">Command</span>
                  </h2>
                  <div className="px-3 py-1 bg-slate-800 rounded-full border border-white/5 text-[10px] font-black uppercase tracking-widest text-slate-500">
                     Phase {challenge?.week_number || 1} Global
                  </div>
                </div>
                
                <div className="space-y-3">
                  {leaderboard.length > 0 ? (
                    leaderboard.map((entry) => (
                      <motion.div 
                        key={entry.rank}
                        whileHover={{ x: 4 }}
                        className={`flex items-center justify-between p-4 rounded-2xl border transition-all ${
                          isCurrentUser(entry.user_email) 
                            ? 'bg-purple-500/10 border-purple-500/30' 
                            : 'bg-[#0F172A]/50 border-white/5'
                        }`}
                      >
                        <div className="flex items-center gap-4">
                          <div className={`w-10 h-10 rounded-xl border flex items-center justify-center font-black text-sm p-0 ${getRankColor(entry.rank)}`}>
                             {getMedalEmoji(entry.rank) || entry.rank}
                          </div>
                          <div>
                            <div className="text-sm font-black text-white flex items-center gap-2">
                               {entry.user_email.split('@')[0]}
                               {isCurrentUser(entry.user_email) && (
                                 <span className="px-1.5 py-0.5 bg-purple-500 rounded-md text-[8px] text-white">YOU</span>
                               )}
                            </div>
                            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                               {formatDate(entry.completed_at)}
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                           <div className="text-lg font-black text-white flex items-center justify-end gap-1">
                              {entry.score} <span className="text-[10px] text-slate-600">/ 50</span>
                           </div>
                           <div className="text-[9px] font-black uppercase tracking-widest text-purple-400 opacity-60">Session Score</div>
                        </div>
                      </motion.div>
                    ))
                  ) : (
                    <div className="py-20 text-center bg-[#0F172A]/30 rounded-3xl border border-white/5 border-dashed">
                       <Loader2 className="w-8 h-8 animate-spin text-slate-700 mx-auto mb-4" />
                       <p className="text-slate-600 font-bold uppercase tracking-widest text-xs">Awaiting First Insertion...</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* SECTION 3: How It Works */}
            <div className="space-y-4">
              <h2 className="text-xs font-black uppercase tracking-widest text-slate-500 mb-4 ml-2">Operation Protocol</h2>
              
              <div className="bg-[#1E293B] rounded-3xl border border-white/5 p-6 hover:border-purple-500/30 transition-all group">
                <div className="p-3 bg-purple-500/10 rounded-2xl border border-purple-500/20 w-fit mb-4 group-hover:scale-110 transition-transform">
                   <Calendar className="w-6 h-6 text-[#6C3FC8]" />
                </div>
                <h3 className="font-black text-white text-sm uppercase tracking-tighter mb-2">Weekly Reset</h3>
                <p className="text-xs text-slate-500 font-bold leading-relaxed">
                  A fresh set of intelligence objectives awaits every Monday at 00:00 UTC.
                </p>
              </div>

              <div className="bg-[#1E293B] rounded-3xl border border-white/5 p-6 hover:border-yellow-500/30 transition-all group">
                <div className="p-3 bg-yellow-500/10 rounded-2xl border border-yellow-500/20 w-fit mb-4 group-hover:scale-110 transition-transform">
                   <Clock className="w-6 h-6 text-yellow-400" />
                </div>
                <h3 className="font-black text-white text-sm uppercase tracking-tighter mb-2">Engagement Window</h3>
                <p className="text-xs text-slate-500 font-bold leading-relaxed">
                  Analyze and execute your best performance within the 168-hour tactical window.
                </p>
              </div>

              <div className="bg-[#1E293B] rounded-3xl border border-white/5 p-6 hover:border-green-500/30 transition-all group">
                <div className="p-3 bg-green-500/10 rounded-2xl border border-green-500/20 w-fit mb-4 group-hover:scale-110 transition-transform">
                   <Medal className="w-6 h-6 text-green-400" />
                </div>
                <h3 className="font-black text-white text-sm uppercase tracking-tighter mb-2">Elite Validation</h3>
                <p className="text-xs text-slate-500 font-bold leading-relaxed">
                  Top tier performers earn specialized matrix experience and global visibility.
                </p>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </main>

      {/* Decorative Orbs */}
      <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden opacity-50">
        <div className="absolute top-[20%] right-[-10%] w-[500px] h-[500px] bg-purple-900/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[500px] h-[500px] bg-blue-900/10 rounded-full blur-[100px]" />
      </div>
    </div>
  )
}