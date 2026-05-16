'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import {
    Loader2, ChevronDown, ChevronUp,
    Zap, Brain, Users, Building2, Code, Layers
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
// Each pack bundles: difficulty + personality + interviewMode + simMode
// Students pick an outcome, not a configuration

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
    accent: string
    iconBg: string
}

const PACKS: Pack[] = [
    {
        id: 'warmup',
        icon: <Users className="w-6 h-6" />,
        label: 'Warm Up',
        tagline: 'Build confidence, reduce anxiety',
        duration: '10–15 min',
        what: ['Intro & background questions', 'Friendly AI interviewer', 'Detailed feedback per answer'],
        difficulty: 'easy',
        personality: 'friendly',
        mode: 'hr',
        sim: false,
        accent: 'border-blue-500/40 hover:border-blue-500/70',
        iconBg: 'bg-blue-500/20 text-blue-400',
    },
    {
        id: 'technical',
        icon: <Code className="w-6 h-6" />,
        label: 'Technical Round',
        tagline: 'Real engineering interview questions',
        duration: '20–25 min',
        what: ['Coding & problem solving', 'Strict technical interviewer', 'Score + model answers'],
        difficulty: 'medium',
        personality: 'strict',
        mode: 'technical',
        sim: false,
        accent: 'border-purple-500/40 hover:border-purple-500/70',
        iconBg: 'bg-purple-500/20 text-purple-400',
    },
    {
        id: 'faang',
        icon: <Building2 className="w-6 h-6" />,
        label: 'FAANG Prep',
        tagline: 'Google · Meta · Amazon level pressure',
        duration: '25–30 min',
        what: ['Hard questions, 2 min per answer', 'FAANG-style interviewer', 'Stress-test your readiness'],
        difficulty: 'hard',
        personality: 'google',
        mode: 'technical',
        sim: true,
        accent: 'border-orange-500/40 hover:border-orange-500/70',
        iconBg: 'bg-orange-500/20 text-orange-400',
    },
    {
        id: 'system',
        icon: <Layers className="w-6 h-6" />,
        label: 'System Design',
        tagline: 'Architecture & scalability thinking',
        duration: '25–30 min',
        what: ['Design large-scale systems', 'Senior-level depth expected', 'Concept + tradeoffs focus'],
        difficulty: 'hard',
        personality: 'strict',
        mode: 'system_design',
        sim: false,
        accent: 'border-cyan-500/40 hover:border-cyan-500/70',
        iconBg: 'bg-cyan-500/20 text-cyan-400',
    },
]

// ─── Component ────────────────────────────────────────────────────────────────

export default function SetupScreen({
    careerPath, careerPaths, pastSessions, loading,
    setCareerPath, setDifficulty, setPersonality, setInterviewMode, setSimMode,
    onStart, resumeModal,
}: SetupScreenProps) {

    const [selectedPack, setSelectedPack] = useState<string>('technical')
    const [showAdvanced, setShowAdvanced] = useState(false)

    // Advanced overrides (power users only)
    const [advDifficulty, setAdvDifficulty] = useState('')
    const [advPersonality, setAdvPersonality] = useState('')
    const [advMode, setAdvMode] = useState<InterviewMode | ''>('')
    const [advSim, setAdvSim] = useState<boolean | null>(null)

    const handleLaunch = () => {
        const pack = PACKS.find(p => p.id === selectedPack)!

        // Apply pack defaults, override with advanced settings if set
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
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            className="max-w-2xl mx-auto"
        >
            {resumeModal}

            {/* ── Header ──────────────────────────────────────────────────────── */}
            <div className="text-center mb-10">
                <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-purple-500/10 border border-purple-500/20 rounded-full mb-4">
                    <Brain className="w-3.5 h-3.5 text-purple-400" />
                    <span className="text-xs font-black text-purple-400 uppercase tracking-widest">
                        AI Interview Coach
                    </span>
                </div>
                <h1 className="text-4xl font-black text-white tracking-tight mb-3">
                    What are you{' '}
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-violet-300">
                        preparing for?
                    </span>
                </h1>
                <p className="text-slate-400 font-medium">
                    {pastSessions > 0
                        ? `${pastSessions} sessions completed · Keep the momentum going`
                        : 'Pick a session type and launch in seconds'}
                </p>
            </div>

            <div className="space-y-6">

                {/* ── Step 1: Career Path ──────────────────────────────────────── */}
                <div className="space-y-3">
                    <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-purple-600 flex items-center justify-center text-xs font-black text-white">
                            1
                        </div>
                        <p className="text-sm font-black text-white uppercase tracking-widest">
                            Target Role
                        </p>
                    </div>
                    {careerPaths.length > 0 ? (
                        <select
                            value={careerPath}
                            onChange={(e) => setCareerPath(e.target.value)}
                            className="w-full bg-[#1E293B] px-5 py-4 text-white rounded-2xl border border-white/10 focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none font-bold text-base appearance-none cursor-pointer"
                        >
                            {careerPaths.map((p, i) => (
                                <option key={i} value={p}>{p}</option>
                            ))}
                        </select>
                    ) : (
                        <div className="w-full bg-[#1E293B] px-5 py-4 rounded-2xl border border-yellow-500/30 text-yellow-400 text-sm font-bold">
                            ⚠ Run Analysis first to unlock personalized questions
                        </div>
                    )}
                </div>

                {/* ── Step 2: Interview Pack ───────────────────────────────────── */}
                <div className="space-y-3">
                    <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-purple-600 flex items-center justify-center text-xs font-black text-white">
                            2
                        </div>
                        <p className="text-sm font-black text-white uppercase tracking-widest">
                            Session Type
                        </p>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        {PACKS.map((pack) => {
                            const isSelected = selectedPack === pack.id
                            return (
                                <motion.button
                                    key={pack.id}
                                    onClick={() => setSelectedPack(pack.id)}
                                    whileTap={{ scale: 0.97 }}
                                    className={`text-left p-5 rounded-2xl border-2 transition-all duration-200 relative overflow-hidden ${isSelected
                                        ? `${pack.accent} bg-[#1E293B]`
                                        : 'border-white/5 bg-[#1E293B]/60 hover:bg-[#1E293B]'
                                        }`}
                                >
                                    {/* Selected glow */}
                                    {isSelected && (
                                        <div className="absolute inset-0 bg-gradient-to-br from-white/[0.03] to-transparent pointer-events-none" />
                                    )}

                                    <div className="relative z-10">
                                        <div className="flex items-start justify-between mb-3">
                                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${pack.iconBg}`}>
                                                {pack.icon}
                                            </div>
                                            {pack.sim && (
                                                <div className="flex items-center gap-1 px-2 py-0.5 bg-orange-500/20 border border-orange-500/30 rounded-full">
                                                    <Zap className="w-2.5 h-2.5 text-orange-400" />
                                                    <span className="text-[9px] font-black text-orange-400 uppercase">Timed</span>
                                                </div>
                                            )}
                                        </div>

                                        <p className="font-black text-white text-base mb-1">{pack.label}</p>
                                        <p className="text-xs text-slate-400 font-medium mb-3 leading-snug">
                                            {pack.tagline}
                                        </p>

                                        <AnimatePresence>
                                            {isSelected && (
                                                <motion.ul
                                                    initial={{ opacity: 0, height: 0 }}
                                                    animate={{ opacity: 1, height: 'auto' }}
                                                    exit={{ opacity: 0, height: 0 }}
                                                    className="space-y-1 overflow-hidden"
                                                >
                                                    {pack.what.map((item, i) => (
                                                        <li key={i} className="flex items-center gap-2 text-[11px] text-slate-300 font-medium">
                                                            <div className="w-1 h-1 rounded-full bg-purple-400 flex-shrink-0" />
                                                            {item}
                                                        </li>
                                                    ))}
                                                    <li className="flex items-center gap-2 text-[11px] text-slate-500 font-medium pt-1">
                                                        <div className="w-1 h-1 rounded-full bg-slate-600 flex-shrink-0" />
                                                        {pack.duration}
                                                    </li>
                                                </motion.ul>
                                            )}
                                        </AnimatePresence>
                                    </div>
                                </motion.button>
                            )
                        })}
                    </div>
                </div>

                {/* ── Advanced Settings (collapsed by default) ─────────────────── */}
                <div className="border border-white/5 rounded-2xl overflow-hidden">
                    <button
                        onClick={() => setShowAdvanced(!showAdvanced)}
                        className="w-full flex items-center justify-between px-5 py-4 text-slate-500 hover:text-slate-300 transition-colors"
                    >
                        <span className="text-xs font-black uppercase tracking-widest">
                            Advanced Settings
                        </span>
                        {showAdvanced
                            ? <ChevronUp className="w-4 h-4" />
                            : <ChevronDown className="w-4 h-4" />
                        }
                    </button>

                    <AnimatePresence>
                        {showAdvanced && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                className="overflow-hidden border-t border-white/5"
                            >
                                <div className="p-5 space-y-5 bg-[#0F172A]/40">
                                    <p className="text-xs text-slate-500 font-medium">
                                        Override defaults for this session. Leave blank to use pack settings.
                                    </p>

                                    {/* Difficulty override */}
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-500">
                                            Difficulty
                                        </label>
                                        <div className="flex gap-2">
                                            {['', 'easy', 'medium', 'hard'].map((d) => (
                                                <button
                                                    key={d}
                                                    onClick={() => setAdvDifficulty(d)}
                                                    className={`flex-1 py-2 rounded-xl text-xs font-black uppercase tracking-wider transition-all border ${advDifficulty === d
                                                        ? 'bg-purple-600 border-purple-600 text-white'
                                                        : 'bg-transparent border-white/10 text-slate-500 hover:border-white/20'
                                                        }`}
                                                >
                                                    {d === '' ? 'Auto' : d}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Interviewer persona override */}
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-500">
                                            Interviewer Style
                                        </label>
                                        <div className="flex gap-2">
                                            {[
                                                { id: '', label: 'Auto' },
                                                { id: 'friendly', label: '😊 Friendly' },
                                                { id: 'strict', label: '😐 Strict' },
                                                { id: 'google', label: '😈 FAANG' },
                                            ].map((p) => (
                                                <button
                                                    key={p.id}
                                                    onClick={() => setAdvPersonality(p.id)}
                                                    className={`flex-1 py-2 rounded-xl text-xs font-black uppercase tracking-wider transition-all border ${advPersonality === p.id
                                                        ? 'bg-purple-600 border-purple-600 text-white'
                                                        : 'bg-transparent border-white/10 text-slate-500 hover:border-white/20'
                                                        }`}
                                                >
                                                    {p.label}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Sim mode override */}
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-500">
                                            Timer Mode
                                        </label>
                                        <div className="flex gap-2">
                                            {[
                                                { val: null, label: 'Auto' },
                                                { val: false, label: 'Practice' },
                                                { val: true, label: '⚡ Simulation' },
                                            ].map((m) => (
                                                <button
                                                    key={String(m.val)}
                                                    onClick={() => setAdvSim(m.val)}
                                                    className={`flex-1 py-2 rounded-xl text-xs font-black uppercase tracking-wider transition-all border ${advSim === m.val
                                                        ? 'bg-purple-600 border-purple-600 text-white'
                                                        : 'bg-transparent border-white/10 text-slate-500 hover:border-white/20'
                                                        }`}
                                                >
                                                    {m.label}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                {/* ── Launch ───────────────────────────────────────────────────── */}
                <Button
                    onClick={handleLaunch}
                    disabled={loading || careerPaths.length === 0}
                    className="w-full h-16 rounded-2xl text-xl font-black uppercase tracking-tighter bg-gradient-to-r from-purple-600 to-violet-500 hover:scale-[1.02] active:scale-95 transition-all shadow-[0_0_30px_rgba(139,92,246,0.3)] disabled:opacity-40 disabled:cursor-not-allowed disabled:scale-100"
                >
                    {loading ? (
                        <Loader2 className="w-6 h-6 animate-spin" />
                    ) : (
                        <>
                            Start {activePack.label} · {activePack.duration}
                        </>
                    )}
                </Button>

            </div>
        </motion.div>
    )
}