'use client'

import { useState } from 'react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import {
    RefreshCw, Copy, Trophy, Target, MessageSquare,
    Zap, ChevronRight, ChevronDown, CheckCircle,
    XCircle, Lightbulb, Star, ArrowRight
} from 'lucide-react'
import type {
    Answer, StreakData, RankData
} from '../hooks/useInterviewSession'

// ─── Types ────────────────────────────────────────────────────────────────────

interface ResultsScreenProps {
    // Score
    totalScore: number
    careerPath: string
    answers: Answer[]
    interviewMode: string

    // Post-session data
    streakData: StreakData | null
    streakMessage: string | null
    rankData: RankData | null
    xpEarned: number | null
    leveledUp: boolean
    newBadge: { emoji: string; name: string } | null

    // Weekly challenge
    isWeeklyMode: boolean
    challengeRank: number | null
    challengeTotalParticipants: number

    // Helpers
    getScoreColor: (score: number) => string
    getPerformanceRating: (score: number) => string

    // Actions
    onReset: () => void
}

// ─── Sub-component: Expandable question card ──────────────────────────────────

function QuestionCard({
    answer,
    index,
    getScoreColor,
}: {
    answer: Answer
    index: number
    getScoreColor: (score: number) => string
}) {
    const [expanded, setExpanded] = useState(false)
    const score = answer.feedback?.score || 0

    return (
        <div className="bg-[#1E293B] rounded-2xl border border-white/5 overflow-hidden">
            {/* Header row — always visible */}
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full flex items-center justify-between p-6 hover:bg-white/[0.02] transition-colors text-left"
            >
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
                            Question {index + 1}
                        </span>
                    </div>
                    <p className="font-bold text-slate-100 truncate pr-4">
                        {answer.question.length > 100
                            ? answer.question.substring(0, 100) + '...'
                            : answer.question}
                    </p>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                    <div className={`px-4 py-2 rounded-xl text-lg font-black border-2 ${getScoreColor(score)}`}>
                        {score}/10
                    </div>
                    {expanded
                        ? <ChevronDown className="w-4 h-4 text-slate-400" />
                        : <ChevronRight className="w-4 h-4 text-slate-400" />
                    }
                </div>
            </button>

            {/* Expanded — real AI feedback */}
            <AnimatePresence>
                {expanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                    >
                        <div className="px-6 pb-6 space-y-4 border-t border-white/5 pt-4">

                            {/* Your answer */}
                            <div>
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">
                                    Your Answer
                                </p>
                                <p className="text-sm text-slate-300 font-medium leading-relaxed bg-[#0F172A] rounded-xl p-4 border border-white/5">
                                    {answer.answer || '(No answer provided)'}
                                </p>
                            </div>

                            {/* Good points */}
                            {answer.feedback?.good_points?.length > 0 && (
                                <div>
                                    <p className="text-[10px] font-black uppercase tracking-widest text-green-400 mb-2 flex items-center gap-1">
                                        <CheckCircle className="w-3 h-3" /> What You Got Right
                                    </p>
                                    <ul className="space-y-1.5">
                                        {answer.feedback.good_points.map((point, i) => (
                                            <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                                                <CheckCircle className="w-3.5 h-3.5 text-green-400 flex-shrink-0 mt-0.5" />
                                                {point}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Missing points */}
                            {answer.feedback?.missing_points?.length > 0 && (
                                <div>
                                    <p className="text-[10px] font-black uppercase tracking-widest text-red-400 mb-2 flex items-center gap-1">
                                        <XCircle className="w-3 h-3" /> What Was Missing
                                    </p>
                                    <ul className="space-y-1.5">
                                        {answer.feedback.missing_points.map((point, i) => (
                                            <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                                                <XCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0 mt-0.5" />
                                                {point}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Model answer */}
                            {answer.feedback?.model_answer && (
                                <div>
                                    <p className="text-[10px] font-black uppercase tracking-widest text-purple-400 mb-2 flex items-center gap-1">
                                        <Star className="w-3 h-3" /> Model Answer
                                    </p>
                                    <p className="text-sm text-slate-300 leading-relaxed bg-purple-500/5 border border-purple-500/20 rounded-xl p-4">
                                        {answer.feedback.model_answer}
                                    </p>
                                </div>
                            )}

                            {/* Tip */}
                            {answer.feedback?.tip && (
                                <div className="flex items-start gap-2 p-3 bg-yellow-500/5 border border-yellow-500/20 rounded-xl">
                                    <Lightbulb className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
                                    <p className="text-xs text-yellow-300 font-medium leading-snug">
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
    getScoreColor, getPerformanceRating,
    onReset,
}: ResultsScreenProps) {

    const [copied, setCopied] = useState(false)
    const scorePercent = (totalScore / 50) * 100

    const copyResults = () => {
        const text = `I just completed an AI Interview for ${careerPath} and scored ${totalScore}/50! Check out AI Career Navigator!`
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    return (
        <motion.div
            key="results"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-4xl mx-auto space-y-10 pb-20"
        >

            {/* ── Weekly Challenge Result ───────────────────────────────────────── */}
            {isWeeklyMode && (
                <div className="bg-gradient-to-br from-[#1E293B] to-[#0F172A] rounded-3xl p-8 border border-purple-500/30 shadow-[0_0_40px_rgba(108,63,200,0.2)]">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="p-3 bg-purple-500/20 rounded-2xl border border-purple-500/30">
                            <Trophy className="w-6 h-6 text-purple-400" />
                        </div>
                        <h2 className="text-xl font-black uppercase tracking-widest text-white">
                            Weekly Challenge Completed!
                        </h2>
                    </div>
                    <div className="grid grid-cols-3 gap-6">
                        <div className="text-center">
                            <div className="text-4xl font-black text-purple-400 mb-1">{totalScore}</div>
                            <div className="text-xs font-black uppercase tracking-widest text-slate-500">/ 50 Points</div>
                        </div>
                        <div className="text-center">
                            <div className="text-4xl font-black text-yellow-400 mb-1">
                                {challengeRank !== null ? `#${challengeRank}` : '—'}
                            </div>
                            <div className="text-xs font-black uppercase tracking-widest text-slate-500">
                                {challengeRank !== null ? 'Your Rank' : 'Pending'}
                            </div>
                        </div>
                        <div className="text-center">
                            <div className="text-4xl font-black text-white mb-1">
                                {challengeTotalParticipants || '—'}
                            </div>
                            <div className="text-xs font-black uppercase tracking-widest text-slate-500">Participants</div>
                        </div>
                    </div>
                    {challengeRank === null && (
                        <p className="mt-4 text-center text-sm text-slate-400">
                            Your results will appear in the leaderboard shortly.
                        </p>
                    )}
                </div>
            )}

            {/* ── Score Circle ─────────────────────────────────────────────────── */}
            <div className="bg-[#1E293B] rounded-3xl p-16 border border-white/5 text-center shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-purple-600 opacity-5 rounded-full blur-[100px] pointer-events-none" />

                <div className="relative flex flex-col items-center">
                    <div className="relative w-56 h-56 mb-10">
                        <svg className="w-full h-full -rotate-90" viewBox="0 0 224 224">
                            <circle cx="112" cy="112" r="100" stroke="currentColor" strokeWidth="12"
                                fill="transparent" className="text-slate-800" />
                            <motion.circle
                                cx="112" cy="112" r="100"
                                stroke="currentColor" strokeWidth="12"
                                fill="transparent" strokeLinecap="round"
                                strokeDasharray={2 * Math.PI * 100}
                                initial={{ strokeDashoffset: 2 * Math.PI * 100 }}
                                animate={{ strokeDashoffset: 2 * Math.PI * 100 * (1 - scorePercent / 100) }}
                                transition={{ duration: 2, ease: 'easeOut' }}
                                className={scorePercent >= 80 ? 'text-yellow-400' : 'text-purple-500'}
                            />
                        </svg>
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <span className="text-7xl font-black tracking-tighter text-white">{totalScore}</span>
                            <span className="text-xs font-black uppercase tracking-widest text-slate-500">/ 50 Points</span>
                        </div>
                    </div>

                    <h2 className={`text-5xl font-black tracking-tighter mb-4 ${scorePercent >= 80 ? 'text-yellow-400' : 'text-purple-400'
                        }`}>
                        {getPerformanceRating(totalScore)}
                    </h2>
                    <p className="text-slate-400 font-bold text-lg max-w-md">
                        {interviewMode === 'hr' ? 'HR Round' :
                            interviewMode === 'system_design' ? 'System Design Round' :
                                'Technical Round'} · {careerPath}
                    </p>
                </div>
            </div>

            {/* ── Streak + Rank + XP ────────────────────────────────────────────── */}
            {(streakData || rankData || xpEarned) && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {streakData && (
                        <div className="bg-[#1E293B] rounded-2xl p-5 border border-white/5 text-center">
                            <Zap className="w-6 h-6 text-orange-400 mx-auto mb-2" />
                            <div className="text-3xl font-black text-white">{streakData.current_streak}</div>
                            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mt-1">
                                Day Streak
                            </div>
                        </div>
                    )}
                    {rankData && (
                        <div className="bg-[#1E293B] rounded-2xl p-5 border border-white/5 text-center">
                            <Trophy className="w-6 h-6 text-purple-400 mx-auto mb-2" />
                            <div className="text-lg font-black text-white truncate">{rankData.rank_title}</div>
                            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mt-1">
                                Level {rankData.level}
                            </div>
                        </div>
                    )}
                    {xpEarned != null && xpEarned > 0 && (
                        <div className="bg-[#1E293B] rounded-2xl p-5 border border-yellow-500/20 text-center">
                            <Star className="w-6 h-6 text-yellow-400 mx-auto mb-2" />
                            <div className="text-3xl font-black text-yellow-400">+{xpEarned}</div>
                            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mt-1">
                                XP Earned
                            </div>
                        </div>
                    )}
                    {leveledUp && (
                        <div className="bg-gradient-to-br from-yellow-500/20 to-orange-500/20 rounded-2xl p-5 border border-yellow-500/30 text-center">
                            <div className="text-2xl mb-1">🎉</div>
                            <div className="text-sm font-black text-yellow-400">Level Up!</div>
                            <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mt-1">
                                New Rank
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ── Badge Earned ─────────────────────────────────────────────────── */}
            {newBadge && (
                <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="p-8 bg-gradient-to-r from-yellow-500/20 to-orange-500/20 rounded-3xl border border-yellow-500/30 flex items-center gap-6"
                >
                    <div className="text-6xl">{newBadge.emoji}</div>
                    <div>
                        <div className="text-[10px] font-black uppercase tracking-widest text-yellow-400">
                            Badge Unlocked
                        </div>
                        <div className="text-2xl font-black text-white">{newBadge.name}</div>
                    </div>
                </motion.div>
            )}

            {/* ── Streak message ────────────────────────────────────────────────── */}
            {streakMessage && (
                <div className="flex items-center gap-3 p-4 bg-orange-500/10 border border-orange-500/20 rounded-2xl">
                    <Zap className="w-5 h-5 text-orange-400 flex-shrink-0" />
                    <p className="text-sm font-bold text-orange-300">{streakMessage}</p>
                </div>
            )}

            {/* ── Per-question breakdown (expandable with REAL AI feedback) ────── */}
            <div className="space-y-4">
                <h3 className="text-sm font-black uppercase tracking-widest text-slate-400 flex items-center gap-3">
                    <MessageSquare className="w-5 h-5" /> Question Breakdown
                    <span className="text-[10px] text-slate-600 font-bold normal-case tracking-normal">
                        — tap any question to see full AI feedback
                    </span>
                </h3>
                <div className="space-y-3">
                    {answers.map((a, i) => (
                        <QuestionCard
                            key={i}
                            answer={a}
                            index={i}
                            getScoreColor={getScoreColor}
                        />
                    ))}
                </div>
            </div>

            {/* ── Actions ──────────────────────────────────────────────────────── */}
            <div className="flex flex-wrap gap-4 justify-center pt-8 border-t border-white/5">
                <Button
                    onClick={onReset}
                    className="bg-purple-600 hover:bg-purple-700 text-white font-black uppercase tracking-widest px-8 py-6 rounded-xl"
                >
                    <RefreshCw className="w-4 h-4 mr-2" /> New Session
                </Button>

                <Button
                    onClick={copyResults}
                    variant="outline"
                    className="border-white/10 text-slate-400 hover:text-white font-black uppercase tracking-widest px-8 py-6 rounded-xl"
                >
                    <Copy className="w-4 h-4 mr-2" />
                    {copied ? 'Copied!' : 'Share Score'}
                </Button>

                <Link href="/progress">
                    <Button
                        variant="outline"
                        className="border-white/10 text-slate-400 hover:text-white font-black uppercase tracking-widest px-8 py-6 rounded-xl"
                    >
                        View History <ArrowRight className="w-4 h-4 ml-2" />
                    </Button>
                </Link>

                <Link href="/dashboard">
                    <Button
                        variant="outline"
                        className="border-white/10 text-slate-400 hover:text-white font-black uppercase tracking-widest py-6 rounded-xl px-8"
                    >
                        Dashboard
                    </Button>
                </Link>
            </div>

        </motion.div>
    )
}