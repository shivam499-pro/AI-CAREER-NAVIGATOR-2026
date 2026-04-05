'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import Navbar from '@/components/Navbar'
import { 
  Brain, Loader2, Save, Plus, X, CheckCircle,
  GraduationCap, Code, Briefcase, Award, Target,
  ArrowRight, User, Github, Globe, Link as LinkIcon,
  Sparkles, Zap, ChevronRight
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface ProfileData {
  college_name: string
  degree: string
  branch: string
  current_year: string
  graduation_year: number
  cgpa: number
  extra_skills: string[]
  experience: { company: string; role: string; duration: string; description: string }[]
  certificates: { name: string; issuer: string }[]
  target_companies: string[]
  preferred_location: string
  career_goal: string
  open_to: string
  codechef_rating: number
  codeforces_rating: number
  hackathon_wins: number
}

const initialProfile: ProfileData = {
  college_name: '',
  degree: '',
  branch: '',
  current_year: '',
  graduation_year: 0,
  cgpa: 0,
  extra_skills: [],
  experience: [],
  certificates: [],
  target_companies: [],
  preferred_location: '',
  career_goal: '',
  open_to: 'Both',
  codechef_rating: 0,
  codeforces_rating: 0,
  hackathon_wins: 0
}

export default function ProfilePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [user, setUser] = useState<any>(null)
  const [profile, setProfile] = useState<ProfileData>(initialProfile)
  const [githubConnected, setGithubConnected] = useState(false)
  const [leetcodeConnected, setLeetcodeConnected] = useState(false)
  const [resumeUploaded, setResumeUploaded] = useState(false)

  // Tag input states
  const [skillInput, setSkillInput] = useState('')
  const [companyInput, setCompanyInput] = useState('')

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        router.push('/auth/login')
        return
      }
      setUser(user)
      await loadProfile(user.id)
    }
    checkAuth()
  }, [router])

  const loadProfile = async (userId: string) => {
    try {
      const { data: profileData } = await supabase
        .from('profiles')
        .select('*')
        .eq('user_id', userId)
        .single()

      if (profileData) {
        setGithubConnected(!!profileData.github_username)
        setLeetcodeConnected(!!profileData.leetcode_username)
        setResumeUploaded(!!profileData.resume_text)

        setProfile({
          college_name: profileData.college_name || '',
          degree: profileData.degree || '',
          branch: profileData.branch || '',
          current_year: profileData.current_year || '',
          graduation_year: profileData.graduation_year || 0,
          cgpa: profileData.cgpa || 0,
          extra_skills: profileData.extra_skills || [],
          experience: profileData.experience || [],
          certificates: profileData.certificates || [],
          target_companies: profileData.target_companies || [],
          preferred_location: profileData.preferred_location || '',
          career_goal: profileData.career_goal || '',
          open_to: profileData.open_to || 'Both',
          codechef_rating: profileData.codechef_rating || 0,
          codeforces_rating: profileData.codeforces_rating || 0,
          hackathon_wins: profileData.hackathon_wins || 0
        })
      }
    } catch (err) {
      console.error('Error loading profile:', err)
    } finally {
      setLoading(false)
    }
  }

  const calculateCompleteness = () => {
    let score = 0
    if (githubConnected) score += 20
    if (leetcodeConnected) score += 20
    if (resumeUploaded) score += 20
    if (profile.college_name && profile.degree) score += 15
    if (profile.extra_skills.length >= 3) score += 10
    if (profile.experience.length > 0) score += 10
    if (profile.career_goal) score += 5
    return score
  }

  const handleSave = async () => {
    if (!user) return
    
    setSaving(true)
    try {
      const { error } = await supabase
        .from('profiles')
        .update({
          college_name: profile.college_name,
          degree: profile.degree,
          branch: profile.branch,
          current_year: profile.current_year,
          graduation_year: profile.graduation_year,
          cgpa: profile.cgpa,
          extra_skills: profile.extra_skills,
          experience: profile.experience,
          certificates: profile.certificates,
          target_companies: profile.target_companies,
          preferred_location: profile.preferred_location,
          career_goal: profile.career_goal,
          open_to: profile.open_to,
          codechef_rating: profile.codechef_rating,
          codeforces_rating: profile.codeforces_rating,
          hackathon_wins: profile.hackathon_wins
        })
        .eq('user_id', user.id)

      if (error) throw error
      
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      console.error('Error saving profile:', err)
    } finally {
      setSaving(false)
    }
  }

  const addSkill = () => {
    if (skillInput.trim() && !profile.extra_skills.includes(skillInput.trim())) {
      setProfile({ ...profile, extra_skills: [...profile.extra_skills, skillInput.trim()] })
      setSkillInput('')
    }
  }

  const addCompany = () => {
    if (companyInput.trim() && !profile.target_companies.includes(companyInput.trim())) {
      setProfile({ ...profile, target_companies: [...profile.target_companies, companyInput.trim()] })
      setCompanyInput('')
    }
  }

  const updateExperience = (index: number, field: string, value: string) => {
    const updated = [...profile.experience]
    updated[index] = { ...updated[index], [field]: value }
    setProfile({ ...profile, experience: updated })
  }

  const updateCertificate = (index: number, field: string, value: string) => {
    const updated = [...profile.certificates]
    updated[index] = { ...updated[index], [field]: value }
    setProfile({ ...profile, certificates: updated })
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex items-center justify-center text-white">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-[#6C3FC8] mx-auto mb-4" />
          <p className="text-slate-400 font-black uppercase tracking-widest text-[10px]">Syncing Performance Protocol...</p>
        </div>
      </div>
    )
  }

  const completeness = calculateCompleteness()
  const userInitial = user?.email?.charAt(0).toUpperCase() || 'U'

  // Animation variants
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { 
        staggerChildren: 0.1,
        delayChildren: 0.1
      }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  }

  return (
    <div className="min-h-screen bg-[#0F172A] text-white selection:bg-purple-500/30">
      <Navbar />
      <main className="max-w-5xl mx-auto px-4 py-12">
        <motion.div
           initial="hidden"
           animate="visible"
           variants={containerVariants}
        >
          {/* Header & Completeness Tracker */}
          <motion.div variants={itemVariants} className="bg-[#1E293B] rounded-[2.5rem] p-8 md:p-10 mb-8 border border-white/5 relative overflow-hidden group shadow-2xl">
            <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-purple-500/5 to-transparent pointer-events-none" />
            
            <div className="flex flex-col md:flex-row items-center gap-8 relative z-10">
              {/* User Avatar Circle */}
              <div className="relative">
                <div className="w-24 h-24 rounded-full bg-gradient-to-br from-[#6C3FC8] to-purple-400 flex items-center justify-center text-4xl font-black shadow-[0_0_40px_rgba(108,63,200,0.5)] border-4 border-white/10 relative z-10">
                  {userInitial}
                </div>
                <div className="absolute inset-0 bg-[#6C3FC8]/20 blur-2xl rounded-full" />
              </div>
              
              <div className="flex-1 w-full text-center md:text-left">
                <div className="flex items-center justify-center md:justify-between mb-4">
                  <div>
                    <h1 className="text-3xl font-black tracking-tighter uppercase mb-1">Intelligence <span className="text-purple-400 text-sm tracking-widest ml-1 italic">Profile</span></h1>
                    <p className="text-slate-500 text-[10px] font-black uppercase tracking-[0.2em]">{user?.email}</p>
                  </div>
                  <div className="hidden md:block text-right">
                    <span className="text-3xl font-black text-yellow-400 drop-shadow-[0_0_10px_rgba(250,204,21,0.3)]">{completeness}%</span>
                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Calibration Level</p>
                  </div>
                </div>
                
                {/* Progress Bar */}
                <div className="h-3 bg-[#0F172A] rounded-full overflow-hidden border border-white/5 p-0.5 mb-6">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${completeness}%` }}
                    transition={{ duration: 1.5, ease: "circOut" }}
                    className="h-full bg-gradient-to-r from-[#6C3FC8] via-purple-400 to-yellow-400 rounded-full relative"
                  >
                    <div className="absolute inset-0 bg-[linear-gradient(45deg,transparent_25%,rgba(255,255,255,0.1)_50%,transparent_75%)] bg-[length:20px_20px] animate-[slide_1s_linear_infinite]" />
                  </motion.div>
                </div>
                
                {/* Checkmarks */}
                <div className="flex flex-wrap justify-center md:justify-start gap-4 text-[9px] font-black uppercase tracking-[0.2em]">
                  {[
                    { label: 'GitHub', ok: githubConnected },
                    { label: 'LeetCode', ok: leetcodeConnected },
                    { label: 'Resume', ok: resumeUploaded },
                    { label: 'Academic', ok: profile.college_name && profile.degree },
                    { label: 'Skills', ok: profile.extra_skills.length >= 3 },
                    { label: 'Experience', ok: profile.experience.length > 0 },
                    { label: 'Goals', ok: profile.career_goal }
                  ].map((task) => (
                    <div key={task.label} className={`flex items-center gap-1.5 ${task.ok ? 'text-green-400' : 'text-slate-600'}`}>
                      <div className={`w-1.5 h-1.5 rounded-full ${task.ok ? 'bg-green-500 shadow-[0_0_5px_#22c55e]' : 'bg-slate-700'}`} />
                      {task.label}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>

          <AnimatePresence>
            {saved && (
              <motion.div 
                initial={{ opacity: 0, y: -20 }} 
                animate={{ opacity: 1, y: 0 }} 
                exit={{ opacity: 0 }} 
                className="mb-8 p-4 bg-green-500/10 border border-green-500/20 rounded-2xl flex items-center justify-center gap-3 shadow-[0_0_20px_rgba(34,197,94,0.1)]"
              >
                <CheckCircle className="w-5 h-5 text-green-400 font-bold" />
                <p className="text-green-400 font-black uppercase tracking-widest text-xs text-center">Neural Profile Synchronized Successfully</p>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="grid lg:grid-cols-2 gap-8 mb-12">
            {/* Academic Information */}
            <motion.section variants={itemVariants} className="bg-[#1E293B] rounded-[2.5rem] border-l-4 border-l-purple-500 border border-white/5 p-8 shadow-xl group">
              <h3 className="text-lg font-black text-white uppercase tracking-widest mb-10 flex items-center gap-4">
                <div className="p-3 bg-purple-500/10 rounded-2xl border border-purple-500/20 group-hover:rotate-12 transition-transform">
                  <GraduationCap className="w-6 h-6 text-[#6C3FC8]" />
                </div>
                Academic Architecture
              </h3>
              <div className="space-y-6">
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="md:col-span-2">
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">Foundation / College</label>
                    <input 
                      type="text" 
                      value={profile.college_name} 
                      onChange={(e) => setProfile({ ...profile, college_name: e.target.value })} 
                      className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-[#6C3FC8] outline-none transition-all placeholder:text-slate-700" 
                      placeholder="Institute Name" 
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">Degree</label>
                    <select 
                      value={profile.degree} 
                      onChange={(e) => setProfile({ ...profile, degree: e.target.value })} 
                      className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-[#6C3FC8] outline-none appearance-none cursor-pointer"
                    >
                      <option value="">Select</option>
                      <option value="B.Tech">B.Tech</option>
                      <option value="BCA">BCA</option>
                      <option value="MCA">MCA</option>
                      <option value="B.Sc">B.Sc</option>
                      <option value="MBA">MBA</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">Branch</label>
                    <select 
                      value={profile.branch} 
                      onChange={(e) => setProfile({ ...profile, branch: e.target.value })} 
                      className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-[#6C3FC8] outline-none appearance-none cursor-pointer"
                    >
                      <option value="">Select</option>
                      <option value="CSE">CSE</option>
                      <option value="IT">IT</option>
                      <option value="ECE">ECE</option>
                      <option value="Mechanical">Mechanical</option>
                      <option value="Civil">Civil</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">Timeline</label>
                    <select 
                      value={profile.current_year} 
                      onChange={(e) => setProfile({ ...profile, current_year: e.target.value })} 
                      className="w-full bg-[#0F172A]/50 border border-white/10 rounded-xl p-3 text-xs font-bold focus:ring-2 focus:ring-[#6C3FC8] outline-none"
                    >
                      <option value="">Year</option>
                      <option value="1st Year">1st</option>
                      <option value="2nd Year">2nd</option>
                      <option value="3rd Year">3rd</option>
                      <option value="Final Year">Final</option>
                      <option value="Graduated">Grad</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">Exit</label>
                    <input 
                      type="number" 
                      value={profile.graduation_year || ''} 
                      onChange={(e) => setProfile({ ...profile, graduation_year: parseInt(e.target.value) || 0 })} 
                      className="w-full bg-[#0F172A]/50 border border-white/10 rounded-xl p-3 text-xs font-bold outline-none placeholder:text-slate-700" 
                      placeholder="2026" 
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">CGPA</label>
                    <input 
                      type="number" 
                      step="0.1" 
                      max="10" 
                      value={profile.cgpa || ''} 
                      onChange={(e) => setProfile({ ...profile, cgpa: parseFloat(e.target.value) || 0 })} 
                      className="w-full bg-[#0F172A]/50 border border-white/10 rounded-xl p-3 text-xs font-bold outline-none placeholder:text-slate-700" 
                      placeholder="8.5" 
                    />
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Technical Skills */}
            <motion.section variants={itemVariants} className="bg-[#1E293B] rounded-[2.5rem] border-l-4 border-l-purple-500 border border-white/5 p-8 shadow-xl group">
              <h3 className="text-lg font-black text-white uppercase tracking-widest mb-10 flex items-center gap-4">
                <div className="p-3 bg-purple-500/10 rounded-2xl border border-purple-500/20 group-hover:rotate-12 transition-transform">
                  <Code className="w-6 h-6 text-[#6C3FC8]" />
                </div>
                Core Capabilities
              </h3>
              
              <div className="flex flex-wrap gap-2 mb-8 min-h-[140px] items-start p-6 bg-[#0F172A]/30 rounded-3xl border border-white/5 shadow-inner">
                <AnimatePresence>
                  {profile.extra_skills.map((skill, i) => (
                    <motion.span 
                      key={i}
                      initial={{ scale: 0.8, opacity: 0 }} 
                      animate={{ scale: 1, opacity: 1 }} 
                      exit={{ scale: 0.8, opacity: 0 }} 
                      className="px-4 py-2 bg-[#0F172A] border border-[#6C3FC8]/30 hover:border-[#6C3FC8] text-slate-200 rounded-2xl flex items-center gap-2 text-[11px] font-black uppercase tracking-widest transition-all group/skill"
                    >
                      {skill}
                      <button 
                        onClick={() => setProfile({ ...profile, extra_skills: profile.extra_skills.filter((_, idx) => idx !== i) })} 
                        className="p-1 hover:bg-red-500/20 rounded-lg group-hover/skill:text-red-500 transition-colors"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </motion.span>
                  ))}
                </AnimatePresence>
                {profile.extra_skills.length === 0 && (
                  <div className="w-full flex flex-col items-center justify-center py-4 text-center">
                    <Zap className="w-8 h-8 text-slate-700 mb-2" />
                    <p className="text-slate-600 font-black uppercase tracking-widest text-[9px]">Awaiting Manual Skill Injection</p>
                  </div>
                )}
              </div>
              
              <div className="flex gap-3">
                <input 
                  type="text" 
                  value={skillInput} 
                  onChange={(e) => setSkillInput(e.target.value)} 
                  onKeyPress={(e) => e.key === 'Enter' && addSkill()} 
                  className="flex-1 bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-[#6C3FC8] outline-none transition-all placeholder:text-slate-700" 
                  placeholder="Inject specialized skill..." 
                />
                <Button 
                  onClick={addSkill} 
                  className="bg-[#6C3FC8] hover:bg-[#6C3FC8]/90 rounded-2xl h-auto px-6 font-black uppercase tracking-tighter shadow-lg active:scale-95"
                >
                  <Plus className="w-5 h-5 mr-1" />
                </Button>
              </div>
            </motion.section>

            {/* Career Goals */}
            <motion.section variants={itemVariants} className="bg-[#1E293B] rounded-[2.5rem] border-l-4 border-l-yellow-400 border border-white/5 p-8 shadow-xl group">
              <h3 className="text-lg font-black text-white uppercase tracking-widest mb-10 flex items-center gap-4">
                <div className="p-3 bg-yellow-400/10 rounded-2xl border border-yellow-400/20 group-hover:rotate-12 transition-transform">
                  <Target className="w-6 h-6 text-yellow-400" />
                </div>
                Target Sector / Goals
              </h3>
              
              <div className="space-y-8">
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">Strategic Objective</label>
                    <input 
                      type="text" 
                      value={profile.career_goal} 
                      onChange={(e) => setProfile({ ...profile, career_goal: e.target.value })} 
                      className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-yellow-400 outline-none transition-all placeholder:text-slate-700" 
                      placeholder="e.g. Senior Backend Architect" 
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">Geographical Focus</label>
                    <input 
                      type="text" 
                      value={profile.preferred_location} 
                      onChange={(e) => setProfile({ ...profile, preferred_location: e.target.value })} 
                      className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-yellow-400 outline-none transition-all placeholder:text-slate-700" 
                      placeholder="e.g. SF, Remote, London" 
                    />
                  </div>
                </div>

                <div>
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-4 block ml-1">Engagement Priority</label>
                  <div className="flex flex-wrap gap-2 mb-6">
                    {profile.target_companies.map((company, i) => (
                      <span key={i} className="px-4 py-2 bg-yellow-400/10 text-yellow-500 border border-yellow-400/20 rounded-2xl flex items-center gap-2 text-[10px] font-black uppercase tracking-widest group/company transition-all hover:bg-yellow-400/20">
                        <Star className="w-3 h-3 fill-current" />
                        {company}
                        <button 
                          onClick={() => setProfile({ ...profile, target_companies: profile.target_companies.filter((_, idx) => idx !== i) })} 
                          className="p-1 hover:text-red-500 transition-colors"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-3">
                    <input 
                      type="text" 
                      value={companyInput} 
                      onChange={(e) => setCompanyInput(e.target.value)} 
                      onKeyPress={(e) => e.key === 'Enter' && addCompany()} 
                      className="flex-1 bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-yellow-400 outline-none transition-all placeholder:text-slate-700" 
                      placeholder="Add Target Entity..." 
                    />
                    <Button 
                      onClick={addCompany} 
                      className="bg-yellow-400 hover:bg-yellow-500 rounded-2xl h-auto px-6 text-[#0F172A] font-black uppercase tracking-tighter shadow-lg"
                    >
                      <Plus className="w-5 h-5" />
                    </Button>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* Section: External Sync */}
            <motion.section variants={itemVariants} className="bg-[#1E293B] rounded-[2.5rem] border-l-4 border-l-blue-400 border border-white/5 p-8 shadow-xl group">
              <h3 className="text-lg font-black text-white uppercase tracking-widest mb-10 flex items-center gap-4">
                <div className="p-3 bg-blue-500/10 rounded-2xl border border-blue-500/20 group-hover:rotate-12 transition-transform">
                  <LinkIcon className="w-6 h-6 text-blue-400" />
                </div>
                External Matrix Sync
              </h3>
              
              <div className="space-y-8">
                <div className="flex items-center gap-6 p-6 bg-[#0F172A]/40 rounded-3xl border border-white/5 hover:border-blue-500/20 transition-all">
                   <div className="w-16 h-16 bg-[#1E293B] rounded-2xl flex items-center justify-center border border-white/5 shadow-inner">
                      <Github className="w-8 h-8 text-slate-400" />
                   </div>
                   <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[11px] font-black uppercase tracking-[0.2em] text-white">GitHub Terminal</span>
                        <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full border ${githubConnected ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                           <div className={`w-2 h-2 rounded-full ${githubConnected ? 'bg-green-500 shadow-[0_0_8px_#22c55e]' : 'bg-red-500'}`} />
                           <span className="text-[9px] font-black uppercase">{githubConnected ? 'Authenticated' : 'Not Linked'}</span>
                        </div>
                      </div>
                      <p className="text-[10px] font-bold text-slate-500 leading-relaxed uppercase tracking-tighter">Sync your repository commit history and specialized project metadata from your verified terminal.</p>
                   </div>
                </div>

                <div className="flex items-center gap-6 p-6 bg-[#0F172A]/40 rounded-3xl border border-white/5 hover:border-yellow-400/20 transition-all">
                   <div className="w-16 h-16 bg-[#1E293B] rounded-2xl flex items-center justify-center border border-white/5 shadow-inner">
                      <Brain className="w-8 h-8 text-yellow-400" />
                   </div>
                   <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[11px] font-black uppercase tracking-[0.2em] text-white">LeetCode Sync</span>
                        <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full border ${leetcodeConnected ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                           <div className={`w-2 h-2 rounded-full ${leetcodeConnected ? 'bg-green-500 shadow-[0_0_8px_#22c55e]' : 'bg-red-500'}`} />
                           <span className="text-[9px] font-black uppercase">{leetcodeConnected ? 'Authenticated' : 'Not Linked'}</span>
                        </div>
                      </div>
                      <p className="text-[10px] font-bold text-slate-500 leading-relaxed uppercase tracking-tighter">Operational metrics for algorithmic complexity and daily solve consistency synchronized via global API.</p>
                   </div>
                </div>
              </div>
            </motion.section>
          </div>

          <motion.div variants={itemVariants} className="mt-12 flex flex-col items-center gap-8 pb-20 pt-16 border-t border-white/5">
            <Button 
               onClick={handleSave} 
               disabled={saving} 
               className="bg-gradient-to-r from-[#6C3FC8] to-purple-600 hover:scale-105 active:scale-95 text-white font-black uppercase tracking-[0.2em] text-xl px-20 py-10 rounded-[2.5rem] shadow-[0_20px_50px_-15px_rgba(108,63,200,0.5)] transition-all group"
            >
              {saving ? (
                <Loader2 className="w-6 h-6 animate-spin" />
              ) : (
                <div className="flex items-center gap-3">
                  <Save className="w-6 h-6 group-hover:rotate-12 transition-transform" /> 
                  Initiate Save Protocol
                </div>
              )}
            </Button>
            
            <div className="flex gap-4">
              <Link href="/dashboard">
                <Button variant="ghost" className="text-slate-500 hover:text-white font-black uppercase tracking-widest text-xs px-8 h-12 rounded-2xl">
                  Abort
                </Button>
              </Link>
              <Link href="/analysis">
                 <Button variant="outline" className="border-white/10 text-slate-400 hover:text-purple-400 px-10 rounded-2xl h-14 font-black uppercase tracking-widest text-xs shadow-lg transition-all">
                    System Analysis <ChevronRight className="ml-2 w-4 h-4" />
                 </Button>
              </Link>
            </div>
          </motion.div>
        </motion.div>
      </main>

      {/* Decorative Layer */}
      <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden opacity-30">
        <div className="absolute top-[10%] left-[-5%] w-[600px] h-[600px] bg-[#6C3FC8]/10 rounded-full blur-[150px]" />
        <div className="absolute bottom-[-10%] right-[-5%] w-[500px] h-[500px] bg-yellow-400/5 rounded-full blur-[120px]" />
        <div className="absolute top-[50%] right-[30%] w-[300px] h-[300px] bg-blue-500/5 rounded-full blur-[100px]" />
      </div>

      <style jsx global>{`
        @keyframes slide {
          from { background-position: 0 0; }
          to { background-position: 40px 40px; }
        }
      `}</style>
    </div>
  )
}
