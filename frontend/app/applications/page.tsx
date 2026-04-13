'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import Navbar from '@/components/Navbar'
import {
  Briefcase, Loader2, ArrowRight, Building2,
  MapPin, Sparkles, TrendingUp, CheckCircle, XCircle,
  Clock, MessageSquare, ChevronRight, AlertCircle
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const STATUS_CONFIG = {
  applied: { label: 'Applied', color: 'bg-yellow-500/20 border-yellow-500/40 text-yellow-400', icon: Clock },
  interview: { label: 'Interview', color: 'bg-blue-500/20 border-blue-500/40 text-blue-400', icon: MessageSquare },
  rejected: { label: 'Rejected', color: 'bg-red-500/20 border-red-500/40 text-red-400', icon: XCircle },
  offer: { label: 'Offer', color: 'bg-green-500/20 border-green-500/40 text-green-400', icon: CheckCircle }
}

export default function ApplicationsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState<any>(null)
  const [applications, setApplications] = useState<any[]>([])
  const [statusCounts, setStatusCounts] = useState<any>({})
  const [applicationsLoading, setApplicationsLoading] = useState(false)
  const [filter, setFilter] = useState<string | null>(null)
  const [updatingId, setUpdatingId] = useState<string | null>(null)

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        router.push('/auth/login')
        return
      }
      setUser(user)
      await loadApplications(user)
    }
    checkAuth()
  }, [router])

  const loadApplications = async (userData: any) => {
    setApplicationsLoading(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      
      const headers: Record<string, string> = {}
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const url = filter 
        ? `${apiUrl}/api/jobs/applications?status=${filter}`
        : `${apiUrl}/api/jobs/applications`

      const response = await fetch(url, { headers })
      
      if (response.ok) {
        const data = await response.json()
        setApplications(data.applications || [])
        setStatusCounts(data.status_counts || {})
      }
    } catch (err) {
      console.error('Failed to load applications:', err)
    } finally {
      setApplicationsLoading(false)
      setLoading(false)
    }
  }

  const updateStatus = async (jobId: string, newStatus: string) => {
    if (!user) return
    setUpdatingId(jobId)

    try {
      const { data: { session } } = await supabase.auth.getSession()
      
      const headers: Record<string, string> = {}
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/jobs/applications/${jobId}`, {
        method: 'PUT',
        headers: {
          ...headers,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: newStatus })
      })

      if (response.ok) {
        await loadApplications(user)
      }
    } catch (err) {
      console.error('Failed to update status:', err)
    } finally {
      setUpdatingId(null)
    }
  }

  const deleteApplication = async (jobId: string) => {
    if (!user) return
    
    try {
      const { data: { session } } = await supabase.auth.getSession()
      
      const headers: Record<string, string> = {}
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      await fetch(`${apiUrl}/api/jobs/applications/${jobId}`, {
        method: 'DELETE',
        headers
      })

      await loadApplications(user)
    } catch (err) {
      console.error('Failed to delete application:', err)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-[#6C3FC8] mx-auto mb-4" />
          <p className="text-slate-400 font-black uppercase tracking-widest text-[10px]">Loading Applications...</p>
        </div>
      </div>
    )
  }

  const totalApplications = Object.values(statusCounts).reduce((a: any, b: any) => a + b, 0)

  return (
    <div className="min-h-screen bg-[#0F172A] text-white selection:bg-purple-500/30">
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-12">
        <motion.div initial="hidden" animate="visible" variants={{
          hidden: { opacity: 0 },
          visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
        }}>
          {/* Header */}
          <motion.div variants={{
            hidden: { opacity: 0, y: 20 },
            visible: { opacity: 1, y: 0 }
          }} className="bg-[#1E293B] rounded-[2.5rem] p-10 mb-12 border border-white/5 relative overflow-hidden group shadow-2xl">
            <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-purple-500/10 to-transparent pointer-events-none" />
            <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-8">
              <div>
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-3 bg-purple-500/20 rounded-2xl border border-purple-500/30 shadow-[0_0_20px_rgba(108,63,200,0.3)]">
                    <Briefcase className="w-8 h-8 text-[#6C3FC8]" />
                  </div>
                  <div>
                    <h1 className="text-4xl font-black tracking-tighter uppercase italic">Application <span className="text-purple-400">Tracker</span></h1>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                      <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Pipeline Active</p>
                    </div>
                  </div>
                </div>
                <p className="text-slate-400 text-sm font-bold max-w-lg leading-relaxed">
                  Track your job applications and see your progress through the hiring pipeline.
                </p>
              </div>
              <div className="text-right">
                <div className="text-5xl font-black text-white/5 uppercase tracking-tighter select-none">{totalApplications}</div>
                <p className="text-[10px] font-black uppercase text-slate-500 tracking-widest">Total Applications</p>
              </div>
            </div>
          </motion.div>

          {/* Stats Cards */}
          <motion.div variants={{
            hidden: { opacity: 0, y: 20 },
            visible: { opacity: 1, y: 0 }
          }} className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
            {Object.entries(STATUS_CONFIG).map(([status, config]) => {
              const Icon = config.icon
              const count = statusCounts[status] || 0
              return (
                <motion.div
                  key={status}
                  whileHover={{ y: -5 }}
                  onClick={() => setFilter(filter === status ? null : status)}
                  className={`bg-[#1E293B] rounded-3xl p-6 border cursor-pointer transition-all ${
                    filter === status 
                      ? 'border-purple-500/50 shadow-[0_10px_30px_-10px_rgba(108,63,200,0.3)]' 
                      : 'border-white/5 hover:border-white/10'
                  }`}
                >
                  <div className={`w-10 h-10 rounded-2xl ${config.color} flex items-center justify-center mb-4`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="text-3xl font-black text-white mb-1">{count}</div>
                  <div className="text-[10px] font-black uppercase text-slate-500 tracking-widest">{config.label}</div>
                </motion.div>
              )
            })}
          </motion.div>

          {/* Applications List */}
          <motion.section variants={{
            hidden: { opacity: 0, y: 20 },
            visible: { opacity: 1, y: 0 }
          }}>
            <div className="flex items-center justify-between mb-8 px-2">
              <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-400" /> {filter ? `${STATUS_CONFIG[filter as keyof typeof STATUS_CONFIG].label} Applications` : 'All Applications'}
              </h3>
              {filter && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setFilter(null)}
                  className="bg-[#1E293B] border-white/10 hover:border-purple-500/30 text-slate-400 hover:text-white rounded-xl py-3 px-4 font-black uppercase tracking-widest text-[10px]"
                >
                  Clear Filter
                </Button>
              )}
            </div>

            {applicationsLoading ? (
              <div className="bg-[#1E293B] rounded-[2rem] border border-white/5 p-20 text-center flex flex-col items-center shadow-xl">
                <div className="w-16 h-16 rounded-full border-4 border-[#6C3FC8]/20 border-t-[#6C3FC8] animate-spin mb-6" />
                <p className="text-slate-500 font-black uppercase tracking-widest text-xs">Loading Applications...</p>
              </div>
            ) : applications.length > 0 ? (
              <div className="space-y-4">
                <AnimatePresence mode='popLayout'>
                  {applications.map((app, i) => {
                    const statusConfig = STATUS_CONFIG[app.status as keyof typeof STATUS_CONFIG]
                    const StatusIcon = statusConfig?.icon || Clock

                    return (
                      <motion.div
                        key={app.job_id || app.id}
                        layout
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-[#1E293B] rounded-[2rem] border border-white/5 p-6 relative overflow-hidden group hover:border-purple-500/30 transition-all shadow-xl"
                      >
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                          {/* Job Info */}
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-3">
                              <h4 className="text-lg font-black text-white uppercase tracking-tight">
                                {app.title}
                              </h4>
                              <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border ${statusConfig?.color || 'border-slate-500'}`}>
                                <StatusIcon className="w-3 h-3 inline mr-1" />
                                {statusConfig?.label || app.status}
                              </span>
                            </div>
                            <div className="flex flex-wrap items-center gap-4 text-xs font-black text-slate-400 uppercase tracking-tighter">
                              <div className="flex items-center gap-2">
                                <Building2 className="w-3 h-3 text-purple-500" /> {app.company || 'Unknown Company'}
                              </div>
                              <div className="flex items-center gap-2">
                                <MapPin className="w-3 h-3 text-slate-600" /> {app.location || 'Remote'}
                              </div>
                              {app.missing_skills && app.missing_skills.length > 0 && (
                                <div className="flex items-center gap-2">
                                  <AlertCircle className="w-3 h-3 text-yellow-500" />
                                  <span className="text-yellow-400">Missing: {app.missing_skills.slice(0, 2).join(', ')}</span>
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Actions */}
                          <div className="flex items-center gap-3">
                            {/* Status Update Dropdown */}
                            <div className="relative group/menu">
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={updatingId === app.job_id}
                                className="bg-[#0F172A] border-white/10 hover:border-purple-500/30 text-slate-400 hover:text-white rounded-xl py-4 px-4 font-black uppercase tracking-widest text-[10px]"
                              >
                                {updatingId === app.job_id ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <>Update <ChevronRight className="w-3 h-3 ml-1 rotate-90" /></>
                                )}
                              </Button>
                              <div className="absolute right-0 top-full mt-2 w-48 bg-[#1E293B] border border-white/10 rounded-xl shadow-xl opacity-0 invisible group-hover/menu:opacity-100 group-hover/menu:visible transition-all z-10">
                                {Object.entries(STATUS_CONFIG).map(([status, config]) => (
                                  <button
                                    key={status}
                                    onClick={() => updateStatus(app.job_id, status)}
                                    className={`w-full text-left px-4 py-3 text-[10px] font-black uppercase tracking-widest hover:bg-white/5 first:rounded-t-xl last:rounded-b-xl ${
                                      app.status === status ? 'text-purple-400' : 'text-slate-400'
                                    }`}
                                  >
                                    Move to {config.label}
                                  </button>
                                ))}
                              </div>
                            </div>

                            {/* Apply Link */}
                            {app.apply_url && app.apply_url !== '#' && (
                              <Button
                                size="sm"
                                className="bg-[#6C3FC8] hover:bg-[#6C3FC8]/90 text-white font-black uppercase tracking-tighter py-4 px-4 rounded-xl text-[10px]"
                                onClick={() => window.open(app.apply_url, '_blank')}
                              >
                                View
                              </Button>
                            )}

                            {/* Delete */}
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => deleteApplication(app.job_id)}
                              className="border-red-500/20 text-red-400 hover:bg-red-500/10 rounded-xl py-4 px-3"
                            >
                              ×
                            </Button>
                          </div>
                        </div>

                        {/* Missing Skills Feedback */}
                        {app.status === 'rejected' && app.missing_skills && app.missing_skills.length > 0 && (
                          <div className="mt-4 pt-4 border-t border-white/5">
                            <div className="flex items-start gap-3 p-4 bg-red-500/10 rounded-xl border border-red-500/20">
                              <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
                              <div>
                                <p className="text-[10px] font-black text-red-400 uppercase tracking-widest mb-2">
                                  Skills to improve for similar roles
                                </p>
                                <div className="flex flex-wrap gap-2">
                                  {app.missing_skills.map((skill: string, idx: number) => (
                                    <span key={idx} className="px-2 py-1 bg-red-500/20 rounded-full text-[9px] font-bold text-red-300">
                                      {skill}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                      </motion.div>
                    )
                  })}
                </AnimatePresence>
              </div>
            ) : (
              <div className="bg-[#1E293B] rounded-[2rem] border border-white/5 border-dashed p-20 text-center flex flex-col items-center">
                <Briefcase className="w-10 h-10 text-slate-800 mb-4" />
                <p className="text-slate-600 font-black uppercase tracking-widest text-xs">
                  {filter ? `No ${STATUS_CONFIG[filter as keyof typeof STATUS_CONFIG].label.toLowerCase()} applications yet` : 'No applications yet'}
                </p>
                <Button
                  className="mt-6 bg-[#6C3FC8] hover:bg-[#6C3FC8]/90 text-white font-black uppercase tracking-tighter py-4 px-8 rounded-xl text-xs"
                  onClick={() => router.push('/jobs')}
                >
                  Find Jobs <ArrowRight className="ml-2 w-4 h-4" />
                </Button>
              </div>
            )}
          </motion.section>
        </motion.div>
      </main>
    </div>
  )
}