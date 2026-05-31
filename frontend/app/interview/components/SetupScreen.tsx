'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import {
    Loader2, ChevronDown, ChevronUp,
    Zap, Brain, Users, Building2, Code, Layers, ArrowRight
} from 'lucide-react'
import type { InterviewMode } from '../hooks/useInterviewSession'

// ─── Types ────────────────────────────────────────────────────────────────────

interface SetupScreenProps {
    careerPath: string
    careerPaths: string[]
    pastSessions: number
    loading: boolean
    setCareerPath: (v: string) => void
    setDifficulty: (v: string) => void
    setPersonality: (v: string) => void
    setInterviewMode: (v: InterviewMode) => void
    setSimMode: (v: boolean) => void
    onStart: () => void
    resumeModal?: React.ReactNode
}

// ─── Interview Packs ──────────────────────────────────────────────────────────

interface Pack {
    id: string
    icon: React.ReactNode
    label: string
    tagline: string
    duration: string
    what: string[]
    difficulty: string
    personality: string
    mode: InterviewMode
    sim: boolean
    // Design tokens — only these changed vs original
    borderColor: string
    glowRgb: string
    iconGradient: string
    iconColor: string
    tagBg: string
    tagBorder: string
    tagColor: string
    chipColor: string
}

const PACKS: Pack[] = [
    {
        id: 'warmup',
        icon: <Users className="w-5 h-5" />,
        label: 'Warm Up',
        tagline: 'Build confidence, reduce anxiety',
        duration: '10–15 min',
        what: ['Intro & background questions', 'Friendly AI interviewer', 'Detailed feedback per answer'],
        difficulty: 'easy',
        personality: 'friendly',
        mode: 'hr',
        sim: false,
        borderColor: '#3B82F6',
        glowRgb: '59,130,246',
        iconGradient: 'from-blue-500/30 to-blue-600/10',
        iconColor: 'text-blue-400',
        tagBg: 'bg-blue-500/10',
        tagBorder: 'border-blue-500/20',
        tagColor: 'text-blue-300',
        chipColor: 'bg-blue-500/20 text-blue-300',
    },
    {
        id: 'technical',
        icon: <Code className="w-5 h-5" />,
        label: 'Technical Round',
        tagline: 'Real engineering interview questions',
        duration: '20–25 min',
        what: ['Coding & problem solving', 'Strict technical interviewer', 'Score + model answers'],
        difficulty: 'medium',
        personality: 'strict',
        mode: 'technical',
        sim: false,
        borderColor: '#8B5CF6',
        glowRgb: '139,92,246',
        iconGradient: 'from-purple-500/30 to-purple-600/10',
        iconColor: 'text-purple-400',
        tagBg: 'bg-purple-500/10',
        tagBorder: 'border-purple-500/20',
        tagColor: 'text-purple-300',
        chipColor: 'bg-purple-500/20 text-purple-300',
    },
    {
        id: 'faang',
        icon: <Building2 className="w-5 h-5" />,
        label: 'FAANG Prep',
        tagline: 'Google · Meta · Amazon level pressure',
        duration: '25–30 min',
        what: ['Hard questions, 2 min per answer', 'FAANG-style interviewer', 'Stress-test your readiness'],
        difficulty: 'hard',
        personality: 'google',
        mode: 'technical',
        sim: true,
        borderColor: '#F97316',
        glowRgb: '249,115,22',
        iconGradient: 'from-orange-500/30 to-orange-600/10',
        iconColor: 'text-orange-400',
        tagBg: 'bg-orange-500/10',
        tagBorder: 'border-orange-500/20',
        tagColor: 'text-orange-300',
        chipColor: 'bg-orange-500/20 text-orange-300',
    },
    {
        id: 'system',
        icon: <Layers className="w-5 h-5" />,
        label: 'System Design',
        tagline: 'Architecture & scalability thinking',
        duration: '25–30 min',
        what: ['Design large-scale systems', 'Senior-level depth expected', 'Concept + tradeoffs focus'],
        difficulty: 'hard',
        personality: 'strict',
        mode: 'system_design',
        sim: false,
        borderColor: '#06B6D4',
        glowRgb: '6,182,212',
        iconGradient: 'from-cyan-500/30 to-cyan-600/10',
        iconColor: 'text-cyan-400',
        tagBg: 'bg-cyan-500/10',
        tagBorder: 'border-cyan-500/20',
        tagColor: 'text-cyan-300',
        chipColor: 'bg-cyan-500/20 text-cyan-300',
    },
]

// ─── Sub-components ───────────────────────────────────────────────────────────

/** Numbered step badge with gradient ring */
function StepBadge({ n, active }: { n: number; active: boolean }) {
    return (
        <div className="relative flex items-center justify-center w-7 h-7 shrink-0">
            {active && (
                <span className="absolute inset-0 rounded-full bg-purple-500/30 animate-ping opacity-60" />
            )}
            <div
                className={`relative z-10 w-7 h-7 rounded-full flex items-center justify-center text-xs font-black
                    ${active
                        ? 'bg-gradient-to-br from-purple-500 to-violet-600 text-white shadow-[0_0_12px_rgba(139,92,246,0.5)]'
                        : 'bg-[#1E293B] border border-white/10 text-slate-400'
                    }`}
            >
                {n}
            </div>
        </div>
    )
}

/** Pill-style option toggle button */
function TogglePill({
    active, onClick, children,
}: {
    active: boolean
    onClick: () => void
    children: React.ReactNode
}) {
    return (
        <button
            onClick={onClick}
            className={`relative flex-1 py-2.5 rounded-xl text-[11px] font-black uppercase tracking-widest transition-all duration-200 border overflow-hidden
                ${active
                    ? 'border-purple-500/60 text-white shadow-[0_0_12px_rgba(139,92,246,0.25)]'
                    : 'border-white/[0.06] text-slate-500 hover:text-slate-300 hover:border-white/[0.12]'
                }`}
        >
            {active && (
                <span className="absolute inset-0 bg-gradient-to-br from-purple-600 to-violet-700" />
            )}
            <span className="relative z-10">{children}</span>
        </button>
    )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function SetupScreen({
    careerPath, careerPaths, pastSessions, loading,
    setCareerPath, setDifficulty, setPersonality, setInterviewMode, setSimMode,
    onStart, resumeModal,
}: SetupScreenProps) {

    const [selectedPack, setSelectedPack] = useState<string>('technical')
    const [showAdvanced, setShowAdvanced] = useState(false)

    // Advanced overrides (power users only) — LOGIC UNCHANGED
    const [advDifficulty, setAdvDifficulty] = useState('')
    const [advPersonality, setAdvPersonality] = useState('')
    const [advMode, setAdvMode] = useState<InterviewMode | ''>('')
    const [advSim, setAdvSim] = useState<boolean | null>(null)

    // LOGIC UNCHANGED
    const handleLaunch = () => {
        const pack = PACKS.find(p => p.id === selectedPack)!
        setDifficulty(advDifficulty || pack.difficulty)
        setPersonality(advPersonality || pack.personality)
        setInterviewMode((advMode || pack.mode) as InterviewMode)
        setSimMode(advSim !== null ? advSim : pack.sim)
        onStart()
    }

    const activePack = PACKS.find(p => p.id === selectedPack)!

    return (
        <motion.div
            key="setup"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="max-w-2xl mx-auto"
        >
            {resumeModal}

            {/* ── Ambient background orbs ─────────────────────────────────────── */}
            <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
                <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-purple-600/[0.04] blur-[120px]" />
                <div className="absolute bottom-1/3 right-1/4 w-[400px] h-[400px] rounded-full bg-violet-500/[0.03] blur-[100px]" />
            </div>

            {/* ── Header ──────────────────────────────────────────────────────── */}
            <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05, duration: 0.4 }}
                className="text-center mb-12"
            >
                {/* Badge */}
                <div className="inline-flex items-center gap-2 px-4 py-1.5 mb-5
                    bg-purple-500/[0.08] border border-purple-500/20 rounded-full
                    shadow-[0_0_20px_rgba(139,92,246,0.08)]"
                >
                    <Brain className="w-3.5 h-3.5 text-purple-400" />
                    <span className="text-[10px] font-black text-purple-400 uppercase tracking-[0.18em]">
                        AI Interview Coach
                    </span>
                </div>

                {/* Headline */}
                <h1 className="text-[2.75rem] leading-[1.1] font-black text-white tracking-[-0.03em] mb-3">
                    What are you{' '}
                    <span className="relative inline-block">
                        <span className="relative z-10 text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-violet-300 to-purple-400">
                            preparing for?
                        </span>
                        {/* Subtle underline glow */}
                        <span className="absolute -bottom-1 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-500/40 to-transparent" />
                    </span>
                </h1>

                {/* Sub */}
                <p className="text-slate-500 font-medium text-[0.9rem]">
                    {pastSessions > 0 ? (
                        <>
                            <span className="text-slate-300 font-semibold">{pastSessions} sessions</span>
                            {' '}completed · Keep the momentum going
                        </>
                    ) : (
                        'Pick a session type and launch in seconds'
                    )}
                </p>
            </motion.div>

            <div className="space-y-6">

                {/* ── Step 1: Target Role ──────────────────────────────────────── */}
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="space-y-3"
                >
                    <div className="flex items-center gap-2.5">
                        <StepBadge n={1} active={false} />
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.16em]">
                            Target Role
                        </p>
                    </div>

                    {careerPaths.length > 0 ? (
                        <div className="relative group">
                            <select
                                value={careerPath}
                                aria-label="Select career path"
                                onChange={(e) => setCareerPath(e.target.value)}
                                className="w-full bg-[#131C2E] px-5 py-4 text-white rounded-2xl
                                    border border-white/[0.07] focus:border-purple-500/50
                                    focus:ring-0 focus:outline-none
                                    font-semibold text-[0.95rem] appearance-none cursor-pointer
                                    transition-all duration-200
                                    group-hover:border-white/[0.12]
                                    shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
                            >
                                {careerPaths.map((p, i) => (
                                    <option key={i} value={p}>{p}</option>
                                ))}
                            </select>
                            {/* Custom dropdown arrow */}
                            <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none">
                                <ChevronDown className="w-4 h-4 text-slate-500" />
                            </div>
                        </div>
                    ) : (
                        <div className="w-full bg-[#131C2E] px-5 py-4 rounded-2xl
                            border border-yellow-500/20 text-yellow-400/90 text-sm font-semibold
                            flex items-center gap-2.5"
                        >
                            <span className="text-base">⚠</span>
                            Run Analysis first to unlock personalized questions
                        </div>
                    )}
                </motion.div>

                {/* ── Step 2: Session Pack ─────────────────────────────────────── */}
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15 }}
                    className="space-y-3"
                >
                    <div className="flex items-center gap-2.5">
                        <StepBadge n={2} active />
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.16em]">
                            Session Type
                        </p>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        {PACKS.map((pack, idx) => {
                            const isSelected = selectedPack === pack.id
                            return (
                                <motion.button
                                    key={pack.id}
                                    onClick={() => setSelectedPack(pack.id)}
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.18 + idx * 0.06 }}
                                    whileHover={{ y: -2 }}
                                    whileTap={{ scale: 0.975 }}
                                    className="text-left p-5 rounded-2xl border-[1.5px] relative overflow-hidden
                                        transition-all duration-250 focus:outline-none group"
                                    style={{
                                        borderColor: isSelected ? pack.borderColor : 'rgba(255,255,255,0.06)',
                                        background: isSelected
                                            ? `linear-gradient(135deg, rgba(${pack.glowRgb},0.08) 0%, rgba(15,23,42,0.95) 100%)`
                                            : 'rgba(19,28,46,0.7)',
                                        boxShadow: isSelected
                                            ? `0 0 0 1px rgba(${pack.glowRgb},0.15), 0 8px 32px rgba(${pack.glowRgb},0.12), inset 0 1px 0 rgba(255,255,255,0.04)`
                                            : 'inset 0 1px 0 rgba(255,255,255,0.03)',
                                    }}
                                >
                                    {/* Subtle noise texture overlay */}
                                    <div className="absolute inset-0 opacity-[0.015] bg-[url('data:image/svg+xml,%3Csvg viewBox=%220 0 256 256%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noise%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.9%22 numOctaves=%224%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noise)%22/%3E%3C/svg%3E')] pointer-events-none" />

                                    {/* Hover shimmer */}
                                    {!isSelected && (
                                        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300
                                            bg-gradient-to-br from-white/[0.02] to-transparent pointer-events-none" />
                                    )}

                                    <div className="relative z-10">
                                        {/* Icon row */}
                                        <div className="flex items-start justify-between mb-4">
                                            <div
                                                className={`w-10 h-10 rounded-xl flex items-center justify-center
                                                    bg-gradient-to-br ${pack.iconGradient} ${pack.iconColor}
                                                    border border-white/[0.06]`}
                                                style={{
                                                    boxShadow: isSelected ? `0 0 16px rgba(${pack.glowRgb},0.2)` : 'none'
                                                }}
                                            >
                                                {pack.icon}
                                            </div>

                                            {pack.sim && (
                                                <div className="flex items-center gap-1 px-2 py-0.5
                                                    bg-orange-500/15 border border-orange-500/25 rounded-full">
                                                    <Zap className="w-2.5 h-2.5 text-orange-400" />
                                                    <span className="text-[9px] font-black text-orange-400 uppercase tracking-wider">
                                                        Timed
                                                    </span>
                                                </div>
                                            )}
                                        </div>

                                        {/* Label */}
                                        <p className="font-black text-white text-[0.95rem] mb-1 tracking-[-0.01em]">
                                            {pack.label}
                                        </p>
                                        <p className={`text-xs font-medium mb-3 leading-snug
                                            ${isSelected ? 'text-slate-300' : 'text-slate-500'}`}>
                                            {pack.tagline}
                                        </p>

                                        {/* Expanded details on selection */}
                                        <AnimatePresence>
                                            {isSelected && (
                                                <motion.div
                                                    initial={{ opacity: 0, height: 0 }}
                                                    animate={{ opacity: 1, height: 'auto' }}
                                                    exit={{ opacity: 0, height: 0 }}
                                                    transition={{ duration: 0.22 }}
                                                    className="overflow-hidden"
                                                >
                                                    {/* Divider */}
                                                    <div
                                                        className="h-px mb-3"
                                                        style={{ background: `linear-gradient(90deg, rgba(${pack.glowRgb},0.3), transparent)` }}
                                                    />
                                                    <ul className="space-y-1.5">
                                                        {pack.what.map((item, i) => (
                                                            <li key={i} className="flex items-center gap-2 text-[11px] text-slate-300 font-medium">
                                                                <div
                                                                    className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                                                                    style={{ background: `rgba(${pack.glowRgb},0.9)` }}
                                                                />
                                                                {item}
                                                            </li>
                                                        ))}
                                                        <li className="flex items-center gap-2 text-[11px] text-slate-600 font-medium pt-0.5">
                                                            <div className="w-1.5 h-1.5 rounded-full bg-slate-700 flex-shrink-0" />
                                                            {pack.duration}
                                                        </li>
                                                    </ul>
                                                </motion.div>
                                            )}
                                        </AnimatePresence>
                                    </div>
                                </motion.button>
                            )
                        })}
                    </div>
                </motion.div>

                {/* ── Advanced Settings ────────────────────────────────────────── */}
                <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.35 }}
                    className="rounded-2xl border border-white/[0.06] overflow-hidden
                        bg-[#0C1525]/60 backdrop-blur-sm"
                >
                    <button
                        onClick={() => setShowAdvanced(!showAdvanced)}
                        className="w-full flex items-center justify-between px-5 py-4
                            text-slate-500 hover:text-slate-300 transition-colors duration-200 group"
                    >
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-px bg-slate-700 group-hover:bg-slate-500 transition-colors" />
                            <span className="text-[10px] font-black uppercase tracking-[0.16em]">
                                Advanced Settings
                            </span>
                            <div className="w-4 h-px bg-slate-700 group-hover:bg-slate-500 transition-colors" />
                        </div>
                        <motion.div animate={{ rotate: showAdvanced ? 180 : 0 }} transition={{ duration: 0.2 }}>
                            <ChevronDown className="w-3.5 h-3.5" />
                        </motion.div>
                    </button>

                    <AnimatePresence>
                        {showAdvanced && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                transition={{ duration: 0.25 }}
                                className="overflow-hidden border-t border-white/[0.04]"
                            >
                                <div className="p-5 space-y-5">
                                    <p className="text-[11px] text-slate-600 font-medium">
                                        Override defaults for this session. Leave blank to use pack settings.
                                    </p>

                                    {/* ── Difficulty ─────────────────────────────────────────── */}
                                    <div className="space-y-2.5">
                                        <label className="text-[10px] font-black uppercase tracking-[0.14em] text-slate-600">
                                            Difficulty
                                        </label>
                                        <div className="flex gap-2">
                                            {['', 'easy', 'medium', 'hard'].map((d) => (
                                                <TogglePill
                                                    key={d}
                                                    active={advDifficulty === d}
                                                    onClick={() => setAdvDifficulty(d)}
                                                >
                                                    {d === '' ? 'Auto' : d}
                                                </TogglePill>
                                            ))}
                                        </div>
                                    </div>

                                    {/* ── Interviewer Style ───────────────────────────────────── */}
                                    <div className="space-y-2.5">
                                        <label className="text-[10px] font-black uppercase tracking-[0.14em] text-slate-600">
                                            Interviewer Style
                                        </label>
                                        <div className="flex gap-2">
                                            {[
                                                { id: '', label: 'Auto' },
                                                { id: 'friendly', label: '😊 Friendly' },
                                                { id: 'strict', label: '😐 Strict' },
                                                { id: 'google', label: '😈 FAANG' },
                                            ].map((p) => (
                                                <TogglePill
                                                    key={p.id}
                                                    active={advPersonality === p.id}
                                                    onClick={() => setAdvPersonality(p.id)}
                                                >
                                                    {p.label}
                                                </TogglePill>
                                            ))}
                                        </div>
                                    </div>

                                    {/* ── Timer Mode ──────────────────────────────────────────── */}
                                    <div className="space-y-2.5">
                                        <label className="text-[10px] font-black uppercase tracking-[0.14em] text-slate-600">
                                            Timer Mode
                                        </label>
                                        <div className="flex gap-2">
                                            {[
                                                { val: null, label: 'Auto' },
                                                { val: false, label: 'Practice' },
                                                { val: true, label: '⚡ Simulation' },
                                            ].map((m) => (
                                                <TogglePill
                                                    key={String(m.val)}
                                                    active={advSim === m.val}
                                                    onClick={() => setAdvSim(m.val)}
                                                >
                                                    {m.label}
                                                </TogglePill>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.div>

                {/* ── Launch CTA ───────────────────────────────────────────────── */}
                <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                >
                    <button
                        onClick={handleLaunch}
                        disabled={loading || careerPaths.length === 0}
                        className="relative w-full h-[60px] rounded-2xl overflow-hidden
                            font-black text-white text-base uppercase tracking-[0.06em]
                            transition-all duration-200
                            hover:scale-[1.015] active:scale-[0.985]
                            disabled:opacity-40 disabled:cursor-not-allowed disabled:scale-100
                            focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:ring-offset-2 focus:ring-offset-[#0F172A]
                            group"
                    >
                        {/* Base gradient */}
                        <span className="absolute inset-0 bg-gradient-to-r from-purple-600 via-violet-600 to-purple-600 bg-[length:200%_100%]
                            group-hover:animate-[shimmer_1.5s_ease-in-out_infinite]" />

                        {/* Glow layer */}
                        <span className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300
                            shadow-[0_0_40px_rgba(139,92,246,0.5)]" />

                        {/* Top highlight */}
                        <span className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/25 to-transparent" />

                        {/* Content */}
                        <span className="relative z-10 flex items-center justify-center gap-3">
                            {loading ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                <>
                                    <span>Start {activePack.label}</span>
                                    <span className="w-px h-4 bg-white/20" />
                                    <span className="text-white/70 font-semibold text-sm normal-case tracking-normal">
                                        {activePack.duration}
                                    </span>
                                    <ArrowRight className="w-4 h-4 opacity-60 group-hover:translate-x-0.5 transition-transform" />
                                </>
                            )}
                        </span>
                    </button>
                </motion.div>

            </div>
        </motion.div>
    )
}