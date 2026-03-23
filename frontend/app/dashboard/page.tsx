'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import Navbar from '@/components/Navbar'
import { Brain, LogOut, ChevronRight, Sparkles, Target, TrendingUp } from 'lucide-react'

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
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Welcome */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-foreground">
              Welcome{user?.email ? `, ${user.email.split('@')[0]}` : ''}!
            </h1>
            <p className="text-muted-foreground mt-2">
              Your AI-powered career journey starts here
            </p>
          </div>

          {/* Analysis Status Card */}
          <div className="bg-card rounded-2xl shadow-card p-8 border mb-8">
            <div className="flex items-start gap-4">
              <div className="w-16 h-16 rounded-2xl bg-warning/10 flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-8 h-8 text-warning" />
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-semibold text-foreground mb-2">
                  Your analysis is not ready yet
                </h2>
                <p className="text-muted-foreground mb-4">
                  Connect your profiles to get personalized career recommendations powered by AI.
                </p>
                <Link href="/onboarding">
                  <Button className="bg-primary hover:bg-primary/90">
                    Get Started
                    <ChevronRight className="w-4 h-4 ml-2" />
                  </Button>
                </Link>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <h2 className="text-xl font-semibold text-foreground mb-4">Quick Actions</h2>
          <div className="grid md:grid-cols-3 gap-4">
            <Link href="/onboarding">
              <div className="bg-card rounded-xl p-6 border hover:shadow-card-hover transition-shadow cursor-pointer group">
                <Target className="w-8 h-8 text-primary mb-3 group-hover:scale-110 transition-transform" />
                <h3 className="font-semibold text-foreground mb-1">Connect Profiles</h3>
                <p className="text-sm text-muted-foreground">Link your GitHub, LeetCode, and more</p>
              </div>
            </Link>
            
            <Link href="/analysis">
              <div className="bg-card rounded-xl p-6 border hover:shadow-card-hover transition-shadow cursor-pointer group">
                <Brain className="w-8 h-8 text-accent-violet mb-3 group-hover:scale-110 transition-transform" />
                <h3 className="font-semibold text-foreground mb-1">View Analysis</h3>
                <p className="text-sm text-muted-foreground">See your AI-generated career insights</p>
              </div>
            </Link>
            
            <Link href="/jobs">
              <div className="bg-card rounded-xl p-6 border hover:shadow-card-hover transition-shadow cursor-pointer group">
                <TrendingUp className="w-8 h-8 text-success mb-3 group-hover:scale-110 transition-transform" />
                <h3 className="font-semibold text-foreground mb-1">Find Jobs</h3>
                <p className="text-sm text-muted-foreground">Discover opportunities matched to you</p>
              </div>
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
