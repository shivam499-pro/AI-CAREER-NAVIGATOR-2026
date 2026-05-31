'use client'

import { useState } from 'react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import {
    RefreshCw, Copy, Trophy, Target, MessageSquare,
    Zap, ChevronRight, ChevronDown, CheckCircle,
    XCircle, Lightbulb, Star, ArrowRight, BarChart3
} from 'lucide-react'
import type {
    Answer, StreakData, RankData
} from '../hooks/useInterviewSession'

// ─── Types ────────────────────────────────────────────────────────────────────
// ALL UNCHANGED

interface ResultsScreenProps {
    totalScore: number
    careerPath: string
    answers: Answer[]
    interviewMode: string
    streakData: StreakData | null
    streakMessage: string | null
    rankData: RankData | null
    xpEarned: number | null
    leveledUp: boolean
    newBadge: { emoji: string; name: string } | null
    isWeeklyMode: boolean
    challengeRank: number | null
    challengeTotalParticipants: number
    getScoreColor: (score: number) => string
    getPerformanceRating: (score: number) => string
    onReset: () => void
}

// ─── Design helpers ───────────────────────────────────────────────────────────

function scoreGradient(pct: number) {
    if (pct >= 80) return { stroke: '#FBBF24', glow: 'rgba(251,191,36,0.25)', text: 'text-yellow-400', label: 'from-yellow-400 to-orange-300' }
    if (pct >= 60) return { stroke: '#8B5CF6', glow: 'rgba(139,92,246,0.25)', text: 'text-purple-400', label: 'from-purple-400 to-violet-300' }
    return { stroke: '#64748B', glow: 'rgba(100,116,139,0.15)', text: 'text-slate-400', label: 'from-slate-400 to-slate-300' }
}

/** Layered CTA button — matches SetupScreen / InterviewScreen language */
function CTAButton({
    onClick, children, variant = 'primary', className = '',
}: {
    onClick?: () => void
    children: React.ReactNode
    variant?: 'primary' | 'ghost'
    className?: string
}) {
    if (variant === 'ghost') {
        return (
            <button
                onClick={onClick}
                className={`relative flex items-center gap-2 px-6 py-3.5 rounded-2xl
                    font-black text-[12px] uppercase tracking-widest
                    border border-white/[0.08] text-slate-400
                    hover:text-white hover:border-white/[0.16] hover:bg-white/[0.03]
                    transition-all duration-200 focus:outline-none group ${className}`}
            >
                {children}
            </button>
        )
    }
    return (
        <button
            onClick={onClick}
            className={`relative flex items-center gap-2 px-8 py-3.5 rounded-2xl
                font-black text-[12px] uppercase tracking-widest text-white
                overflow-hidden transition-all duration-200
                hover:scale-[1.02] active:scale-[0.97]
                focus:outline-none focus:ring-2 focus:ring-purple-500/40
                focus:ring-offset-2 focus:ring-offset-[#0F172A] group ${className}`}
        >
            <span className="absolute inset-0 bg-gradient-to-r from-purple-600 to-violet-600" />
            <span className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity
                bg-gradient-to-r from-purple-500 to-violet-500" />
            <span className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
            <span className="relative z-10 flex items-center gap-2">{children}</span>
        </button>
    )
}

// ─── Sub-component: Expandable Question Card ──────────────────────────────────

function QuestionCard({
    answer, index, getScoreColor,
}: {
    answer: Answer
    index: number
    getScoreColor: (score: number) => string
}) {
    const [expanded, setExpanded] = useState(false)
    const score = answer.feedback?.score || 0
    const pct = (score / 10) * 100

    // Score-based accent for this card
    const accent =
        score >= 8 ? { border: 'rgba(52,211,153,0.2)', glow: 'rgba(52,211,153,0.1)', bar: 'from-emerald-500 to-green-400', num: 'text-emerald-400' } :
        score >= 6 ? { border: 'rgba(139,92,246,0.2)', glow: 'rgba(139,92,246,0.1)', bar: 'from-purple-600 to-violet-400', num: 'text-purple-400' } :
        score >= 4 ? { border: 'rgba(251,191,36,0.2)', glow: 'rgba(251,191,36,0.1)', bar: 'from-yellow-500 to-amber-400', num: 'text-yellow-400' } :
                     { border: 'rgba(239,68,68,0.2)', glow: 'rgba(239,68,68,0.08)', bar: 'from-red-600 to-rose-500', num: 'text-red-400' }

    return (
        <div
            className="rounded-2xl border overflow-hidden transition-all duration-300
                bg-[#131C2E] shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]"
            style={{
                borderColor: expanded ? accent.border : 'rgba(255,255,255,0.05)',
                boxShadow: expanded ? `0 0 24px ${accent.glow}, inset 0 1px 0 rgba(255,255,255,0.03)` : 'inset 0 1px 0 rgba(255,255,255,0.03)',
            }}
        >
            {/* Header — always visible */}
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full flex items-center gap-4 px-5 py-4
                    hover:bg-white/[0.02] transition-colors text-left group"
            >
                {/* Mini score ring */}
                <div className="relative flex-shrink-0 w-11 h-11">
                    <svg className="w-11 h-11 -rotate-90" viewBox="0 0 44 44">
                        <circle cx="22" cy="22" r="17"
                            fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="3" />
                        <motion.circle
                            cx="22" cy="22" r="17"
                            fill="none"
                            stroke={accent.num.replace('text-', '').includes('emerald') ? '#34D399'
                                : accent.num.includes('purple') ? '#8B5CF6'
                                : accent.num.includes('yellow') ? '#FBBF24'
                                : '#EF4444'}
                            strokeWidth="3" strokeLinecap="round"
                            strokeDasharray={2 * Math.PI * 17}
                            initial={{ strokeDashoffset: 2 * Math.PI * 17 }}
                            animate={{ strokeDashoffset: 2 * Math.PI * 17 * (1 - pct / 100) }}
                            transition={{ duration: 0.8, ease: 'easeOut', delay: index * 0.08 }}
                        />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                        <span className={`text-[11px] font-black tabular-nums ${accent.num}`}>
                            {score}
                        </span>
                    </div>
                </div>

                {/* Question text */}
                <div className="flex-1 min-w-0">
                    <p className="text-[10px] font-black text-slate-600 uppercase tracking-widest mb-1">
                        Question {index + 1}
                    </p>
                    <p className="text-[0.875rem] font-semibold text-slate-200 leading-snug
                        group-hover:text-white transition-colors truncate pr-2">
                        {answer.question.length > 100
                            ? answer.question.substring(0, 100) + '…'
                            : answer.question}
                    </p>
                </div>

                {/* Expand chevron */}
                <motion.div
                    animate={{ rotate: expanded ? 90 : 0 }}
                    transition={{ duration: 0.2 }}
                    className="flex-shrink-0"
                >
                    <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 transition-colors" />
                </motion.div>
            </button>

            {/* Expanded feedback */}
            <AnimatePresence>
                {expanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.25 }}
                        className="overflow-hidden"
                    >
                        <div className="border-t px-5 py-5 space-y-4"
                            style={{ borderColor: 'rgba(255,255,255,0.04)' }}>

                            {/* Your answer */}
                            <div>
                                <p className="text-[9px] font-black uppercase tracking-[0.16em] text-slate-600 mb-2">
                                    Your Answer
                                </p>
                                <div className="px-4 py-3.5 rounded-xl bg-[#0C1525] border border-white/[0.05]
                                    shadow-[inset_0_1px_0_rgba(255,255,255,0.02)]">
                                    <p className="text-[13px] text-slate-400 font-medium leading-relaxed">
                                        {answer.answer || '(No answer provided)'}
                                    </p>
                                </div>
                            </div>

                            {/* Good points */}
                            {answer.feedback?.good_points?.length > 0 && (
                                <div>
                                    <p className="text-[9px] font-black uppercase tracking-[0.16em]
                                        text-emerald-500/80 mb-2.5 flex items-center gap-1.5">
                                        <CheckCircle className="w-2.5 h-2.5" />
                                        What You Got Right
                                    </p>
                                    <ul className="space-y-2">
                                        {answer.feedback.good_points.map((point, i) => (
                                            <li key={i} className="flex items-start gap-2.5 text-[13px] text-slate-300 font-medium">
                                                <CheckCircle className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                                                {point}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Missing points */}
                            {answer.feedback?.missing_points?.length > 0 && (
                                <div>
                                    <p className="text-[9px] font-black uppercase tracking-[0.16em]
                                        text-red-500/80 mb-2.5 flex items-center gap-1.5">
                                        <XCircle className="w-2.5 h-2.5" />
                                        What Was Missing
                                    </p>
                                    <ul className="space-y-2">
                                        {answer.feedback.missing_points.map((point, i) => (
                                            <li key={i} className="flex items-start gap-2.5 text-[13px] text-slate-300 font-medium">
                                                <XCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0 mt-0.5" />
                                                {point}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Model answer — gold treatment */}
                            {answer.feedback?.model_answer && (
                                <div>
                                    <p className="text-[9px] font-black uppercase tracking-[0.16em]
                                        text-yellow-500/80 mb-2.5 flex items-center gap-1.5">
                                        <Star className="w-2.5 h-2.5" />
                                        Model Answer
                                    </p>
                                    <div className="px-4 py-3.5 rounded-xl
                                        bg-yellow-500/[0.05] border border-yellow-500/[0.15]
                                        shadow-[inset_0_1px_0_rgba(251,191,36,0.05)]">
                                        <p className="text-[13px] text-slate-200 leading-relaxed font-medium">
                                            {answer.feedback.model_answer}
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* Tip */}
                            {answer.feedback?.tip && (
                                <div className="flex items-start gap-2.5 px-4 py-3 rounded-xl
                                    bg-amber-500/[0.06] border border-amber-500/[0.15]">
                                    <Lightbulb className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
                                    <p className="text-[12px] text-amber-200/80 font-medium leading-relaxed">
                                        {answer.feedback.tip}
                                    </p>
                                </div>
                            )}

                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function ResultsScreen({
    totalScore, careerPath, answers, interviewMode,
    streakData, streakMessage, rankData, xpEarned, leveledUp, newBadge,
    isWeeklyMode, challengeRank, challengeTotalParticipants,
    getScoreColor, getPerformanceRating, onReset,
}: ResultsScreenProps) {

    // ── State — ALL UNCHANGED ─────────────────────────────────────────────────
    const [copied, setCopied] = useState(false)
    const scorePercent = (totalScore / 50) * 100
    const colors = scoreGradient(scorePercent)

    // ── Handlers — ALL UNCHANGED ──────────────────────────────────────────────
    const copyResults = () => {
        const text = `I just completed an AI Interview for ${careerPath} and scored ${totalScore}/50! Check out AI Career Navigator!`
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    const modeLabel =
        interviewMode === 'hr' ? 'HR Round' :
        interviewMode === 'system_design' ? 'System Design Round' :
        'Technical Round'

    const circumference = 2 * Math.PI * 100

    return (
        <motion.div
            key="results"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="max-w-4xl mx-auto space-y-8 pb-20"
        >

            {/* ── Ambient background ──────────────────────────────────────────── */}
            <div className="fixed inset-0 pointer-events-none -z-10 overflow-hidden">
                <div
                    className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[700px] h-[700px] rounded-full blur-[140px] opacity-[0.06]"
                    style={{ background: colors.stroke }}
                />
            </div>

            {/* ── Weekly Challenge Banner ─────────────────────────────────────── */}
            {isWeeklyMode && (
                <motion.div
                    initial={{ opacity: 0, y: -12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="rounded-3xl overflow-hidden relative"
                    style={{
                        background: 'linear-gradient(135deg, rgba(139,92,246,0.12) 0%, rgba(15,23,42,0.95) 100%)',
                        boxShadow: '0 0 0 1px rgba(139,92,246,0.2), 0 16px 48px rgba(139,92,246,0.15)',
                    }}
                >
                    {/* Top line */}
                    <div className="h-px w-full bg-gradient-to-r from-purple-500/60 via-violet-400/30 to-transparent" />

                    <div className="p-8">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="w-11 h-11 rounded-2xl flex items-center justify-center
                                bg-gradient-to-br from-purple-500/30 to-violet-600/10
                                border border-purple-500/20
                                shadow-[0_0_16px_rgba(139,92,246,0.25)]">
                                <Trophy className="w-5 h-5 text-purple-400" />
                            </div>
                            <div>
                                <p className="text-[10px] font-black uppercase tracking-[0.16em] text-purple-400/70 mb-0.5">
                                    Competition
                                </p>
                                <h2 className="text-lg font-black text-white tracking-tight">
                                    Weekly Challenge Completed
                                </h2>
                            </div>
                        </div>

                        <div className="grid grid-cols-3 gap-4">
                            {[
                                { label: 'Your Score', value: `${totalScore}`, sub: '/ 50 pts', color: 'text-white' },
                                { label: 'Leaderboard Rank', value: challengeRank !== null ? `#${challengeRank}` : '—', sub: 'pending', color: 'text-yellow-400' },
                                { label: 'Participants', value: challengeTotalParticipants || '—', sub: 'total', color: 'text-slate-200' },
                            ].map((stat) => (
                                <div key={stat.label}
                                    className="text-center px-4 py-4 rounded-2xl
                                        bg-white/[0.03] border border-white/[0.05]">
                                    <div className={`text-3xl font-black tabular-nums mb-1 ${stat.color}`}>
                                        {stat.value}
                                    </div>
                                    <div className="text-[10px] font-black uppercase tracking-widest text-slate-600">
                                        {stat.sub}
                                    </div>
                                    <div className="text-[11px] text-slate-500 font-medium mt-0.5">
                                        {stat.label}
                                    </div>
                                </div>
                            ))}
                        </div>

                        {challengeRank === null && (
                            <p className="mt-4 text-center text-[12px] text-slate-600 font-medium">
                                Your results will appear in the leaderboard shortly.
                            </p>
                        )}
                    </div>
                </motion.div>
            )}

            {/* ── Score Hero ───────────────────────────────────────────────────── */}
            <motion.div
                initial={{ opacity: 0, scale: 0.97 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.08, duration: 0.45 }}
                className="relative rounded-3xl overflow-hidden text-center
                    bg-gradient-to-b from-[#131C2E] to-[#0C1525]
                    border border-white/[0.06]
                    shadow-[0_4px_32px_rgba(0,0,0,0.4),inset_0_1px_0_rgba(255,255,255,0.04)]"
            >
                {/* Score-colored top line */}
                <div
                    className="h-px w-full"
                    style={{ background: `linear-gradient(90deg, transparent, ${colors.stroke}80, transparent)` }}
                />

                {/* Ambient glow behind ring */}
                <div
                    className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-72 h-72 rounded-full blur-[80px] pointer-events-none"
                    style={{ background: colors.glow }}
                />

                <div className="relative px-16 py-16 flex flex-col items-center">

                    {/* SVG Ring */}
                    <div className="relative w-52 h-52 mb-8">
                        <svg className="w-full h-full -rotate-90" viewBox="0 0 224 224">
                            {/* Track */}
                            <circle cx="112" cy="112" r="100"
                                stroke="rgba(255,255,255,0.04)" strokeWidth="10" fill="transparent" />
                            {/* Progress */}
                            <motion.circle
                                cx="112" cy="112" r="100"
                                stroke={colors.stroke}
                                strokeWidth="10" fill="transparent" strokeLinecap="round"
                                strokeDasharray={circumference}
                                initial={{ strokeDashoffset: circumference }}
                                animate={{ strokeDashoffset: circumference * (1 - scorePercent / 100) }}
                                transition={{ duration: 1.8, ease: [0.25, 0.46, 0.45, 0.94], delay: 0.2 }}
                                style={{ filter: `drop-shadow(0 0 8px ${colors.stroke}60)` }}
                            />
                        </svg>

                        {/* Inner score */}
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <motion.span
                                initial={{ opacity: 0, scale: 0.7 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: 0.5, duration: 0.4, ease: 'backOut' }}
                                className="text-6xl font-black tracking-tighter text-white leading-none"
                            >
                                {totalScore}
                            </motion.span>
                            <span className="text-[10px] font-black uppercase tracking-[0.16em] text-slate-600 mt-1">
                                / 50 pts
                            </span>
                        </div>
                    </div>

                    {/* Performance label */}
                    <motion.h2
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.6 }}
                        className={`text-5xl font-black tracking-[-0.03em] mb-3
                            text-transparent bg-clip-text bg-gradient-to-r ${colors.label}`}
                    >
                        {getPerformanceRating(totalScore)}
                    </motion.h2>

                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.7 }}
                        className="text-slate-500 font-semibold text-[0.9rem]"
                    >
                        {modeLabel}
                        <span className="mx-2 text-slate-700">·</span>
                        {careerPath}
                    </motion.p>
                </div>
            </motion.div>

            {/* ── Badge Earned ─────────────────────────────────────────────────── */}
            <AnimatePresence>
                {newBadge && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.8, y: 16 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        transition={{ type: 'spring', stiffness: 280, damping: 22, delay: 0.3 }}
                        className="flex items-center gap-6 p-7 rounded-3xl relative overflow-hidden"
                        style={{
                            background: 'linear-gradient(135deg, rgba(251,191,36,0.1) 0%, rgba(249,115,22,0.06) 100%)',
                            boxShadow: '0 0 0 1px rgba(251,191,36,0.2), 0 8px 32px rgba(251,191,36,0.1)',
                        }}
                    >
                        <div className="h-px absolute inset-x-0 top-0 bg-gradient-to-r from-transparent via-yellow-400/40 to-transparent" />

                        <motion.div
                            animate={{ rotate: [0, -8, 8, -4, 4, 0] }}
                            transition={{ delay: 0.6, duration: 0.6 }}
                            className="text-6xl flex-shrink-0 leading-none"
                        >
                            {newBadge.emoji}
                        </motion.div>
                        <div>
                            <p className="text-[10px] font-black uppercase tracking-[0.16em] text-yellow-500/80 mb-1">
                                Badge Unlocked
                            </p>
                            <p className="text-2xl font-black text-white tracking-tight">
                                {newBadge.name}
                            </p>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ── Streak / Rank / XP Grid ──────────────────────────────────────── */}
            {(streakData || rankData || xpEarned) && (
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.25 }}
                    className="grid grid-cols-2 md:grid-cols-4 gap-3"
                >
                    {streakData && (
                        <StatCard
                            icon={<Zap className="w-4 h-4 text-orange-400" />}
                            iconBg="bg-orange-500/10 border-orange-500/15"
                            value={streakData.current_streak}
                            suffix="day"
                            label="Streak"
                            valueColor="text-orange-400"
                        />
                    )}
                    {rankData && (
                        <StatCard
                            icon={<Trophy className="w-4 h-4 text-purple-400" />}
                            iconBg="bg-purple-500/10 border-purple-500/15"
                            value={rankData.rank_title}
                            suffix={`Lvl ${rankData.level}`}
                            label="Rank"
                            valueColor="text-purple-400"
                            smallValue
                        />
                    )}
                    {xpEarned != null && xpEarned > 0 && (
                        <StatCard
                            icon={<Star className="w-4 h-4 text-yellow-400" />}
                            iconBg="bg-yellow-500/10 border-yellow-500/15"
                            value={`+${xpEarned}`}
                            label="XP Earned"
                            valueColor="text-yellow-400"
                        />
                    )}
                    {leveledUp && (
                        <div
                            className="flex flex-col items-center justify-center gap-1
                                rounded-2xl p-5 border text-center"
                            style={{
                                background: 'linear-gradient(135deg, rgba(251,191,36,0.08) 0%, rgba(249,115,22,0.05) 100%)',
                                borderColor: 'rgba(251,191,36,0.2)',
                            }}
                        >
                            <span className="text-3xl">🎉</span>
                            <p className="text-sm font-black text-yellow-400">Level Up!</p>
                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-600">
                                New Rank
                            </p>
                        </div>
                    )}
                </motion.div>
            )}

            {/* ── Streak message ────────────────────────────────────────────────── */}
            {streakMessage && (
                <div className="flex items-center gap-3 px-5 py-4
                    rounded-2xl bg-orange-500/[0.07] border border-orange-500/[0.15]">
                    <Zap className="w-4 h-4 text-orange-400 flex-shrink-0" />
                    <p className="text-[13px] font-semibold text-orange-200/80">{streakMessage}</p>
                </div>
            )}

            {/* ── Question Breakdown ───────────────────────────────────────────── */}
            <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                className="space-y-4"
            >
                <div className="flex items-center gap-3 px-1">
                    <div className="w-7 h-7 rounded-xl flex items-center justify-center
                        bg-slate-800 border border-white/[0.06]">
                        <MessageSquare className="w-3.5 h-3.5 text-slate-500" />
                    </div>
                    <h3 className="text-[11px] font-black uppercase tracking-[0.14em] text-slate-500">
                        Question Breakdown
                    </h3>
                    <span className="text-[10px] text-slate-700 font-medium">
                        · tap to see AI feedback
                    </span>
                </div>

                <div className="space-y-2.5">
                    {answers.map((a, i) => (
                        <QuestionCard
                            key={i}
                            answer={a}
                            index={i}
                            getScoreColor={getScoreColor}
                        />
                    ))}
                </div>
            </motion.div>

            {/* ── Actions ──────────────────────────────────────────────────────── */}
            <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.45 }}
                className="pt-6 border-t border-white/[0.05]"
            >
                <div className="flex flex-wrap gap-3 justify-center">
                    <CTAButton onClick={onReset} variant="primary">
                        <RefreshCw className="w-3.5 h-3.5" />
                        New Session
                    </CTAButton>

                    <CTAButton onClick={copyResults} variant="ghost">
                        <Copy className="w-3.5 h-3.5" />
                        {copied ? 'Copied!' : 'Share Score'}
                    </CTAButton>

                    <Link href="/progress">
                        <CTAButton variant="ghost">
                            <BarChart3 className="w-3.5 h-3.5" />
                            View History
                            <ArrowRight className="w-3 h-3 opacity-50" />
                        </CTAButton>
                    </Link>

                    <Link href="/dashboard">
                        <CTAButton variant="ghost">
                            Dashboard
                        </CTAButton>
                    </Link>
                </div>
            </motion.div>

        </motion.div>
    )
}

// ─── StatCard sub-component ───────────────────────────────────────────────────

function StatCard({
    icon, iconBg, value, suffix, label, valueColor, smallValue = false,
}: {
    icon: React.ReactNode
    iconBg: string
    value: string | number
    suffix?: string
    label: string
    valueColor: string
    smallValue?: boolean
}) {
    return (
        <div className="flex flex-col items-center gap-2 px-4 py-5 rounded-2xl text-center
            bg-[#131C2E] border border-white/[0.05]
            shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
            <div className={`w-8 h-8 rounded-xl border flex items-center justify-center ${iconBg}`}>
                {icon}
            </div>
            <div className={`font-black tabular-nums ${valueColor} ${smallValue ? 'text-base leading-tight' : 'text-2xl'}`}>
                {value}
            </div>
            {suffix && (
                <div className="text-[10px] font-black uppercase tracking-widest text-slate-600 -mt-1">
                    {suffix}
                </div>
            )}
            <div className="text-[10px] font-black uppercase tracking-widest text-slate-700">
                {label}
            </div>
        </div>
    )
}