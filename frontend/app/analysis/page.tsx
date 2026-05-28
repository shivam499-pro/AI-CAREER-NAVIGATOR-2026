'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import Navbar from '@/components/Navbar'
import {
  Brain, Loader2, Sparkles, TrendingUp, Target, Code,
  CheckCircle, Calendar, ArrowRight, Award, Zap, AlertTriangle
} from 'lucide-react'

// Phase 3 — all logic lives in these three imports
import { useAnalysis } from './hooks/useAnalysis'
import { getBrandColor, getExperienceStyles } from './config/brandTokens'

// ─── Design helpers (UI only) ──────────────────────────────────────────────
const SectionHeader = ({
  icon: Icon, label, iconColor, meta,
}: {
  icon: React.ElementType
  label: string
  iconColor: string
  meta?: React.ReactNode
}) => (
  <div className="flex items-center gap-3 mb-5">
    <div className="w-7 h-7 rounded-lg bg-white/[0.04] border border-white/[0.07] flex items-center justify-center flex-shrink-0">
      <Icon className={`w-3.5 h-3.5 ${iconColor}`} />
    </div>
    <span className="text-sm font-semibold text-slate-300 tracking-wide">{label}</span>
    {meta && <span className="text-xs text-slate-600">{meta}</span>}
    <div className="flex-1 h-px bg-slate-800" />
  </div>
)

// ─── Component — logic-less, pure renderer ────────────────────────────────
export default function AnalysisPage() {
  const {
    loading, analyzing, analysis, selectedPath, pathDetails,
    roadmapProgress, error, milestoneError, user,
    setSelectedPath, runAnalysis, updateMilestone,
  } = useAnalysis()

  // ── Loading screens ───────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-[#0B1120] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary-violet mx-auto mb-3" />
          <p className="text-sm text-slate-500">Loading analysis…</p>
        </div>
      </div>
    )
  }

  if (analyzing) {
    return (
      <div className="min-h-screen bg-[#0B1120] flex items-center justify-center">
        <div className="text-center max-w-sm p-8">
          <div className="relative w-20 h-20 mx-auto mb-8">
            <div className="absolute inset-0 rounded-full border-2 border-primary-violet/15" />
            <div className="absolute inset-0 rounded-full border-2 border-primary-violet border-t-transparent animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center">
              <Brain className="w-8 h-8 text-primary-violet" />
            </div>
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">Syncing Intelligence</h2>
          <p className="text-sm text-slate-500 mb-7">Reading GitHub and LeetCode activity…</p>
          <div className="space-y-3 text-left">
            {['Fetching GitHub repos', 'Parsing LeetCode solutions', 'Generating career paths'].map((step, i) => (
              <div key={i} className="flex items-center gap-3 text-sm text-slate-400">
                <CheckCircle className={`w-4 h-4 flex-shrink-0 ${i < 2 ? 'text-emerald-500' : 'text-slate-700'}`} />
                {step}
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="min-h-screen bg-[#0B1120] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary-violet mx-auto mb-3" />
          <p className="text-sm text-slate-500">Loading analysis…</p>
        </div>
      </div>
    )
  }

  const containerVariants = { hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.1 } } }
  const itemVariants = { hidden: { opacity: 0, y: 16 }, visible: { opacity: 1, y: 0 } }

  const activeRoadmap = pathDetails[selectedPath]?.roadmap || analysis.roadmap
  const activeGaps = pathDetails[selectedPath]?.skill_gaps || analysis.skill_gaps || []
  const completedCount = Object.values(roadmapProgress).filter(s => s === 'completed').length
  const totalMilestones = activeRoadmap?.milestones?.length || 1

  return (
    <div className="min-h-screen bg-[#0B1120] text-white">
      <Navbar />
      <main className="container mx-auto px-4 py-10 max-w-6xl">
        <motion.div variants={containerVariants} initial="hidden" animate="visible" className="space-y-7">

          {/* ── 1. HERO ─────────────────────────────────────────────────── */}
          <motion.div variants={itemVariants}>
            <div className="bg-[#111827] rounded-2xl border border-slate-800 p-7 flex flex-col sm:flex-row items-center gap-5">
              <div className="flex-shrink-0 w-14 h-14 rounded-xl bg-primary-violet/10 border border-primary-violet/20 flex items-center justify-center">
                <Award className="w-7 h-7 text-primary-violet" />
              </div>
              <div className="flex-1 text-center sm:text-left">
                <div className="flex items-center justify-center sm:justify-start gap-1.5 mb-1">
                  <Sparkles className="w-3 h-3 text-primary-violet" />
                  <span className="text-[11px] font-semibold uppercase tracking-widest text-primary-violet">AI Analysis</span>
                </div>
                <h2 className="text-2xl font-bold text-white leading-tight">{analysis.experience_level}</h2>
                <p className="text-xs text-slate-500 mt-0.5">AI-estimated from your real GitHub & LeetCode activity</p>
              </div>
              <div className="flex items-center gap-3 flex-shrink-0">
                <span className={`px-3 py-1.5 rounded-lg border text-xs font-semibold ${getExperienceStyles(analysis.experience_level)}`}>
                  {analysis.experience_level}
                </span>
                <button
                  onClick={() => user && runAnalysis(user.id)}
                  disabled={analyzing}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-slate-600 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition-all disabled:opacity-40"
                >
                  <Zap className="w-3 h-3" />
                  Re-analyse
                </button>
              </div>
            </div>
          </motion.div>

          {/* ── 2. RESUME SCORE ──────────────────────────────────────────── */}
          {analysis.resume_score && (
            <motion.div variants={itemVariants}>
              <SectionHeader icon={Award} label="Resume Score" iconColor="text-amber-400" />
              <div className="bg-[#111827] rounded-2xl border border-slate-800 p-7">
                <div className="flex flex-col md:flex-row items-center gap-8">
                  <div className="relative flex-shrink-0 w-28 h-28">
                    <svg className="w-28 h-28 -rotate-90" viewBox="0 0 120 120">
                      <circle cx="60" cy="60" r="50" fill="none" stroke="#1E293B" strokeWidth="10" />
                      <circle cx="60" cy="60" r="50" fill="none" stroke="#6C3FC8" strokeWidth="10"
                        strokeDasharray={`${(analysis.resume_score.overall / 100) * 314} 314`}
                        strokeLinecap="round" />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-3xl font-bold text-white">{analysis.resume_score.overall}</span>
                      <span className="text-[10px] text-slate-500 font-medium">/100</span>
                    </div>
                  </div>
                  <div className="flex-1 w-full">
                    <p className="text-sm text-slate-400 leading-relaxed mb-5 pl-3 border-l-2 border-primary-violet/30 italic">
                      "{analysis.resume_score.summary}"
                    </p>
                    <div className="space-y-3">
                      {Object.entries(analysis.resume_score.breakdown || {}).map(([key, val]) => {
                        const v = val as number
                        const barClr = v >= 80 ? '#22C55E' : v >= 60 ? '#6C3FC8' : v >= 40 ? '#F59E0B' : '#EF4444'
                        return (
                          <div key={key} className="flex items-center gap-3">
                            <span className="text-xs text-slate-500 w-32 flex-shrink-0 capitalize">{key.replace(/_/g, ' ')}</span>
                            <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                              <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${v}%`, background: barClr }} />
                            </div>
                            <span className="text-xs font-semibold text-white w-6 text-right">{v}</span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* ── 3. SALARY INSIGHTS ───────────────────────────────────────── */}
          {analysis.salary_insights && (
            <motion.div variants={itemVariants}>
              <SectionHeader icon={TrendingUp} label="Salary Insights" iconColor="text-emerald-400" />
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'Entry Level', value: analysis.salary_insights.entry_level, textClr: 'text-sky-400', border: 'border-sky-500/20', bg: 'bg-sky-500/5' },
                  { label: 'Mid Level', value: analysis.salary_insights.mid_level, textClr: 'text-primary-violet', border: 'border-primary-violet/20', bg: 'bg-primary-violet/5' },
                  { label: 'Senior', value: analysis.salary_insights.senior_level, textClr: 'text-amber-400', border: 'border-amber-500/20', bg: 'bg-amber-500/5' },
                ].map(item => (
                  <div key={item.label} className={`rounded-xl border ${item.border} ${item.bg} p-5`}>
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2">{item.label}</p>
                    <p className={`text-xl font-bold ${item.textClr}`}>{item.value}</p>
                  </div>
                ))}
              </div>
              <p className="text-[11px] text-slate-600 mt-2.5 px-1">{analysis.salary_insights.note}</p>
            </motion.div>
          )}

          {/* ── 4. TOP COMPANIES ─────────────────────────────────────────── */}
          {analysis.top_companies && analysis.top_companies.length > 0 && (
            <motion.div variants={itemVariants}>
              <SectionHeader icon={Sparkles} label="Top Companies For You" iconColor="text-sky-400" />
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {analysis.top_companies.map((company, i) => {
                  const clr = getBrandColor(company.name)
                  return (
                    <div key={i} className="bg-[#111827] rounded-xl border border-slate-800 hover:border-slate-700 p-4 flex items-start gap-3 transition-all">
                      <div className="w-9 h-9 rounded-lg flex items-center justify-center font-bold text-sm flex-shrink-0"
                        style={{ background: `${clr}18`, color: clr, border: `1px solid ${clr}30` }}>
                        {company.name[0]}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span className="text-sm font-semibold text-white">{company.name}</span>
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-500 uppercase tracking-wide border border-slate-700">{company.type}</span>
                        </div>
                        <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">{company.why}</p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </motion.div>
          )}

          {/* ── 5. CERTIFICATIONS ────────────────────────────────────────── */}
          {analysis.certifications && analysis.certifications.length > 0 && (
            <motion.div variants={itemVariants}>
              <SectionHeader icon={CheckCircle} label="Recommended Certifications" iconColor="text-emerald-400" />
              <div className="grid sm:grid-cols-2 gap-3">
                {analysis.certifications.map((cert, i) => (
                  <a key={i} href={cert.url} target="_blank" rel="noopener noreferrer"
                    className="bg-[#111827] rounded-xl border border-slate-800 hover:border-primary-violet/30 p-5 group block transition-all">
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-white group-hover:text-primary-violet transition-colors leading-snug">{cert.name}</p>
                        <p className="text-xs text-slate-500 mt-0.5">{cert.provider}</p>
                      </div>
                      <span className={`text-[9px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full flex-shrink-0 ${cert.relevance === 'High' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'}`}>
                        {cert.relevance}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 leading-relaxed">{cert.why}</p>
                  </a>
                ))}
              </div>
            </motion.div>
          )}

          {/* ── 6. STRENGTHS ─────────────────────────────────────────────── */}
          <motion.div variants={itemVariants}>
            <SectionHeader icon={Zap} label="Core Technical Strengths" iconColor="text-emerald-400" />
            <div className="space-y-2">
              {(analysis.strengths || []).map((strength, i) => (
                <div key={i} className="flex items-start gap-3.5 px-4 py-3.5 bg-[#111827] border border-slate-800 hover:border-slate-700 rounded-xl transition-all">
                  <span className="w-5 h-5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                    {i + 1}
                  </span>
                  <p className="text-sm text-slate-300 leading-relaxed">{strength}</p>
                </div>
              ))}
            </div>
          </motion.div>

          {/* ── 7. CAREER PATHS ──────────────────────────────────────────── */}
          <motion.div variants={itemVariants}>
            <SectionHeader icon={Target} label="Strategic Career Paths" iconColor="text-primary-violet" />
            <div className="grid md:grid-cols-3 gap-4">
              {(analysis.career_paths || []).slice(0, 3).map((path, i) => {
                const name = path.name || path.career_name || path.title || 'Unknown'
                const match = path.match_percentage ?? path.match ?? path.percentage ?? 0
                const desc = path.reason || path.description || path.justification || ''
                const isActive = selectedPath === name || (i === 0 && !selectedPath)
                return (
                  <div key={i} onClick={() => setSelectedPath(name)}
                    className={`relative bg-[#111827] rounded-xl border p-6 cursor-pointer transition-all ${isActive ? 'border-primary-violet/40 bg-primary-violet/[0.04]' : 'border-slate-800 hover:border-slate-700'}`}>
                    {i === 0 && (
                      <span className="absolute -top-2.5 left-5 bg-primary-violet text-white text-[9px] font-bold px-3 py-0.5 rounded-full uppercase tracking-widest">
                        Best Match
                      </span>
                    )}
                    <h4 className="text-sm font-semibold text-white mb-3 leading-snug">{name}</h4>
                    <div className="flex items-baseline gap-1 mb-3">
                      <span className={`text-3xl font-bold ${isActive ? 'text-primary-violet' : 'text-white'}`}>{match}%</span>
                      <span className="text-[10px] text-slate-600 uppercase tracking-wide ml-1">match</span>
                    </div>
                    <div className="h-1.5 bg-slate-800 rounded-full mb-4 overflow-hidden">
                      <div className={`h-full rounded-full transition-all duration-1000 ${isActive ? 'bg-primary-violet' : 'bg-slate-700'}`} style={{ width: `${match}%` }} />
                    </div>
                    <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
                  </div>
                )
              })}
            </div>
          </motion.div>

          {/* ── 8. SKILL GAPS ────────────────────────────────────────────── */}
          <motion.div variants={itemVariants}>
            <SectionHeader icon={Code} label="Critical Skill Gaps" iconColor="text-sky-400"
              meta={selectedPath ? `— ${selectedPath}` : undefined} />
            <div className="bg-[#111827] rounded-xl border border-slate-800 overflow-hidden">
              {activeGaps.map((item: any, i: number) => {
                const name = item.skill || item.skill_name || item.name || 'Skill'
                const has = item.have ?? item.has ?? item.owned ?? false
                const p = item.priority ?? item.priority_level ?? item.level ?? 0
                return (
                  <div key={i} className="flex items-center justify-between px-5 py-3.5 border-b border-slate-800/60 last:border-0 hover:bg-white/[0.015] transition-colors">
                    <div className="flex items-center gap-3">
                      <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${has ? 'bg-emerald-500' : p === 1 ? 'bg-red-500' : 'bg-amber-400'}`} />
                      <span className="text-sm text-slate-200">{name}</span>
                    </div>
                    <span className={`text-[9px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full ${has ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : p === 1 ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-amber-400/10 text-amber-400 border border-amber-400/20'}`}>
                      {has ? 'Verified' : `Priority ${p}`}
                    </span>
                  </div>
                )
              })}
            </div>
          </motion.div>

          {/* ── 9. ROADMAP ───────────────────────────────────────────────── */}
          <motion.div variants={itemVariants} className="pb-8">
            <SectionHeader icon={Calendar} label={`${activeRoadmap?.duration_months || 6}-Month Growth Path`} iconColor="text-primary-violet" />
            <div className="bg-[#111827] rounded-2xl border border-slate-800 p-6">
              {activeRoadmap?.milestones?.length > 0 && (
                <div className="mb-6 pb-5 border-b border-slate-800">
                  <div className="flex justify-between mb-2">
                    <span className="text-xs text-slate-500">Overall progress</span>
                    <span className="text-xs font-semibold text-primary-violet">{completedCount} / {totalMilestones} completed</span>
                  </div>
                  <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-primary-violet rounded-full transition-all duration-500"
                      style={{ width: `${(completedCount / totalMilestones) * 100}%` }} />
                  </div>
                </div>
              )}
              {milestoneError && (
                <div className="mb-4 px-4 py-3 bg-amber-500/8 border border-amber-500/20 rounded-lg flex items-center gap-3">
                  <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                  <p className="text-xs text-amber-400">{milestoneError}</p>
                </div>
              )}
              <div className="space-y-2.5">
                {activeRoadmap?.milestones?.map((m: any, i: number) => {
                  const status = roadmapProgress[m.week] || 'pending'
                  const done = status === 'completed'
                  const inProg = status === 'in_progress'
                  return (
                    <div key={i}
                      className={`flex gap-4 p-4 rounded-xl border transition-all ${done ? 'bg-emerald-500/[0.04] border-emerald-500/15 opacity-65' : inProg ? 'bg-primary-violet/[0.04] border-primary-violet/20' : 'bg-slate-900/40 border-slate-800 hover:border-slate-700'}`}>
                      <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${done ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/25' : inProg ? 'bg-primary-violet/15 text-primary-violet border border-primary-violet/25' : 'bg-slate-800 text-slate-500 border border-slate-700'}`}>
                        {done ? '✓' : m.week}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2 mb-1.5">
                          <h4 className="text-sm font-semibold text-white leading-snug">{m.title}</h4>
                          <button onClick={() => updateMilestone(m.week, status)}
                            className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center transition-all hover:scale-105 ${done ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/25' : inProg ? 'bg-amber-400/15 text-amber-400 border border-amber-400/25' : 'bg-slate-800 text-slate-600 border border-slate-700 hover:text-slate-400'}`}>
                            {done ? (
                              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="20 6 9 17 4 12" />
                              </svg>
                            ) : (
                              <div className="w-2 h-2 rounded-full bg-current" />
                            )}
                          </button>
                        </div>
                        <p className="text-xs text-slate-500 leading-relaxed mb-2.5">{m.description}</p>
                        <div className="flex flex-wrap gap-1.5">
                          {m.skills?.map((s: string, si: number) => (
                            <span key={si} className="text-[10px] px-2 py-0.5 bg-primary-violet/10 text-primary-violet/80 border border-primary-violet/15 rounded-md">{s}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </motion.div>

          {/* ── 10. CTA ──────────────────────────────────────────────────── */}
          <motion.div variants={itemVariants} className="text-center pb-4">
            <div className="inline-block bg-gradient-to-b from-primary-violet/10 to-transparent rounded-2xl p-8">
              <Link href="/jobs">
                <Button className="bg-primary-violet hover:bg-primary-violet/90 text-white text-base font-semibold px-10 py-5 rounded-xl shadow-lg hover:shadow-primary-violet/20 transition-all gap-3">
                  Accelerate My Career Launch
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
            </div>
          </motion.div>

        </motion.div>
      </main>
    </div>
  )
}