'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import Navbar from '@/components/Navbar'
import {
  Brain, Loader2, Save, Plus, X, CheckCircle,
  AlertCircle, GraduationCap, Code, Briefcase,
  Target, User, Github, Globe, Link as LinkIcon,
  Sparkles, Zap, ChevronRight, Star
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useProfile } from './hooks/useProfile'

export default function ProfilePage() {
  const {
    user,
    profile,
    loading,
    saving,
    saved,
    error,
    completeness,
    resumeUploaded,
    isStudent,
    isProfessional,
    updateField,
    addTag,
    removeTag,
    saveProfile,
  } = useProfile()

  // Local input states — UI only, not business logic
  const [skillInput, setSkillInput]   = useState('')
  const [companyInput, setCompanyInput] = useState('')
  const [techInput, setTechInput]     = useState('')

  // ── Loading ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex items-center justify-center text-white">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-[#6C3FC8] mx-auto mb-4" />
          <p className="text-slate-400 font-black uppercase tracking-widest text-[10px]">
            Syncing Performance Protocol...
          </p>
        </div>
      </div>
    )
  }

  const userInitial = user?.email?.charAt(0).toUpperCase() || 'U'

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.1, delayChildren: 0.1 } }
  }
  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  }

  return (
    <div className="min-h-screen bg-[#0F172A] text-white selection:bg-purple-500/30">
      <Navbar />
      <main className="max-w-5xl mx-auto px-4 py-12">
        <motion.div initial="hidden" animate="visible" variants={containerVariants}>

          {/* ── Header + Completeness ─────────────────────────────────────────── */}
          <motion.div
            variants={itemVariants}
            className="bg-[#1E293B] rounded-[2.5rem] p-8 md:p-10 mb-8 border border-white/5 relative overflow-hidden group shadow-2xl"
          >
            <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-purple-500/5 to-transparent pointer-events-none" />

            <div className="flex flex-col md:flex-row items-center gap-8 relative z-10">
              <div className="relative">
                <div className="w-24 h-24 rounded-full bg-gradient-to-br from-[#6C3FC8] to-purple-400 flex items-center justify-center text-4xl font-black shadow-[0_0_40px_rgba(108,63,200,0.5)] border-4 border-white/10 relative z-10">
                  {userInitial}
                </div>
                <div className="absolute inset-0 bg-[#6C3FC8]/20 blur-2xl rounded-full" />
              </div>

              <div className="flex-1 w-full text-center md:text-left">
                <div className="flex items-center justify-center md:justify-between mb-4">
                  <div>
                    <h1 className="text-3xl font-black tracking-tighter uppercase mb-1">
                      Intelligence <span className="text-purple-400 text-sm tracking-widest ml-1 italic">Profile</span>
                    </h1>
                    <p className="text-slate-500 text-[10px] font-black uppercase tracking-[0.2em]">
                      {user?.email}
                    </p>
                  </div>
                  <div className="hidden md:block text-right">
                    <span className="text-3xl font-black text-yellow-400 drop-shadow-[0_0_10px_rgba(250,204,21,0.3)]">
                      {completeness}%
                    </span>
                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
                      Calibration Level
                    </p>
                  </div>
                </div>

                <div className="h-3 bg-[#0F172A] rounded-full overflow-hidden border border-white/5 p-0.5 mb-6">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${completeness}%` }}
                    transition={{ duration: 1.5, ease: 'circOut' }}
                    className="h-full bg-gradient-to-r from-[#6C3FC8] via-purple-400 to-yellow-400 rounded-full"
                  />
                </div>

                <div className="flex flex-wrap justify-center md:justify-start gap-4 text-[9px] font-black uppercase tracking-[0.2em]">
                  {[
                    { label: 'GitHub',    ok: !!profile.github_username },
                    { label: 'LeetCode',  ok: !!profile.leetcode_username },
                    { label: 'Resume',    ok: resumeUploaded },
                    { label: 'Academic',  ok: !!(profile.college_name && profile.degree) },
                    { label: 'Skills',    ok: profile.extra_skills.length >= 3 },
                    { label: 'Goals',     ok: !!profile.career_goal },
                    { label: 'LinkedIn',  ok: !!profile.linkedin_url },
                  ].map(task => (
                    <div
                      key={task.label}
                      className={`flex items-center gap-1.5 ${task.ok ? 'text-green-400' : 'text-slate-600'}`}
                    >
                      <div className={`w-1.5 h-1.5 rounded-full ${task.ok ? 'bg-green-500 shadow-[0_0_5px_#22c55e]' : 'bg-slate-700'}`} />
                      {task.label}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>

          {/* ── Success banner ────────────────────────────────────────────────── */}
          <AnimatePresence>
            {saved && (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mb-8 p-4 bg-green-500/10 border border-green-500/20 rounded-2xl flex items-center justify-center gap-3"
              >
                <CheckCircle className="w-5 h-5 text-green-400" />
                <p className="text-green-400 font-black uppercase tracking-widest text-xs">
                  Neural Profile Synchronized Successfully
                </p>
              </motion.div>
            )}
          </AnimatePresence>

          {/* ── Error banner ──────────────────────────────────────────────────── */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mb-8 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center justify-center gap-3"
              >
                <AlertCircle className="w-5 h-5 text-red-400" />
                <p className="text-red-400 font-black uppercase tracking-widest text-xs">{error}</p>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="grid lg:grid-cols-2 gap-8 mb-12">

            {/* ── Section 1: Career Goal ───────────────────────────────────────── */}
            <motion.section
              variants={itemVariants}
              className="bg-[#1E293B] rounded-[2.5rem] border-l-4 border-l-yellow-400 border border-white/5 p-8 shadow-xl group"
            >
              <h3 className="text-lg font-black text-white uppercase tracking-widest mb-8 flex items-center gap-4">
                <div className="p-3 bg-yellow-400/10 rounded-2xl border border-yellow-400/20 group-hover:rotate-12 transition-transform">
                  <Target className="w-6 h-6 text-yellow-400" />
                </div>
                Career Target
              </h3>

              <div className="space-y-5">
                <div>
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">
                    Career Goal
                  </label>
                  <input
                    type="text"
                    value={profile.career_goal}
                    onChange={e => updateField('career_goal', e.target.value)}
                    className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-yellow-400 outline-none transition-all placeholder:text-slate-700"
                    placeholder="e.g. Full Stack Developer"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">
                      Work Type
                    </label>
                    <select
                      value={profile.preferred_work_type}
                      onChange={e => updateField('preferred_work_type', e.target.value)}
                      className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-yellow-400 outline-none appearance-none cursor-pointer"
                      aria-label="Preferred work type"
                    >
                      <option value="">Select</option>
                      <option value="Remote">Remote</option>
                      <option value="Hybrid">Hybrid</option>
                      <option value="On-site">On-site</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">
                      Timeline
                    </label>
                    <select
                      value={profile.job_search_timeline}
                      onChange={e => updateField('job_search_timeline', e.target.value)}
                      className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-yellow-400 outline-none appearance-none cursor-pointer"
                      aria-label="Job search timeline"
                    >
                      <option value="">Select</option>
                      <option value="Immediately">Immediately</option>
                      <option value="1-3 months">1–3 months</option>
                      <option value="3-6 months">3–6 months</option>
                      <option value="6+ months">6+ months</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-3 block ml-1">
                    Target Companies
                  </label>
                  <div className="flex flex-wrap gap-2 mb-3 min-h-[40px]">
                    <AnimatePresence>
                      {profile.target_companies.map((c, i) => (
                        <motion.span
                          key={i}
                          initial={{ scale: 0.8, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          exit={{ scale: 0.8, opacity: 0 }}
                          className="px-3 py-1.5 bg-yellow-400/10 text-yellow-400 border border-yellow-400/20 rounded-xl flex items-center gap-2 text-[10px] font-black uppercase tracking-widest"
                        >
                          <Star className="w-3 h-3 fill-current" />
                          {c}
                          <button onClick={() => removeTag('target_companies', i)} aria-label="Remove company">
                            <X className="w-3 h-3 hover:text-red-400 transition-colors" />
                          </button>
                        </motion.span>
                      ))}
                    </AnimatePresence>
                  </div>
                  <div className="flex gap-3">
                    <input
                      type="text"
                      value={companyInput}
                      onChange={e => setCompanyInput(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') { addTag('target_companies', companyInput); setCompanyInput('') } }}
                      className="flex-1 bg-[#0F172A]/50 border border-white/10 rounded-2xl p-3 text-sm font-bold focus:ring-2 focus:ring-yellow-400 outline-none placeholder:text-slate-700"
                      placeholder="Add company..."
                    />
                    <Button
                      onClick={() => { addTag('target_companies', companyInput); setCompanyInput('') }}
                      className="bg-yellow-400 hover:bg-yellow-500 rounded-2xl h-auto px-5 text-[#0F172A] font-black"
                    >
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </motion.section>

            {/* ── Section 2: Academic (student / fresher) ──────────────────────── */}
            {isStudent && (
              <motion.section
                variants={itemVariants}
                className="bg-[#1E293B] rounded-[2.5rem] border-l-4 border-l-purple-500 border border-white/5 p-8 shadow-xl group"
              >
                <h3 className="text-lg font-black text-white uppercase tracking-widest mb-8 flex items-center gap-4">
                  <div className="p-3 bg-purple-500/10 rounded-2xl border border-purple-500/20 group-hover:rotate-12 transition-transform">
                    <GraduationCap className="w-6 h-6 text-[#6C3FC8]" />
                  </div>
                  Academic Info
                </h3>
                <div className="space-y-5">
                  <div>
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">
                      College / Institute
                    </label>
                    <input
                      type="text"
                      value={profile.college_name}
                      onChange={e => updateField('college_name', e.target.value)}
                      className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-[#6C3FC8] outline-none placeholder:text-slate-700"
                      placeholder="Institute name"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">
                        Degree
                      </label>
                      <select
                        value={profile.degree}
                        onChange={e => updateField('degree', e.target.value)}
                        className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-[#6C3FC8] outline-none appearance-none cursor-pointer"
                        aria-label="Select degree"
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
                      <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">
                        Branch
                      </label>
                      <select
                        value={profile.branch}
                        onChange={e => updateField('branch', e.target.value)}
                        className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-[#6C3FC8] outline-none appearance-none cursor-pointer"
                        aria-label="Select branch"
                      >
                        <option value="">Select</option>
                        <option value="CSE">CSE</option>
                        <option value="IT">IT</option>
                        <option value="ECE">ECE</option>
                        <option value="EEE">EEE</option>
                        <option value="Mechanical">Mechanical</option>
                        <option value="Civil">Civil</option>
                        <option value="Other">Other</option>
                      </select>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">
                        Year
                      </label>
                      <select
                        value={profile.year_of_study}
                        onChange={e => updateField('year_of_study', e.target.value)}
                        className="w-full bg-[#0F172A]/50 border border-white/10 rounded-xl p-3 text-xs font-bold focus:ring-2 focus:ring-[#6C3FC8] outline-none appearance-none"
                        aria-label="Year of study"
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
                      <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">
                        Grad Year
                      </label>
                      <input
                        type="number"
                        value={profile.graduation_year || ''}
                        onChange={e => updateField('graduation_year', parseInt(e.target.value) || 0)}
                        className="w-full bg-[#0F172A]/50 border border-white/10 rounded-xl p-3 text-xs font-bold outline-none placeholder:text-slate-700"
                        placeholder="2026"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">
                        CGPA
                      </label>
                      <input
                        type="text"
                        value={profile.cgpa}
                        onChange={e => updateField('cgpa', e.target.value)}
                        className="w-full bg-[#0F172A]/50 border border-white/10 rounded-xl p-3 text-xs font-bold outline-none placeholder:text-slate-700"
                        placeholder="8.5"
                      />
                    </div>
                  </div>
                </div>
              </motion.section>
            )}

            {/* ── Section 3: Professional (professional / career_switch) ────────── */}
            {isProfessional && (
              <motion.section
                variants={itemVariants}
                className="bg-[#1E293B] rounded-[2.5rem] border-l-4 border-l-blue-400 border border-white/5 p-8 shadow-xl group"
              >
                <h3 className="text-lg font-black text-white uppercase tracking-widest mb-8 flex items-center gap-4">
                  <div className="p-3 bg-blue-500/10 rounded-2xl border border-blue-500/20 group-hover:rotate-12 transition-transform">
                    <Briefcase className="w-6 h-6 text-blue-400" />
                  </div>
                  Professional Info
                </h3>
                <div className="space-y-5">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">
                        Job Title
                      </label>
                      <input
                        type="text"
                        value={profile.current_job_title}
                        onChange={e => updateField('current_job_title', e.target.value)}
                        className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-blue-400 outline-none placeholder:text-slate-700"
                        placeholder="e.g. SDE-2"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">
                        Company
                      </label>
                      <input
                        type="text"
                        value={profile.current_company}
                        onChange={e => updateField('current_company', e.target.value)}
                        className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-blue-400 outline-none placeholder:text-slate-700"
                        placeholder="e.g. Infosys"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1">
                      Years of Experience
                    </label>
                    <input
                      type="number"
                      value={profile.years_of_experience || ''}
                      onChange={e => updateField('years_of_experience', parseInt(e.target.value) || 0)}
                      className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-blue-400 outline-none placeholder:text-slate-700"
                      placeholder="e.g. 3"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-3 block ml-1">
                      Current Tech Stack
                    </label>
                    <div className="flex flex-wrap gap-2 mb-3 min-h-[40px]">
                      <AnimatePresence>
                        {profile.current_tech_stack.map((t, i) => (
                          <motion.span
                            key={i}
                            initial={{ scale: 0.8, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.8, opacity: 0 }}
                            className="px-3 py-1.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-xl flex items-center gap-2 text-[10px] font-black uppercase"
                          >
                            {t}
                            <button onClick={() => removeTag('current_tech_stack', i)} aria-label="Remove tech">
                              <X className="w-3 h-3 hover:text-red-400 transition-colors" />
                            </button>
                          </motion.span>
                        ))}
                      </AnimatePresence>
                    </div>
                    <div className="flex gap-3">
                      <input
                        type="text"
                        value={techInput}
                        onChange={e => setTechInput(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') { addTag('current_tech_stack', techInput); setTechInput('') } }}
                        className="flex-1 bg-[#0F172A]/50 border border-white/10 rounded-2xl p-3 text-sm font-bold focus:ring-2 focus:ring-blue-400 outline-none placeholder:text-slate-700"
                        placeholder="Add technology..."
                      />
                      <Button
                        onClick={() => { addTag('current_tech_stack', techInput); setTechInput('') }}
                        className="bg-blue-500 hover:bg-blue-600 rounded-2xl h-auto px-5 font-black"
                      >
                        <Plus className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </motion.section>
            )}

            {/* ── Section 4: Skills ────────────────────────────────────────────── */}
            <motion.section
              variants={itemVariants}
              className="bg-[#1E293B] rounded-[2.5rem] border-l-4 border-l-purple-500 border border-white/5 p-8 shadow-xl group"
            >
              <h3 className="text-lg font-black text-white uppercase tracking-widest mb-8 flex items-center gap-4">
                <div className="p-3 bg-purple-500/10 rounded-2xl border border-purple-500/20 group-hover:rotate-12 transition-transform">
                  <Code className="w-6 h-6 text-[#6C3FC8]" />
                </div>
                Core Skills
              </h3>

              <div className="flex flex-wrap gap-2 mb-6 min-h-[120px] items-start p-5 bg-[#0F172A]/30 rounded-3xl border border-white/5">
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
                        onClick={() => removeTag('extra_skills', i)}
                        className="p-1 hover:bg-red-500/20 rounded-lg group-hover/skill:text-red-500 transition-colors"
                        aria-label="Remove skill"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </motion.span>
                  ))}
                </AnimatePresence>
                {profile.extra_skills.length === 0 && (
                  <div className="w-full flex flex-col items-center justify-center py-4 text-center">
                    <Zap className="w-8 h-8 text-slate-700 mb-2" />
                    <p className="text-slate-600 font-black uppercase tracking-widest text-[9px]">
                      No skills added yet
                    </p>
                  </div>
                )}
              </div>

              <div className="flex gap-3">
                <input
                  type="text"
                  value={skillInput}
                  onChange={e => setSkillInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') { addTag('extra_skills', skillInput); setSkillInput('') } }}
                  className="flex-1 bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-[#6C3FC8] outline-none transition-all placeholder:text-slate-700"
                  placeholder="Add a skill..."
                />
                <Button
                  onClick={() => { addTag('extra_skills', skillInput); setSkillInput('') }}
                  className="bg-[#6C3FC8] hover:bg-[#6C3FC8]/90 rounded-2xl h-auto px-6 font-black shadow-lg active:scale-95"
                >
                  <Plus className="w-5 h-5" />
                </Button>
              </div>
            </motion.section>

            {/* ── Section 5: External Links (editable) ─────────────────────────── */}
            <motion.section
              variants={itemVariants}
              className="bg-[#1E293B] rounded-[2.5rem] border-l-4 border-l-green-400 border border-white/5 p-8 shadow-xl group"
            >
              <h3 className="text-lg font-black text-white uppercase tracking-widest mb-8 flex items-center gap-4">
                <div className="p-3 bg-green-500/10 rounded-2xl border border-green-500/20 group-hover:rotate-12 transition-transform">
                  <LinkIcon className="w-6 h-6 text-green-400" />
                </div>
                External Links
              </h3>

              <div className="space-y-5">
                <div>
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1 flex items-center gap-2">
                    <Github className="w-3 h-3" /> GitHub Username
                  </label>
                  <input
                    type="text"
                    value={profile.github_username}
                    onChange={e => updateField('github_username', e.target.value)}
                    className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-green-400 outline-none placeholder:text-slate-700"
                    placeholder="your-github-username"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1 flex items-center gap-2">
                    <Brain className="w-3 h-3 text-yellow-400" /> LeetCode Username
                  </label>
                  <input
                    type="text"
                    value={profile.leetcode_username}
                    onChange={e => updateField('leetcode_username', e.target.value)}
                    className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-green-400 outline-none placeholder:text-slate-700"
                    placeholder="your-leetcode-username"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2 block ml-1 flex items-center gap-2">
                    <Globe className="w-3 h-3 text-blue-400" /> LinkedIn URL
                  </label>
                  <input
                    type="text"
                    value={profile.linkedin_url}
                    onChange={e => updateField('linkedin_url', e.target.value)}
                    className="w-full bg-[#0F172A]/50 border border-white/10 rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-green-400 outline-none placeholder:text-slate-700"
                    placeholder="https://linkedin.com/in/yourname"
                  />
                </div>
              </div>
            </motion.section>

          </div>

          {/* ── Save button ───────────────────────────────────────────────────── */}
          <motion.div
            variants={itemVariants}
            className="mt-12 flex flex-col items-center gap-8 pb-20 pt-16 border-t border-white/5"
          >
            <Button
              onClick={saveProfile}
              disabled={saving}
              className="bg-gradient-to-r from-[#6C3FC8] to-purple-600 hover:scale-105 active:scale-95 text-white font-black uppercase tracking-[0.2em] text-xl px-20 py-10 rounded-[2.5rem] shadow-[0_20px_50px_-15px_rgba(108,63,200,0.5)] transition-all group"
            >
              {saving ? (
                <Loader2 className="w-6 h-6 animate-spin" />
              ) : (
                <div className="flex items-center gap-3">
                  <Save className="w-6 h-6 group-hover:rotate-12 transition-transform" />
                  Save Profile
                </div>
              )}
            </Button>

            <div className="flex gap-4">
              <Link href="/dashboard">
                <Button variant="ghost" className="text-slate-500 hover:text-white font-black uppercase tracking-widest text-xs px-8 h-12 rounded-2xl">
                  Back to Dashboard
                </Button>
              </Link>
              <Link href="/analysis">
                <Button variant="outline" className="border-white/10 text-slate-400 hover:text-purple-400 px-10 rounded-2xl h-14 font-black uppercase tracking-widest text-xs shadow-lg transition-all">
                  Run Analysis <ChevronRight className="ml-2 w-4 h-4" />
                </Button>
              </Link>
            </div>
          </motion.div>

        </motion.div>
      </main>

      {/* ── Decorative orbs ─────────────────────────────────────────────────── */}
      <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden opacity-30">
        <div className="absolute top-[10%] left-[-5%] w-[600px] h-[600px] bg-[#6C3FC8]/10 rounded-full blur-[150px]" />
        <div className="absolute bottom-[-10%] right-[-5%] w-[500px] h-[500px] bg-yellow-400/5 rounded-full blur-[120px]" />
        <div className="absolute top-[50%] right-[30%] w-[300px] h-[300px] bg-blue-500/5 rounded-full blur-[100px]" />
      </div>
    </div>
  )
}