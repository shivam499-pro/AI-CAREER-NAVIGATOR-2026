'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { supabase } from '@/lib/supabase'
import Navbar from '@/components/Navbar'
import ProgressTracker from '@/components/ProgressTracker'
import MatchFitScore from '@/components/MatchFitScore'
import { Brain, LogOut, ChevronRight, Sparkles, Target, TrendingUp, ShieldCheck, Briefcase, Activity } from 'lucide-react'

export default function DashboardPage() {
  const [user, setUser] = useState<{ email: string } | null>(null)
  const [loading, setLoading] = useState(true)

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
        setUser({ email: user.email })
      } catch (err) {
        window.location.href = '/auth/login'
      } finally {
        setLoading(false)
      }
    }
    getUser()
  }, [])

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
            <MatchFitScore />
          </motion.div>
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
      </main>
    </div>
  )
}
