'use client'

import Link from 'next/link'
import Navbar from '@/components/Navbar'
import { Button } from '@/components/ui/button'
import {
  Loader2, Trophy, Calendar, Clock,
  Target, Zap, Crown,
  ChevronRight, Sparkles, Medal,
  Brain, RefreshCw
} from 'lucide-react'
import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import { useChallenge } from './hooks/useChallenge'

// ─── Pure UI helpers (no business logic) ─────────────────────────────────────

const getTimeRemaining = (endsAt: string) => {
  try {
    const diff = new Date(endsAt).getTime() - Date.now()
    if (diff <= 0) return { days: 0, hours: 0, minutes: 0, seconds: 0 }
    return {
      days: Math.floor(diff / (1000 * 60 * 60 * 24)),
      hours: Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
      minutes: Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60)),
      seconds: Math.floor((diff % (1000 * 60)) / 1000),
    }
  } catch { return { days: 0, hours: 0, minutes: 0, seconds: 0 } }
}

const getNextSundayMidnight = () => {
  const now = new Date()
  const daysUntilSunday = (7 - now.getUTCDay()) % 7
  const next = new Date(now)
  next.setUTCDate(now.getUTCDate() + (daysUntilSunday === 0 ? 7 : daysUntilSunday))
  next.setUTCHours(0, 0, 0, 0)
  return next.toISOString()
}

const formatDate = (dateStr: string) => {
  try { return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }
  catch { return 'N/A' }
}

const formatDateTime = (dateStr: string) => {
  try { return new Date(dateStr).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }
  catch { return 'N/A' }
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

const getPerformanceInsight = (score: number) => {
  if (score >= 40) return 'Strong performance'
  if (score >= 25) return 'Good attempt, room to improve'
  return 'Needs improvement'
}

const getTimeRemainingInHours = () => {
  const diff = new Date(getNextSundayMidnight()).getTime() - Date.now()
  return Math.max(0, diff / (1000 * 60 * 60))
}

const getCountdownColor = () => {
  const hours = getTimeRemainingInHours()
  if (hours < 6) return 'text-red-400'
  if (hours < 24) return 'text-yellow-400'
  return 'text-purple-400'
}

const getDaysRemaining = (endsAt: string) => {
  try {
    const diff = Math.ceil((new Date(endsAt).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
    return diff > 0 ? diff : 0
  } catch { return 0 }
}

// ─── Component — logic-less, pure renderer ────────────────────────────────────

export default function ChallengesPage() {
  const {
    user, challenge, leaderboard, loading,
    error, isStarting, attemptStatus,
    refetch: retryFetch,
    handleAcceptChallenge,
  } = useChallenge()

  // Countdown timer — pure UI state, belongs in component
  const [countdown, setCountdown] = useState({ days: 0, hours: 0, minutes: 0, seconds: 0 })

  useEffect(() => {
    const update = () => setCountdown(getTimeRemaining(getNextSundayMidnight()))
    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [])

  const userRank = user ? leaderboard.find(e => e.user_email === user.email) : null
  const isCurrentUser = (email: string) => user?.email === email
  const getCountdownPulse = () => getTimeRemainingInHours() < 6

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.1, delayChildren: 0.2 } }
  }
  const itemVariants = { hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }

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

  return (
    <div className="min-h-screen bg-[#0F172A] text-white">
      <Navbar />
      <main className="max-w-5xl mx-auto p-6 md:p-12">
        <motion.div initial="hidden" animate="visible" variants={containerVariants}>

          {/* SECTION 1: Weekly Challenge Banner */}
          <motion.div
            variants={itemVariants}
            className="relative bg-gradient-to-br from-[#0F172A] to-[#1E293B] rounded-[2.5rem] p-10 mb-12 border border-white/10 overflow-hidden group shadow-[0_20px_50px_-20px_rgba(108,63,200,0.3)]"
          >
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
                      </div>
                      <div className="flex items-center gap-3 mt-2">
                        <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 rounded-xl border border-white/5">
                          <Clock className="w-4 h-4 text-slate-400" />
                          <span className="text-xs font-black uppercase tracking-widest text-slate-400">Time Remaining</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 mt-2">
                        {[
                          { value: countdown.days, label: 'Days' },
                          { value: countdown.hours, label: 'Hrs' },
                          { value: countdown.minutes, label: 'Min' },
                          { value: countdown.seconds, label: 'Sec' },
                        ].map((unit, i) => (
                          <div key={unit.label} className="flex items-center gap-2">
                            {i > 0 && <span className="text-sm font-black text-slate-500">:</span>}
                            <div className={`flex items-center justify-center w-14 h-12 bg-[#0F172A] rounded-xl border ${getCountdownColor()}/20 ${unit.label === 'Sec' && getCountdownPulse() ? 'animate-pulse' : ''}`}>
                              <span className={`text-lg font-black ${unit.label === 'Sec' && getCountdownPulse() ? 'text-red-400 animate-pulse' : getCountdownColor()}`}>
                                {String(unit.value).padStart(2, '0')}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="flex items-center gap-6 text-[10px] font-black uppercase tracking-widest text-slate-500 mt-1 ml-1">
                        <span>Days</span><span>Hrs</span><span>Min</span><span>Sec</span>
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex flex-col gap-4">
                  <Button
                    onClick={handleAcceptChallenge}
                    disabled={isStarting}
                    className={`bg-[#6C3FC8] hover:bg-[#6C3FC8]/90 text-white font-black uppercase tracking-tighter text-lg px-10 py-8 rounded-2xl shadow-[0_0_30px_rgba(108,63,200,0.4)] transition-all active:scale-95 group/btn ${isStarting ? 'opacity-70 cursor-wait' : ''}`}
                  >
                    {isStarting ? (
                      <><Loader2 className="w-5 h-5 mr-2 animate-spin" />Starting...</>
                    ) : (
                      <>🚀 {attemptStatus === 'completed' ? 'Retry Challenge' : attemptStatus === 'started' ? 'Continue Challenge' : 'Start Challenge'}<ChevronRight className="w-5 h-5 ml-2 group-hover/btn:translate-x-1 transition-transform" /></>
                    )}
                  </Button>
                  <div className="text-[10px] font-bold text-slate-500 text-center">
                    {attemptStatus === 'completed' ? 'Try again to improve your score' : attemptStatus === 'started' ? 'Continue your in-progress challenge' : "Start this week's challenge now"}
                  </div>
                  <div className="p-4 bg-[#0F172A]/50 rounded-2xl border border-white/5">
                    <div className="text-xs font-bold text-slate-400 text-center">Rewards will be revealed after completion</div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Microcopy */}
          {challenge && (
            <motion.div variants={itemVariants} className="mb-8 -mt-4">
              <p className="text-slate-400 text-sm text-center font-medium">Complete this challenge to test your real interview readiness.</p>
            </motion.div>
          )}

          {/* SECTION 2: Challenge Preview */}
          {challenge && challenge.questions && challenge.questions.length > 0 && (
            <motion.div variants={itemVariants} className="mb-12">
              <h2 className="text-sm font-black uppercase tracking-widest text-slate-500 mb-6 ml-2 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-400" />Challenge Preview
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
                <div className="bg-[#1E293B] rounded-2xl border border-white/5 p-5 hover:border-purple-500/30 transition-all group cursor-default">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 bg-blue-500/10 rounded-xl border border-blue-500/20 group-hover:scale-110 transition-transform">
                      <Brain className="w-5 h-5 text-blue-400" />
                    </div>
                  </div>
                  <div className="text-2xl font-black text-white">{challenge.questions.length}</div>
                  <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mt-1">Questions</div>
                </div>
              </div>
            </motion.div>
          )}

          {/* SECTION 3: Leaderboard */}
          <motion.div variants={itemVariants} className="grid lg:grid-cols-3 gap-8 mb-12">
            <div className="lg:col-span-2">
              <div className="bg-[#1E293B] rounded-[2rem] border border-white/5 p-8 relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-8 opacity-5"><Trophy className="w-32 h-32" /></div>
                <div className="flex items-center justify-between mb-8">
                  <h2 className="text-xl font-black uppercase tracking-widest text-white flex items-center gap-3">
                    <Crown className="w-6 h-6 text-yellow-400" /> High <span className="text-slate-500">Command</span>
                  </h2>
                  <div className="flex items-center gap-2 px-3 py-1 bg-slate-800 rounded-full border border-white/5">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Live Rankings</span>
                  </div>
                </div>
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }} className="space-y-3">
                  {error ? (
                    <div className="py-12 text-center bg-[#0F172A]/30 rounded-3xl border border-red-500/20 border-dashed">
                      <p className="text-red-400 font-bold uppercase tracking-widest text-xs mb-4">{error}</p>
                      <Button onClick={retryFetch} className="bg-red-500/20 hover:bg-red-500/30 text-red-400 font-black uppercase text-xs px-6 py-3 rounded-xl border border-red-500/30">
                        <RefreshCw className="w-4 h-4 mr-2" />Retry
                      </Button>
                    </div>
                  ) : leaderboard.length > 0 ? (
                    leaderboard.map((entry) => (
                      <motion.div key={entry.rank} whileHover={{ x: 4 }}
                        className={`flex items-center justify-between p-4 rounded-2xl border transition-all ${isCurrentUser(entry.user_email) ? 'bg-purple-500/10 border-purple-500/30' : 'bg-[#0F172A]/50 border-white/5'}`}>
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
                            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{formatDate(entry.completed_at)}</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-lg font-black text-white flex items-center justify-end gap-1">{entry.score} <span className="text-[10px] text-slate-600">/ 50</span></div>
                          <div className="text-[9px] font-black uppercase tracking-widest text-purple-400 opacity-60">Session Score</div>
                        </div>
                      </motion.div>
                    ))
                  ) : (
                    <div className="py-12 text-center bg-[#0F172A]/30 rounded-3xl border border-white/5 border-dashed">
                      <Trophy className="w-8 h-8 text-slate-600 mx-auto mb-4" />
                      <p className="text-slate-500 font-bold uppercase tracking-widest text-xs">No participants yet. Be the first to take the challenge!</p>
                    </div>
                  )}
                </motion.div>
              </div>

              {user && (
                <motion.div variants={itemVariants} className="mt-6">
                  {userRank ? (
                    <div className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-2xl border border-purple-500/30 p-6">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-4">
                          <div className="p-3 bg-purple-500/20 rounded-xl border border-purple-500/30"><Crown className="w-6 h-6 text-purple-400" /></div>
                          <div>
                            <div className="text-xs font-black uppercase tracking-widest text-purple-400 mb-1">Your Rank</div>
                            <div className="text-2xl font-black text-white">#{userRank.rank} <span className="text-slate-500 text-base font-normal">of {leaderboard.length}</span></div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-xl font-black text-white">{userRank.score} <span className="text-sm text-slate-500">/ 50</span></div>
                          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Your Score</div>
                        </div>
                      </div>
                      <div className="flex items-center justify-between pt-4 border-t border-purple-500/20">
                        <div className="text-xs text-slate-400">Completed {formatDateTime(userRank.completed_at)}</div>
                        <div className="text-sm font-bold text-purple-400">{getPerformanceInsight(userRank.score)}</div>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-[#1E293B] rounded-2xl border border-white/5 p-6 text-center">
                      <div className="p-3 bg-slate-800/50 rounded-xl border border-white/5 w-fit mx-auto mb-4"><Trophy className="w-6 h-6 text-slate-500" /></div>
                      <p className="text-slate-500 font-bold text-sm text-center">You are not in the top rankings yet.</p>
                      <p className="text-slate-600 text-xs text-center mt-2">Complete the challenge to appear here.</p>
                    </div>
                  )}
                </motion.div>
              )}
            </div>

            {/* SECTION 4: How It Works */}
            <div className="space-y-4">
              <h2 className="text-xs font-black uppercase tracking-widest text-slate-500 mb-4 ml-2">Operation Protocol</h2>
              {[
                { icon: Calendar, color: 'purple', title: 'Weekly Reset', desc: 'A fresh set of intelligence objectives awaits every Monday at 00:00 UTC.' },
                { icon: Clock, color: 'yellow', title: 'Engagement Window', desc: 'Analyze and execute your best performance within the 168-hour tactical window.' },
                { icon: Medal, color: 'green', title: 'Elite Validation', desc: 'Top tier performers earn specialized matrix experience and global visibility.' },
              ].map(({ icon: Icon, color, title, desc }) => (
                <div key={title} className={`bg-[#1E293B] rounded-3xl border border-white/5 p-6 hover:border-${color}-500/30 transition-all group`}>
                  <div className={`p-3 bg-${color}-500/10 rounded-2xl border border-${color}-500/20 w-fit mb-4 group-hover:scale-110 transition-transform`}>
                    <Icon className={`w-6 h-6 text-${color}-400`} />
                  </div>
                  <h3 className="font-black text-white text-sm uppercase tracking-tighter mb-2">{title}</h3>
                  <p className="text-xs text-slate-500 font-bold leading-relaxed">{desc}</p>
                </div>
              ))}
            </div>
          </motion.div>

        </motion.div>
        <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden opacity-50">
          <div className="absolute top-[20%] right-[-10%] w-[500px] h-[500px] bg-purple-900/10 rounded-full blur-[120px]" />
          <div className="absolute bottom-[-10%] left-[-10%] w-[500px] h-[500px] bg-blue-900/10 rounded-full blur-[100px]" />
        </div>
      </main>
    </div>
  )
}