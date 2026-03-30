'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import Navbar from '@/components/Navbar'
import ProgressTracker from '@/components/ProgressTracker'
import MatchFitScore from '@/components/MatchFitScore'
import { Brain, LogOut, ChevronRight, Sparkles, Target, TrendingUp, ShieldCheck, Briefcase, Activity } from 'lucide-react'

export default function DashboardPage() {
  const [user, setUser] = useState<{ email: string } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const getUser = async () => {
      try {
        console.log('Getting user session...')
        
        // First check if there's a session in storage
        const { data: sessionData } = await supabase.auth.getSession()
        console.log('Session data:', sessionData)
        
        const { data: { user }, error } = await supabase.auth.getUser()
        
        console.log('User from getUser:', user)
        console.log('Error:', error)
        
        if (error || !user || !user.email) {
          // Not logged in - redirect to login
          console.log('Not logged in, redirecting to login')
          window.location.href = '/auth/login'
          return
        }
        
        setUser({ email: user.email })
      } catch (err) {
        console.log('Error getting user:', err)
        // Error - redirect to login
        window.location.href = '/auth/login'
        return
      } finally {
        setLoading(false)
      }
    }
    
    getUser()
  }, [])

  const handleLogout = async () => {
    await supabase.auth.signOut()
    window.location.href = '/auth/login'
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container mx-auto px-4 py-12 flex flex-col gap-8 max-w-6xl">
        {/* Welcome */}
        <div className="mb-8">
           <h1 className="text-3xl font-bold text-foreground">
             Welcome{user?.email ? `, ${user.email.split('@')[0]}` : ''}!
           </h1>
           <p className="text-muted-foreground mt-2">
             Monitor your AI-powered career journey and role compatibility
           </p>
        </div>

        {/* Analytics Grid */}
        <div className="grid lg:grid-cols-2 gap-8 items-start mb-8">
          <ProgressTracker />
          <MatchFitScore />
        </div>

        {/* Quick Actions */}
        <div>
           <div className="flex items-center gap-4 mb-6">
              <h2 className="text-xl font-semibold text-foreground">Quick Actions</h2>
              <div className="flex-1 border-t border-muted" />
           </div>
           
           <div className="grid md:grid-cols-4 gap-4">
             {[
               { href: '/onboarding', icon: Target, label: 'Connect Profiles', desc: 'Sync LinkedIn & GitHub' },
               { href: '/analysis', icon: Brain, label: 'View Analysis', desc: 'See AI insights' },
               { href: '/jobs', icon: Briefcase, label: 'Find Jobs', desc: 'Market recommendations' },
               { href: '/profile', icon: Activity, label: 'Profile Management', desc: 'Update your assets' }
             ].map((action, i) => (
               <Link key={i} href={action.href}>
                 <div className="bg-card rounded-xl p-6 border hover:shadow-sm transition-shadow cursor-pointer h-full group">
                   <div className="w-10 h-10 rounded-lg bg-primary/5 flex items-center justify-center mb-6 group-hover:scale-105 transition-transform">
                     <action.icon className="w-5 h-5 text-primary" />
                   </div>
                   <div>
                      <h3 className="font-semibold text-foreground text-sm mb-1">{action.label}</h3>
                      <p className="text-xs text-muted-foreground leading-tight">{action.desc}</p>
                   </div>
                 </div>
               </Link>
             ))}
           </div>
        </div>
      </main>
    </div>
  )
}
