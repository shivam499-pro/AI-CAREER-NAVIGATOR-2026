'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { supabase } from '@/lib/supabase'
import Navbar from '@/components/Navbar'
import { 
  Trophy, Lock, Sparkles, Star, Target, 
  ChevronRight, ArrowLeft, Loader2, Award, Zap
} from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

interface Badge {
  id?: string
  badge_id: string
  name: string
  emoji: string
  description: string
  earned_at?: string
}

interface BadgeResponse {
  earned: Badge[]
  all_badges: Badge[]
}

export default function BadgesPage() {
  const [badges, setBadges] = useState<BadgeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [userId, setUserId] = useState<string | null>(null)

  useEffect(() => {
    async function fetchBadges() {
      const { data: { user } } = await supabase.auth.getUser()
      
      if (!user) {
        setLoading(false)
        return
      }

      setUserId(user.id)

      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/badges/${user.id}`
        )
        const data = await response.json()
        setBadges(data)
      } catch (error) {
        console.error('Error fetching badges:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchBadges()
  }, [])

  const earnedIds = new Set(badges?.earned.map(b => b.badge_id) || [])
  const earnedBadges = badges?.earned || []
  const lockedBadges = (badges?.all_badges || []).filter(b => !earnedIds.has(b.badge_id))
  
  const totalBadges = badges?.all_badges.length || 12
  const progressPercent = (earnedBadges.length / totalBadges) * 100

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
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
          <Loader2 className="w-12 h-12 animate-spin text-purple-500 mx-auto mb-4" />
          <p className="text-slate-400 font-medium">Loading achievements...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0F172A] text-white">
      <Navbar />
      
      <main className="max-w-6xl mx-auto px-4 py-12">
        <motion.div
           initial="hidden"
           animate="visible"
           variants={containerVariants}
        >
          {/* Header Section */}
          <div className="text-center mb-16 relative">
            <motion.div variants={itemVariants} className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/10 rounded-full border border-purple-500/20 text-[#6C3FC8] font-black uppercase tracking-widest text-[10px] mb-4">
               <Award className="w-4 h-4" /> Mastery Profile
            </motion.div>
            
            <motion.h1 variants={itemVariants} className="text-6xl font-black mb-6 tracking-tighter leading-tight">
               <span className="text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 via-orange-400 to-yellow-500">Achievement</span> Gallery
            </motion.h1>

            <motion.div variants={itemVariants} className="max-w-2xl mx-auto">
              <div className="flex justify-between items-end mb-4 px-2">
                 <span className="text-xs font-black uppercase tracking-widest text-[#6C3FC8]">Completion Status</span>
                 <span className="text-2xl font-black text-white">{earnedBadges.length}<span className="text-slate-600 text-lg mx-1">/</span>{totalBadges}</span>
              </div>
              <div className="h-4 bg-[#1E293B] rounded-full overflow-hidden border border-white/5 p-0.5 shadow-inner">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${progressPercent}%` }}
                  transition={{ duration: 1.5, ease: "circOut" }}
                  className="h-full bg-gradient-to-r from-[#6C3FC8] via-purple-500 to-yellow-400 rounded-full relative"
                >
                   <div className="absolute inset-0 bg-[linear-gradient(45deg,transparent_25%,rgba(255,255,255,0.1)_50%,transparent_75%)] bg-[length:20px_20px] animate-[slide_1s_linear_infinite]" />
                </motion.div>
              </div>
              <p className="text-slate-400 mt-4 font-bold text-sm">Targeting {totalBadges} verified milestones across career intelligence.</p>
            </motion.div>
          </div>

          {/* Earned Badges Section */}
          {earnedBadges.length > 0 && (
            <div className="mb-16">
              <div className="flex items-center gap-3 mb-8 px-2">
                 <div className="h-px bg-yellow-400/20 flex-1" />
                 <h2 className="text-sm font-black uppercase tracking-[0.3em] text-yellow-400">Earned Milestones</h2>
                 <div className="h-px bg-yellow-400/20 flex-1" />
              </div>
              <motion.div 
                variants={containerVariants}
                className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
              >
                {earnedBadges.map((badge) => (
                  <motion.div
                    key={badge.badge_id}
                    variants={itemVariants}
                    whileHover={{ y: -8, scale: 1.02 }}
                    className="bg-[#1E293B] rounded-3xl p-8 text-center relative overflow-hidden border-2 border-yellow-400/20 group transition-all"
                  >
                    {/* Shimmer Effect */}
                    <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-yellow-400/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-30 transition-opacity">
                       <Sparkles className="w-12 h-12 text-yellow-500" />
                    </div>

                    <div className="relative z-10 flex flex-col items-center">
                      <div className="text-7xl mb-6 transform group-hover:rotate-12 transition-transform drop-shadow-[0_0_20px_rgba(250,204,21,0.3)]">
                        {badge.emoji}
                      </div>
                      <h3 className="text-xl font-black text-yellow-400 mb-2">{badge.name}</h3>
                      <p className="text-sm text-slate-400 font-medium mb-6 line-clamp-2">{badge.description}</p>
                      
                      <div className="w-full pt-6 border-t border-white/5 flex flex-col items-center gap-2">
                        <div className="flex items-center gap-1.5 text-green-400">
                          <Zap className="w-3 h-3 fill-current" />
                          <span className="text-[10px] font-black uppercase tracking-widest">Authenticated</span>
                        </div>
                        <p className="text-[9px] font-black text-slate-500 uppercase tracking-widest">
                          {formatDate(badge.earned_at)}
                        </p>
                      </div>
                    </div>
                    
                    {/* Card Glow */}
                    <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none shadow-[inset_0_0_40px_rgba(250,204,21,0.05),0_0_20px_rgba(250,204,21,0.1)] rounded-3xl" />
                  </motion.div>
                ))}
              </motion.div>
            </div>
          )}

          {/* Locked Badges Section */}
          {lockedBadges.length > 0 && (
            <div>
              <div className="flex items-center gap-3 mb-8 px-2">
                 <div className="h-px bg-white/5 flex-1" />
                 <h2 className="text-sm font-black uppercase tracking-[0.3em] text-slate-500">Locked Intel</h2>
                 <div className="h-px bg-white/5 flex-1" />
              </div>
              <motion.div 
                variants={containerVariants}
                className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
              >
                {lockedBadges.map((badge) => (
                  <motion.div
                    key={badge.badge_id}
                    variants={itemVariants}
                    whileHover={{ opacity: 1, scale: 0.98 }}
                    className="bg-[#1E293B] rounded-3xl p-8 text-center border border-white/5 opacity-60 grayscale hover:grayscale-0 hover:opacity-100 transition-all cursor-not-allowed group relative overflow-hidden"
                  >
                    <div className="absolute top-4 right-4">
                       <Lock className="w-4 h-4 text-slate-600 group-hover:text-red-500 transition-colors" />
                    </div>
                    <div className="text-7xl mb-6 opacity-30 group-hover:opacity-60 transition-opacity">
                      {badge.emoji}
                    </div>
                    <h3 className="text-xl font-black text-slate-500 group-hover:text-slate-300 mb-2">{badge.name}</h3>
                    <p className="text-[10px] font-black uppercase tracking-widest text-[#EF4444] mt-2 opacity-0 group-hover:opacity-100 transition-opacity">Locked Achievements</p>
                  </motion.div>
                ))}
              </motion.div>
            </div>
          )}

          {/* No badges initial state */}
          {earnedBadges.length === 0 && (
            <motion.div 
              variants={itemVariants}
              className="text-center py-24 bg-[#1E293B] rounded-[3rem] border border-white/5"
            >
              <div className="text-8xl mb-8 opacity-20">🎖️</div>
              <h3 className="text-3xl font-black text-white mb-4">Initial Achievement Sync</h3>
              <p className="text-slate-500 font-bold max-w-sm mx-auto mb-10">Complete your first specialized interview session to authenticate your first milestone.</p>
              <Link href="/interview">
                 <Button className="bg-[#6C3FC8] hover:bg-purple-600 px-10 py-7 rounded-2xl text-lg font-black uppercase tracking-tighter">
                    Launch Performance Phase
                 </Button>
              </Link>
            </motion.div>
          )}

          {/* Global CTA */}
          <motion.div 
            variants={itemVariants}
            className="mt-24 text-center pb-20 border-t border-white/5 pt-12"
          >
             <p className="text-slate-500 text-xs font-black uppercase tracking-widest mb-6">Want to unlock higher tiers?</p>
             <div className="flex justify-center gap-4">
                <Link href="/dashboard">
                  <Button variant="outline" className="border-white/10 text-slate-400 hover:text-white font-black uppercase tracking-widest px-8 rounded-xl">
                     Return Terminal
                  </Button>
                </Link>
                <Link href="/analysis">
                  <Button variant="outline" className="border-white/10 text-slate-400 hover:text-white font-black uppercase tracking-widest px-8 rounded-xl">
                     View Skill Intel
                  </Button>
                </Link>
             </div>
          </motion.div>
        </motion.div>
      </main>

      {/* Decorative Orbs */}
      <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden opacity-30">
        <div className="absolute top-[10%] right-[-5%] w-[600px] h-[600px] bg-yellow-500/5 rounded-full blur-[150px]" />
        <div className="absolute bottom-[0%] left-[-5%] w-[600px] h-[600px] bg-[#6C3FC8]/10 rounded-full blur-[150px]" />
      </div>
    </div>
  )
}