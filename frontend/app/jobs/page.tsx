'use client'
import CareerRoadmap from '@/components/CareerRoadmap'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import Navbar from '@/components/Navbar'
import {
  Brain, Briefcase, Loader2, ArrowRight, Building2,
  Globe, Search, GraduationCap, TrendingUp, ExternalLink, RefreshCw,
  MapPin, Star, Zap, ChevronRight, Sparkles, Target, Layers
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface CareerPath {
  name?: string
  career_name?: string
  match_percentage?: number
}

export default function JobsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState<any>(null)
  const [profile, setProfile] = useState<any>(null)
  const [analysis, setAnalysis] = useState<any>(null)
  const [targetCareer, setTargetCareer] = useState('Full Stack Developer')
  const [jobs, setJobs] = useState<any[]>([])
  const [jobsLoading, setJobsLoading] = useState(false)
  const [jobsError, setJobsError] = useState<string | null>(null)

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        router.push('/auth/login')
        return
      }
      setUser(user)
      await loadUserData(user.id)
    }
    checkAuth()
  }, [router])

  const loadUserData = async (userId: string) => {
    try {
      const { data: profileData } = await supabase
        .from('profiles')
        .select('*')
        .eq('user_id', userId)
        .single()

      if (profileData) {
        setProfile(profileData)
      }

      const { data: analysisData } = await supabase
        .from('analyses')
        .select('*')
        .eq('user_id', userId)
        .single()

      if (analysisData) {
        setAnalysis(analysisData)
        const careerPaths = analysisData.career_paths || []
        if (Array.isArray(careerPaths) && careerPaths.length > 0) {
          const topPath = careerPaths[0]
          const careerName = topPath?.name || topPath?.career_name || 'Full Stack Developer'
          setTargetCareer(careerName)
          fetchRealJobs(careerName)
        }
      }
    } catch (err) {
      console.error('Error loading user data:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchRealJobs = async (query: string) => {
    setJobsLoading(true)
    setJobsError(null)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/jobs?query=${encodeURIComponent(query)}`)
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`)
      }
      const data = await response.json()
      setJobs(data.jobs || [])
    } catch (err) {
      console.error("Failed to fetch jobs:", err)
      setJobsError("Job search is currently unavailable. Please try again later.")
    } finally {
      setJobsLoading(false)
    }
  }

  const techCompanies = [
    {
      name: 'Google',
      careersUrl: 'https://careers.google.com/jobs',
      description: 'Software Engineer, Frontend Developer, Backend',
      color: 'bg-red-500',
      initialColor: 'text-red-400'
    },
    {
      name: 'Microsoft',
      careersUrl: 'https://careers.microsoft.com',
      description: 'Full Stack Developer, Cloud Engineer, Data Scientist',
      color: 'bg-blue-500',
      initialColor: 'text-blue-400'
    },
    {
      name: 'Amazon',
      careersUrl: 'https://www.amazon.jobs',
      description: 'Software Development Engineer, DevOps, ML Engineer',
      color: 'bg-orange-500',
      initialColor: 'text-orange-400'
    },
    {
      name: 'Meta',
      careersUrl: 'https://metacareers.com',
      description: 'React Developer, iOS/Android Engineer, Backend',
      color: 'bg-blue-600',
      initialColor: 'text-blue-500'
    },
    {
      name: 'Apple',
      careersUrl: 'https://jobs.apple.com',
      description: 'Swift Developer, ML Engineer, Systems Engineer',
      color: 'bg-gray-400',
      initialColor: 'text-slate-300'
    }
  ]

  const internshipPlatforms = [
    {
      name: 'Internshala',
      url: 'https://internshala.com/internships',
      description: 'The preferred hub for student internships in India.',
      icon: GraduationCap,
      accent: 'border-blue-500/30'
    },
    {
      name: 'LinkedIn Jobs',
      url: 'https://www.linkedin.com/jobs/',
      description: 'Global entry-level opportunities and professional networking.',
      icon: Briefcase,
      accent: 'border-purple-500/30'
    },
    {
      name: 'Naukri',
      url: 'https://www.naukri.com/nlogin/login',
      description: 'India\'s largest job platform for freshers and professionals.',
      icon: Search,
      accent: 'border-red-500/30'
    }
  ]

  const jobSearchByRole = [
    {
      platform: 'LinkedIn',
      url: `https://www.linkedin.com/jobs/search/?keywords=${encodeURIComponent(targetCareer)}`,
      icon: Briefcase,
      color: 'text-blue-500'
    },
    {
      platform: 'Naukri',
      url: `https://www.naukri.com/${encodeURIComponent(targetCareer.toLowerCase().replace(/\s+/g, '-'))}-jobs`,
      icon: Search,
      color: 'text-red-500'
    },
    {
      platform: 'Indeed',
      url: `https://www.indeed.com/jobs?q=${encodeURIComponent(targetCareer)}`,
      icon: Globe,
      color: 'text-blue-400'
    },
    {
      platform: 'Glassdoor',
      url: `https://www.glassdoor.com/Job/jobs.htm?sc.keyword=${encodeURIComponent(targetCareer)}`,
      icon: Building2,
      color: 'text-green-500'
    }
  ]

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-[#6C3FC8] mx-auto mb-4" />
          <p className="text-slate-400 font-black uppercase tracking-widest text-[10px]">Syncing Opportunity Matrix...</p>
        </div>
      </div>
    )
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  }

  return (
    <div className="min-h-screen bg-[#0F172A] text-white selection:bg-purple-500/30">
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 py-12">
        <motion.div initial="hidden" animate="visible" variants={containerVariants}>
          
          {/* Section: Intel Hero */}
          <motion.div variants={itemVariants} className="bg-[#1E293B] rounded-[2.5rem] p-10 mb-12 border border-white/5 relative overflow-hidden group shadow-2xl">
            <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-purple-500/10 to-transparent pointer-events-none" />
            <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-8">
              <div>
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-3 bg-purple-500/20 rounded-2xl border border-purple-500/30 shadow-[0_0_20px_rgba(108,63,200,0.3)]">
                    <Briefcase className="w-8 h-8 text-[#6C3FC8]" />
                  </div>
                  <div>
                    <h1 className="text-4xl font-black tracking-tighter uppercase italic">Opportunity <span className="text-purple-400">Stream</span></h1>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                      <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Global Vacancy Search Active</p>
                    </div>
                  </div>
                </div>
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500/10 rounded-full border border-purple-500/20 text-[#6C3FC8] font-black uppercase tracking-widest text-[10px] mb-4">
                  <Target className="w-3 h-3" /> Target Path: {targetCareer}
                </div>
                <p className="text-slate-400 text-sm font-bold max-w-lg leading-relaxed">
                  Based on your neural career analysis, we've filtered the global job market to prioritize roles in <span className="text-white">{targetCareer}</span>.
                </p>
              </div>
              <div className="text-right">
                 <div className="text-5xl font-black text-white/5 uppercase tracking-tighter select-none">VALIDATED</div>
              </div>
            </div>
          </motion.div>

          {/* Section: Recommended Career Paths */}
          {analysis?.career_paths && analysis.career_paths.length > 0 && (
            <motion.div variants={itemVariants} className="mb-12">
               <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 mb-6 ml-2 flex items-center gap-2">
                 <Layers className="w-4 h-4" /> Neural Compatibility Matrix
               </h3>
               <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  {analysis.career_paths.slice(0, 4).map((path: any, i: number) => (
                    <motion.div
                      key={i}
                      whileHover={{ y: -5 }}
                      className={`bg-[#1E293B] rounded-3xl p-6 border-l-4 transition-all ${
                        i === 0 ? 'border-l-purple-500 border-purple-500/20 shadow-[0_10px_30px_-10px_rgba(108,63,200,0.3)]' : 'border-l-slate-700 border-white/5'
                      }`}
                    >
                      {i === 0 && (
                        <div className="flex items-center gap-1.5 text-[9px] font-black text-purple-400 uppercase tracking-widest mb-3">
                           <Star className="w-3 h-3 fill-current" /> Optimal Match
                        </div>
                      )}
                      <h4 className="font-black text-white text-sm uppercase tracking-tight mb-2 leading-tight">
                        {path.name || path.career_name}
                      </h4>
                      <div className="text-2xl font-black text-yellow-400 drop-shadow-[0_0_10px_rgba(250,204,21,0.2)]">
                        {path.match_percentage}%
                      </div>
                      <div className="text-[9px] font-black uppercase text-slate-500 tracking-widest">Similarity Score</div>
                    </motion.div>
                  ))}
               </div>
            </motion.div>
          )}

          {/* Section: Live Job Matches */}
          <motion.section variants={itemVariants} className="mb-16">
            <div className="flex items-center justify-between mb-8 px-2">
              <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-400" /> Real-Time Opportunities
              </h3>
              <Button
                variant="outline"
                size="sm"
                onClick={() => fetchRealJobs(targetCareer)}
                className="bg-[#1E293B] border-white/10 hover:border-purple-500/30 text-slate-400 hover:text-white rounded-xl py-5 px-6 font-black uppercase tracking-widest text-[10px] group transition-all"
              >
                <RefreshCw className={`w-3 h-3 mr-2 group-hover:rotate-180 transition-transform duration-700 ${jobsLoading ? 'animate-spin' : ''}`} />
                Refresh Stream
              </Button>
            </div>

            {jobsLoading ? (
              <div className="bg-[#1E293B] rounded-[2rem] border border-white/5 p-20 text-center flex flex-col items-center shadow-xl">
                 <div className="w-16 h-16 rounded-full border-4 border-[#6C3FC8]/20 border-t-[#6C3FC8] animate-spin mb-6" />
                 <p className="text-slate-500 font-black uppercase tracking-widest text-xs">Querying Global Recruiters...</p>
              </div>
            ) : jobs.length > 0 ? (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                <AnimatePresence mode='popLayout'>
                  {jobs.map((job, i) => (
                    <motion.div
                      key={i}
                      layout
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      whileHover={{ y: -8 }}
                      className="bg-[#1E293B] rounded-[2.5rem] border border-white/5 p-8 relative overflow-hidden group hover:border-purple-500/30 transition-all shadow-xl"
                    >
                      <div className="absolute top-0 right-0 p-4">
                        <div className="px-3 py-1 bg-green-500/10 border border-green-500/20 rounded-full text-[9px] font-black text-green-400 uppercase tracking-widest animate-pulse shadow-[0_0_15px_rgba(34,197,94,0.2)]">
                           New
                        </div>
                      </div>
                      
                      <div className="mb-8">
                        <h4 className="text-lg font-black text-white leading-tight uppercase tracking-tight mb-4 group-hover:text-purple-300 transition-colors">
                          {job.title}
                        </h4>
                        <div className="space-y-2">
                           <div className="flex items-center gap-2 text-xs font-black text-slate-400 uppercase tracking-tighter">
                              <Building2 className="w-3 h-3 text-purple-500" /> {job.company}
                           </div>
                           <div className="flex items-center gap-2 text-xs font-black text-slate-500 uppercase tracking-tighter">
                              <MapPin className="w-3 h-3 text-slate-600" /> {job.location}
                           </div>
                        </div>
                      </div>

                      <Button
                        className="w-full bg-[#6C3FC8] hover:bg-[#6C3FC8]/90 text-white font-black uppercase tracking-tighter py-7 rounded-2xl shadow-[0_10px_30px_-10px_rgba(108,63,200,0.4)] active:scale-95 transition-all group/btn"
                        onClick={() => {
                          const applyUrl = job.link || job.job_link || job.apply_link || job.url || job.redirect_url || 
                            `https://www.google.com/search?q=${encodeURIComponent(job.title + ' ' + job.company + ' job apply')}`
                          window.open(applyUrl, '_blank')
                        }}
                      >
                        Initiate Application
                        <ExternalLink className="ml-2 w-4 h-4 group-hover/btn:translate-x-1 group-hover/btn:-translate-y-1 transition-transform" />
                      </Button>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            ) : jobsError ? (
              <div className="bg-[#1E293B] rounded-[2rem] border border-white/5 border-dashed p-20 text-center flex flex-col items-center">
                 <p className="text-red-400 font-black uppercase tracking-widest text-xs mb-4">{jobsError}</p>
              </div>
            ) : (
              <div className="bg-[#1E293B] rounded-[2rem] border border-white/5 border-dashed p-20 text-center flex flex-col items-center">
                 <Loader2 className="w-10 h-10 text-slate-800 animate-spin mb-4" />
                 <p className="text-slate-600 font-black uppercase tracking-widest text-xs">No active vacancies detected in the local sector</p>
              </div>
            )}
          </motion.section>

          {/* Section: Tech Giants */}
          <motion.section variants={itemVariants} className="mb-16">
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 mb-8 ml-2 flex items-center gap-2">
               <Building2 className="w-4 h-4" /> Top Tech Hubs
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {techCompanies.map((company, i) => (
                <motion.a
                  key={i}
                  href={company.careersUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  whileHover={{ scale: 1.05 }}
                  className="bg-[#1E293B] rounded-3xl border border-white/5 p-6 text-center group transition-all hover:bg-[#1E293B]/80"
                >
                  <div className={`w-12 h-12 rounded-2xl ${company.color}/10 border border-white/5 flex items-center justify-center mx-auto mb-4`}>
                    <span className={`text-xl font-black ${company.initialColor}`}>{company.name.charAt(0)}</span>
                  </div>
                  <h4 className="font-black text-white text-[11px] uppercase tracking-widest mb-3 group-hover:text-purple-400 transition-colors">
                    {company.name}
                  </h4>
                  <div className="flex items-center justify-center gap-1 text-[9px] font-black text-slate-500 group-hover:text-purple-300 transition-colors">
                    Apply <ChevronRight className="w-3 h-3" />
                  </div>
                </motion.a>
              ))}
            </div>
          </motion.section>

          {/* Section: Hybrid Operations (Internships) */}
          <motion.section variants={itemVariants} className="mb-16">
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 mb-8 ml-2 flex items-center gap-2">
               <GraduationCap className="w-4 h-4" /> Internship Channels (India)
            </h3>
            <div className="grid md:grid-cols-3 gap-6">
              {internshipPlatforms.map((platform, i) => (
                <motion.a
                  key={i}
                  href={platform.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  whileHover={{ x: 5 }}
                  className={`bg-[#1E293B] rounded-[2rem] border-l-4 ${platform.accent} border border-white/5 p-8 group transition-all shadow-xl`}
                >
                  <div className="p-3 bg-white/5 rounded-2xl w-fit mb-6 group-hover:rotate-12 transition-transform">
                    <platform.icon className="w-6 h-6 text-purple-500" />
                  </div>
                  <h4 className="text-lg font-black text-white uppercase tracking-tighter mb-2 group-hover:text-purple-300 transition-colors">
                    {platform.name}
                  </h4>
                  <p className="text-[10px] font-bold text-slate-500 leading-relaxed uppercase tracking-widest mb-6">
                    {platform.description}
                  </p>
                  <Button variant="outline" className="w-full border-purple-500/30 text-purple-400 hover:bg-purple-500 hover:text-white rounded-xl font-black uppercase tracking-widest text-[10px] h-12 transition-all">
                    Search Jobs <ArrowRight className="ml-2 w-3 h-3" />
                  </Button>
                </motion.a>
              ))}
            </div>
          </motion.section>

          {/* Section: Rapid Search (Role Based) */}
          <motion.section variants={itemVariants} className="mb-16">
             <div className="bg-[#1E293B] rounded-[2.5rem] border border-white/5 p-10 shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_at_top_right,rgba(108,63,200,0.1),transparent)] pointer-events-none" />
                <h3 className="text-lg font-black text-white uppercase tracking-tighter mb-8 flex items-center gap-3">
                  <Search className="w-5 h-5 text-purple-400" /> Sequential Sector Search: <span className="text-purple-500 font-black">{targetCareer}</span>
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {jobSearchByRole.map((platform, i) => (
                    <motion.a
                      key={i}
                      href={platform.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      whileHover={{ scale: 1.05 }}
                      className="bg-[#0F172A] rounded-2xl border border-white/5 p-6 flex items-center gap-4 group transition-all hover:border-purple-500/30"
                    >
                      <div className={`p-2 rounded-xl bg-white/5 ${platform.color} transition-colors`}>
                        <platform.icon className="w-5 h-5" />
                      </div>
                      <span className="text-xs font-black uppercase tracking-widest text-slate-400 group-hover:text-white transition-colors">{platform.platform}</span>
                    </motion.a>
                  ))}
                </div>
             </div>
          </motion.section>

          {/* Section: Career Roadmap */}
          {analysis?.roadmap && (
            <motion.div variants={itemVariants} className="mb-16">
              <div className="bg-[#1E293B] rounded-[2.5rem] border border-white/5 p-10 shadow-2xl">
                <div className="flex items-center justify-between mb-10">
                   <h3 className="text-xl font-black text-white uppercase tracking-tighter flex items-center gap-3">
                     <TrendingUp className="w-6 h-6 text-purple-500 shadow-[0_0_15px_rgba(108,63,200,0.4)]" /> Tactical Roadmap
                   </h3>
                   <div className="px-4 py-1.5 bg-yellow-400/10 rounded-full border border-yellow-400/20 text-[10px] font-black text-yellow-400 uppercase tracking-widest">
                      Live Phase Tracking
                   </div>
                </div>
                <CareerRoadmap roadmap={analysis.roadmap} />
              </div>
            </motion.div>
          )}

          {/* Section: Profile Intelligence Summary */}
          {profile && (
            <motion.section variants={itemVariants} className="mb-16">
              <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 mb-6 ml-2">Neural Profile Snapshot</h3>
              <div className="bg-[#1E293B] rounded-[2rem] border border-white/5 p-8">
                <div className="grid md:grid-cols-3 gap-8">
                  <div className="p-4 bg-[#0F172A]/50 rounded-2xl border border-white/5">
                    <p className="text-[9px] font-black text-slate-600 uppercase tracking-widest mb-1">GitHub Endpoint</p>
                    <p className="text-sm font-black text-white group-hover:text-purple-400 transition-colors uppercase tracking-tight">
                      {profile.github_username || 'NOT LINKED'}
                    </p>
                  </div>
                  <div className="p-4 bg-[#0F172A]/50 rounded-2xl border border-white/5">
                    <p className="text-[9px] font-black text-slate-600 uppercase tracking-widest mb-1">LeetCode Core</p>
                    <p className="text-sm font-black text-white uppercase tracking-tight">
                      {profile.leetcode_username || 'NOT LINKED'}
                    </p>
                  </div>
                  <div className="p-4 bg-[#0F172A]/50 rounded-2xl border border-white/5">
                    <p className="text-[9px] font-black text-slate-600 uppercase tracking-widest mb-1">Experience Level</p>
                    <p className="text-sm font-black text-yellow-400 uppercase tracking-tight">
                      {analysis?.analysis?.experience_level || analysis?.experience_level || 'ANALYZING...'}
                    </p>
                  </div>
                </div>
                <div className="mt-8 pt-8 border-t border-white/5 flex justify-center md:justify-start">
                  <Link href="/analysis">
                    <Button variant="outline" className="border-white/10 text-slate-400 hover:text-white rounded-xl h-12 px-8 font-black uppercase tracking-widest text-[10px]">
                      View Global System Analysis <ArrowRight className="ml-2 w-4 h-4" />
                    </Button>
                  </Link>
                </div>
              </div>
            </motion.section>
          )}
        </motion.div>
      </main>

      {/* Decorative Orbs */}
      <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden opacity-50">
        <div className="absolute top-[10%] right-[-10%] w-[600px] h-[600px] bg-purple-900/10 rounded-full blur-[150px]" />
        <div className="absolute bottom-[-5%] left-[-10%] w-[500px] h-[500px] bg-blue-900/10 rounded-full blur-[120px]" />
      </div>
    </div>
  )
}
