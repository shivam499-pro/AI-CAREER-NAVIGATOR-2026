'use client'

import { useState, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { supabase } from '@/lib/supabase'
import { toast } from 'sonner'
import {
    Brain, Loader2, Lightbulb, Mic, Square,
    Volume2, Sparkles, Clock, Zap, ChevronRight, ArrowRight
} from 'lucide-react'
import AICoachPanel from './AICoachPanel'
import type { Question, AuthenticityStatus } from '../hooks/useInterviewSession'
import type { VoiceStatus, CommScore } from '../hooks/useVoiceInput'

// ─── Types ────────────────────────────────────────────────────────────────────
// ALL UNCHANGED

interface ChatMessage { role: 'ai' | 'user'; text: string }

interface InterviewScreenProps {
    questions: Question[]
    currentQuestion: number
    answer: string
    submitting: boolean
    elapsedTime: number
    messages: ChatMessage[]
    interviewMode: string
    careerPath: string
    simMode: boolean
    typingBehavior: { startTime: number | null; keystrokes: number; typingDuration: number }
    authenticityStatus: AuthenticityStatus
    setAnswer: (v: string) => void
    setTypingBehavior: (v: any) => void
    setPasteAttempted: (v: boolean) => void
    isRecording: boolean
    voiceStatus: VoiceStatus
    speechSupported: boolean
    isSpeaking: boolean
    usedVoiceInput: boolean
    commScore: CommScore | null
    toggleVoice: () => void
    speakQuestion: () => void
    simTimeLeft: number
    timerColor: string
    barColor: string
    barWidth: string
    isUrgent: boolean
    stopTimer: () => void
    weakestPath: string | null
    aiTip: string
    readinessScore: number
    brainLoaded: boolean
    formatTime: (s: number) => string
    getAiLabel: () => string
    submitAnswer: () => void
    handleTimeUp: () => void
}

// ─── Coaching hint fetch ─────────────────────────────────────────────────────
// ALL UNCHANGED

interface CoachingHint { looking_for: string; structure: string; example: string }

async function fetchCoachingHint(question: string, careerPath: string): Promise<CoachingHint> {
    const { data: { session } } = await supabase.auth.getSession()
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const res = await fetch(`${apiUrl}/api/v1/interview/question-hint`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
        },
        body: JSON.stringify({ question, career_path: careerPath }),
    })
    if (!res.ok) throw new Error('Hint fetch failed')
    return res.json()
}

// ─── Persona config ───────────────────────────────────────────────────────────
// ALL UNCHANGED — only extended with new design tokens

interface PersonaConfig {
    initials: string
    label: string
    // Design tokens added below — logic untouched
    avatarGradient: string
    avatarText: string
    avatarGlow: string
    accentColor: string
    accentRgb: string
}

function getPersonaConfig(aiLabel: string): PersonaConfig {
    switch (aiLabel) {
        case 'FAANG Interviewer':
            return {
                initials: 'FA', label: aiLabel,
                avatarGradient: 'from-orange-500/30 to-orange-700/10',
                avatarText: 'text-orange-300',
                avatarGlow: '0 0 16px rgba(249,115,22,0.25)',
                accentColor: 'border-orange-500/30',
                accentRgb: '249,115,22',
            }
        case 'Technical Interviewer':
            return {
                initials: 'TI', label: aiLabel,
                avatarGradient: 'from-blue-500/30 to-blue-700/10',
                avatarText: 'text-blue-300',
                avatarGlow: '0 0 16px rgba(59,130,246,0.25)',
                accentColor: 'border-blue-500/30',
                accentRgb: '59,130,246',
            }
        default:
            return {
                initials: 'AI', label: 'AI Coach',
                avatarGradient: 'from-purple-500/30 to-violet-700/10',
                avatarText: 'text-purple-300',
                avatarGlow: '0 0 16px rgba(139,92,246,0.25)',
                accentColor: 'border-purple-500/30',
                accentRgb: '139,92,246',
            }
    }
}

// ─── Sub-components ───────────────────────────────────────────────────────────

/** Compact icon action button — replaces generic hover:bg-white/5 patterns */
function IconAction({
    onClick, active = false, activeClass = '', label, children,
}: {
    onClick: () => void
    active?: boolean
    activeClass?: string
    label: string
    children: React.ReactNode
}) {
    return (
        <button
            onClick={onClick}
            aria-label={label}
            className={`p-2 rounded-xl transition-all duration-200 focus:outline-none
                ${active
                    ? activeClass || 'bg-purple-600/80 text-white'
                    : 'text-slate-500 hover:text-slate-200 hover:bg-white/[0.05]'
                }`}
        >
            {children}
        </button>
    )
}

/** Pill action button — matches SetupScreen's TogglePill visual language */
function ActionPill({
    onClick, active = false, activeClass = 'bg-purple-600/90 border-purple-500/60 text-white',
    children,
}: {
    onClick: () => void
    active?: boolean
    activeClass?: string
    children: React.ReactNode
}) {
    return (
        <button
            onClick={onClick}
            className={`relative flex items-center gap-2 px-4 py-2.5 rounded-xl
                text-[11px] font-black uppercase tracking-widest
                transition-all duration-200 border overflow-hidden
                focus:outline-none focus:ring-1 focus:ring-purple-500/30
                ${active
                    ? activeClass
                    : 'border-white/[0.07] text-slate-500 hover:text-slate-200 hover:border-white/[0.14] bg-transparent'
                }`}
        >
            {children}
        </button>
    )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function InterviewScreen({
    questions, currentQuestion, answer, submitting, elapsedTime, messages,
    interviewMode, careerPath, simMode,
    typingBehavior, authenticityStatus,
    setAnswer, setTypingBehavior, setPasteAttempted,
    isRecording, voiceStatus, speechSupported, isSpeaking,
    usedVoiceInput, commScore, toggleVoice, speakQuestion,
    simTimeLeft, timerColor, barColor, barWidth, isUrgent, stopTimer,
    weakestPath, aiTip, readinessScore, brainLoaded,
    formatTime, getAiLabel, submitAnswer, handleTimeUp,
}: InterviewScreenProps) {

    // ── State — ALL UNCHANGED ─────────────────────────────────────────────────
    const [showCoachingHint, setShowCoachingHint] = useState(false)
    const [coachingHint, setCoachingHint] = useState<CoachingHint | null>(null)
    const [hintLoading, setHintLoading] = useState(false)
    const [showAICoachPanel, setShowAICoachPanel] = useState(false)
    const [showHistory, setShowHistory] = useState(false)

    const q = questions[currentQuestion]
    const persona = getPersonaConfig(getAiLabel())

    // ── Handlers — ALL UNCHANGED ──────────────────────────────────────────────
    useEffect(() => {
        setCoachingHint(null)
        setShowCoachingHint(false)
    }, [currentQuestion])

    const handleFetchHint = useCallback(async () => {
        if (!q) return
        setHintLoading(true)
        try {
            const hint = await fetchCoachingHint(q.question, careerPath)
            setCoachingHint(hint)
        } catch {
            toast.error('Failed to fetch hint.')
        } finally {
            setHintLoading(false)
        }
    }, [q, careerPath])

    const toggleCoachingHint = useCallback(() => {
        if (!showCoachingHint && !coachingHint) handleFetchHint()
        setShowCoachingHint(prev => !prev)
    }, [showCoachingHint, coachingHint, handleFetchHint])

    const handleSubmit = useCallback(() => {
        stopTimer()
        submitAnswer()
    }, [stopTimer, submitAnswer])

    const handleAnswerChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const val = e.target.value
        setAnswer(val)
        if (!typingBehavior.startTime && val.length > 0) {
            setTypingBehavior({ ...typingBehavior, startTime: Date.now() })
        }
        if (val.length > answer.length) {
            setTypingBehavior({
                ...typingBehavior,
                keystrokes: typingBehavior.keystrokes + (val.length - answer.length),
            })
        }
    }

    const handlePaste = (e: React.ClipboardEvent) => {
        e.preventDefault()
        setPasteAttempted(true)
        toast.error('Paste disabled — type your answer genuinely.')
        setTimeout(() => setPasteAttempted(false), 3000)
    }

    if (!q) return null

    // ── Derived display values — UNCHANGED ────────────────────────────────────
    const modeLabel =
        interviewMode === 'hr' ? 'HR Round' :
            interviewMode === 'system_design' ? 'System Design' :
                'Technical Round'

    const wordCount = answer.trim() ? answer.trim().split(/\s+/).length : 0

    // Word count color: consistent visual progression
    const wordCountColor =
        wordCount === 0 ? 'text-slate-700' :
            wordCount < 30 ? 'text-red-500/70' :
                wordCount < 60 ? 'text-yellow-500/80' :
                    'text-emerald-500/80'

    // Sim timer: parse barWidth % for ring calculation
    const barWidthNum = parseFloat(barWidth) || 100
    const ringCircumference = 2 * Math.PI * 18 // r=18
    const ringOffset = ringCircumference * (1 - barWidthNum / 100)

    return (
        <motion.div
            key="interview"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }}
            transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="max-w-3xl mx-auto space-y-4"
        >

            {/* ── Top Command Bar ──────────────────────────────────────────────── */}
            <div className="flex items-center justify-between gap-4 px-1">

                {/* Left cluster: question position + mode + timed badge */}
                <div className="flex items-center gap-2.5">
                    {/* Question counter */}
                    <div className="flex items-baseline gap-1">
                        <span className="text-sm font-black text-white tabular-nums">
                            Q{currentQuestion + 1}
                        </span>
                        <span className="text-[11px] font-semibold text-slate-600">
                            /{questions.length}
                        </span>
                    </div>

                    <span className="w-px h-3.5 bg-white/[0.08]" />

                    <span className="text-[11px] font-semibold text-slate-500">{modeLabel}</span>

                    {simMode && (
                        <div className="flex items-center gap-1 px-2 py-0.5
                            bg-orange-500/10 border border-orange-500/20 rounded-full">
                            <Zap className="w-2.5 h-2.5 text-orange-400" />
                            <span className="text-[9px] font-black text-orange-400 uppercase tracking-widest">
                                Timed
                            </span>
                        </div>
                    )}
                </div>

                {/* Right cluster: elapsed + coach toggle */}
                <div className="flex items-center gap-2">
                    {/* Elapsed time — subtle */}
                    <div className="flex items-center gap-1.5 px-3 py-1.5
                        bg-[#131C2E] border border-white/[0.05] rounded-xl">
                        <Clock className="w-3 h-3 text-slate-600" />
                        <span className="text-[11px] font-bold tabular-nums text-slate-500">
                            {formatTime(elapsedTime)}
                        </span>
                    </div>

                    {/* AI Coach toggle */}
                    <button
                        onClick={() => setShowAICoachPanel(!showAICoachPanel)}
                        className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-xl
                            text-[11px] font-black uppercase tracking-widest
                            transition-all duration-200 border overflow-hidden
                            focus:outline-none
                            ${showAICoachPanel
                                ? 'border-purple-500/50 text-white shadow-[0_0_16px_rgba(139,92,246,0.2)]'
                                : 'border-white/[0.06] text-slate-500 hover:text-slate-300 hover:border-white/[0.12] bg-[#131C2E]'
                            }`}
                    >
                        {showAICoachPanel && (
                            <span className="absolute inset-0 bg-gradient-to-r from-purple-600/90 to-violet-700/90" />
                        )}
                        <Brain className="w-3 h-3 relative z-10" />
                        <span className="relative z-10">Coach</span>
                    </button>
                </div>
            </div>

            {/* ── Progress Segments ────────────────────────────────────────────── */}
            <div className="flex gap-1.5 px-1">
                {questions.map((_, i) => (
                    <div key={i} className="flex-1 relative h-1 rounded-full overflow-hidden bg-slate-800/80">
                        {i <= currentQuestion && (
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: '100%' }}
                                transition={{ duration: 0.4, ease: 'easeOut', delay: i === currentQuestion ? 0.1 : 0 }}
                                className={`absolute inset-y-0 left-0 rounded-full ${
                                    i < currentQuestion
                                        ? 'bg-gradient-to-r from-purple-600 to-violet-500'
                                        : 'bg-purple-400/70'
                                }`}
                            />
                        )}
                    </div>
                ))}
            </div>

            {/* ── Simulation Countdown Bar ─────────────────────────────────────── */}
            <AnimatePresence>
                {simMode && (
                    <motion.div
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -8 }}
                        className="flex items-center gap-4 px-5 py-3.5
                            bg-[#131C2E] rounded-2xl border border-white/[0.05]
                            shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]"
                    >
                        {/* Ring timer */}
                        <div className="relative flex-shrink-0 w-11 h-11">
                            <svg className="w-11 h-11 -rotate-90" viewBox="0 0 44 44">
                                {/* Track */}
                                <circle cx="22" cy="22" r="18"
                                    fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="3" />
                                {/* Progress */}
                                <circle cx="22" cy="22" r="18"
                                    fill="none"
                                    stroke={isUrgent ? '#EF4444' : barWidthNum > 50 ? '#8B5CF6' : '#F97316'}
                                    strokeWidth="3"
                                    strokeLinecap="round"
                                    strokeDasharray={ringCircumference}
                                    strokeDashoffset={ringOffset}
                                    style={{ transition: 'stroke-dashoffset 0.5s ease, stroke 0.5s ease' }}
                                />
                            </svg>
                            {/* Center countdown */}
                            <div className="absolute inset-0 flex items-center justify-center">
                                <span className={`text-[10px] font-black tabular-nums ${timerColor} ${isUrgent ? 'animate-pulse' : ''}`}>
                                    {formatTime(simTimeLeft).replace('0:', '')}
                                </span>
                            </div>
                        </div>

                        {/* Linear bar */}
                        <div className="flex-1 space-y-1">
                            <div className="flex items-center justify-between">
                                <span className="text-[10px] font-black uppercase tracking-widest text-slate-600">
                                    Answer time remaining
                                </span>
                                <span className={`text-xs font-black tabular-nums ${timerColor}`}>
                                    {formatTime(simTimeLeft)}
                                </span>
                            </div>
                            <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                <motion.div
                                    animate={{ width: barWidth }}
                                    transition={{ duration: 0.5, ease: 'easeOut' }}
                                    className={`h-full rounded-full ${barColor}`}
                                    style={{ boxShadow: isUrgent ? '0 0 8px rgba(239,68,68,0.5)' : 'none' }}
                                />
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ── Question Card ────────────────────────────────────────────────── */}
            <div
                className="rounded-3xl border overflow-hidden
                    bg-gradient-to-b from-[#131C2E] to-[#0F172A]/80
                    shadow-[0_4px_24px_rgba(0,0,0,0.3),inset_0_1px_0_rgba(255,255,255,0.04)]"
                style={{ borderColor: `rgba(${persona.accentRgb},0.15)` }}
            >
                {/* Colored top accent line */}
                <div
                    className="h-px w-full"
                    style={{
                        background: `linear-gradient(90deg, rgba(${persona.accentRgb},0.6), rgba(${persona.accentRgb},0.1), transparent)`,
                    }}
                />

                {/* Persona strip */}
                <div className="flex items-center gap-3.5 px-6 pt-5 pb-4
                    border-b"
                    style={{ borderColor: `rgba(${persona.accentRgb},0.08)` }}
                >
                    {/* Avatar */}
                    <div
                        className={`relative w-10 h-10 rounded-2xl flex items-center justify-center
                            text-xs font-black flex-shrink-0 border
                            bg-gradient-to-br ${persona.avatarGradient} ${persona.avatarText} ${persona.accentColor}`}
                        style={{ boxShadow: persona.avatarGlow }}
                    >
                        {persona.initials}
                        {/* Tiny live indicator */}
                        <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full
                            bg-emerald-500 border-2 border-[#0F172A]" />
                    </div>

                    <div className="flex-1 min-w-0">
                        <p className="text-xs font-black text-white tracking-tight">{persona.label}</p>
                        <p className="text-[10px] text-slate-600 font-medium mt-0.5 truncate">{careerPath}</p>
                    </div>

                    {/* Actions: speak + type badge */}
                    <div className="flex items-center gap-2">
                        {speechSupported && (
                            <IconAction
                                onClick={speakQuestion}
                                active={isSpeaking}
                                activeClass="bg-purple-600/60 text-purple-200"
                                label="Read question aloud"
                            >
                                <Volume2 className="w-4 h-4" />
                            </IconAction>
                        )}
                        <span className="px-2.5 py-1 bg-[#0F172A] border border-white/[0.06]
                            rounded-xl text-[10px] font-black text-slate-500 uppercase tracking-widest">
                            {q.type}
                        </span>
                    </div>
                </div>

                {/* Question text — the hero */}
                <div className="px-6 py-6">
                    <p className="text-[1.15rem] font-semibold text-white leading-[1.65] tracking-[-0.01em]">
                        {q.question}
                    </p>
                </div>

                {/* ── Coaching Hint ─────────────────────────────────────────────── */}
                <AnimatePresence>
                    {!simMode && showCoachingHint && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.25 }}
                            className="overflow-hidden"
                        >
                            <div className="mx-6 mb-6 rounded-2xl overflow-hidden"
                                style={{
                                    background: 'linear-gradient(135deg, rgba(139,92,246,0.06) 0%, rgba(15,23,42,0.8) 100%)',
                                    boxShadow: '0 0 0 1px rgba(139,92,246,0.15), inset 0 1px 0 rgba(139,92,246,0.08)',
                                }}
                            >
                                {hintLoading ? (
                                    <div className="flex items-center gap-3 p-5 text-slate-400 text-sm">
                                        <Loader2 className="w-4 h-4 animate-spin text-purple-400 flex-shrink-0" />
                                        <span className="text-xs font-medium text-slate-500">Generating strategy...</span>
                                    </div>
                                ) : coachingHint ? (
                                    <div className="p-5 space-y-4">
                                        <div className="flex items-center gap-2">
                                            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                                            <span className="text-[10px] font-black text-purple-400 uppercase tracking-[0.16em]">
                                                Strategy Hint
                                            </span>
                                        </div>
                                        <div className="space-y-4">
                                            <div>
                                                <p className="text-[9px] font-black text-slate-600 uppercase tracking-[0.14em] mb-1.5">
                                                    What they want to hear
                                                </p>
                                                <p className="text-sm text-slate-200 leading-relaxed font-medium">
                                                    {coachingHint.looking_for}
                                                </p>
                                            </div>
                                            <div className="h-px bg-white/[0.04]" />
                                            <div>
                                                <p className="text-[9px] font-black text-slate-600 uppercase tracking-[0.14em] mb-1.5">
                                                    Best structure
                                                </p>
                                                <p className="text-sm text-slate-300 italic leading-relaxed">
                                                    "{coachingHint.structure}"
                                                </p>
                                            </div>
                                            {coachingHint.example && (
                                                <>
                                                    <div className="h-px bg-white/[0.04]" />
                                                    <div>
                                                        <p className="text-[9px] font-black text-slate-600 uppercase tracking-[0.14em] mb-1.5">
                                                            Direction
                                                        </p>
                                                        <p className="text-sm text-slate-400 leading-relaxed">
                                                            {coachingHint.example}
                                                        </p>
                                                    </div>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                ) : null}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* ── AI Coach Panel ────────────────────────────────────────────── */}
                <AnimatePresence>
                    {showAICoachPanel && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.25 }}
                            className="overflow-hidden"
                        >
                            <div className="mx-6 mb-6">
                                <AICoachPanel
                                    weakestPath={weakestPath}
                                    aiTip={aiTip}
                                    readinessScore={readinessScore}
                                    loading={!brainLoaded}
                                />
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* ── Past Responses Toggle ────────────────────────────────────────── */}
            {messages.length > 2 && (
                <button
                    onClick={() => setShowHistory(!showHistory)}
                    className="flex items-center gap-2 text-[11px] text-slate-600
                        hover:text-slate-400 transition-colors font-bold group px-1"
                >
                    <ChevronRight
                        className={`w-3 h-3 transition-transform duration-200
                            ${showHistory ? 'rotate-90' : ''} group-hover:text-purple-400`}
                    />
                    {showHistory ? 'Hide' : 'Show'} conversation history
                    <span className="px-1.5 py-0.5 bg-[#1E293B] border border-white/[0.06]
                        rounded-md text-slate-600 text-[10px] font-black">
                        {Math.floor(messages.length / 2)}
                    </span>
                </button>
            )}

            <AnimatePresence>
                {showHistory && messages.length > 2 && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.22 }}
                        className="overflow-hidden"
                    >
                        <div className="space-y-2 max-h-52 overflow-y-auto pr-1 pl-1
                            [&::-webkit-scrollbar]:w-1
                            [&::-webkit-scrollbar-track]:bg-transparent
                            [&::-webkit-scrollbar-thumb]:bg-slate-800
                            [&::-webkit-scrollbar-thumb]:rounded-full">
                            {messages.slice(0, -1).map((msg, idx) => (
                                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    <div
                                        className={`max-w-[82%] rounded-2xl px-4 py-3 text-[13px] leading-relaxed font-medium
                                            ${msg.role === 'ai'
                                                ? 'bg-[#131C2E] text-slate-400 border border-white/[0.05] rounded-tl-md'
                                                : 'bg-purple-500/10 text-slate-300 border border-purple-500/15 rounded-tr-md'
                                            }`}
                                    >
                                        {msg.text.length > 120 ? msg.text.substring(0, 120) + '…' : msg.text}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ── Answer Area ──────────────────────────────────────────────────── */}
            <div
                className="rounded-3xl border overflow-hidden
                    bg-[#131C2E] transition-all duration-300
                    shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]"
                style={{
                    borderColor: isRecording
                        ? 'rgba(239,68,68,0.35)'
                        : answer.length > 10
                            ? 'rgba(139,92,246,0.2)'
                            : 'rgba(255,255,255,0.06)',
                    boxShadow: isRecording
                        ? '0 0 0 1px rgba(239,68,68,0.15), inset 0 1px 0 rgba(255,255,255,0.03)'
                        : answer.length > 10
                            ? '0 0 20px rgba(139,92,246,0.08), inset 0 1px 0 rgba(255,255,255,0.03)'
                            : 'inset 0 1px 0 rgba(255,255,255,0.03)',
                }}
            >
                {/* Answer header */}
                <div className="flex items-center justify-between px-5 pt-4 pb-3
                    border-b border-white/[0.04]">
                    <p className="text-[10px] font-black text-slate-600 uppercase tracking-[0.16em]">
                        Your Answer
                    </p>
                    <div className="flex items-center gap-3">
                        {/* Authenticity indicator */}
                        {authenticityStatus !== 'analyzing' && (
                            <div className={`flex items-center gap-1.5 text-[10px] font-black
                                ${authenticityStatus === 'genuine' ? 'text-emerald-500' : 'text-yellow-500'}`}>
                                <span className={`w-1.5 h-1.5 rounded-full
                                    ${authenticityStatus === 'genuine' ? 'bg-emerald-500' : 'bg-yellow-500 animate-pulse'}`}
                                />
                                {authenticityStatus === 'genuine' ? 'Genuine' : 'Suspicious'}
                            </div>
                        )}
                        {/* Word count pill */}
                        <div className={`text-[10px] font-black tabular-nums ${wordCountColor}`}>
                            {wordCount}w
                        </div>
                    </div>
                </div>

                {/* Textarea */}
                <div className="relative">
                    <textarea
                        value={answer}
                        onChange={handleAnswerChange}
                        onPaste={handlePaste}
                        onContextMenu={(e) => { e.preventDefault(); handlePaste(e as any) }}
                        placeholder="Type your answer here..."
                        aria-label="Your answer"
                        className="w-full bg-transparent px-5 py-5 text-white
                            text-[0.95rem] font-medium leading-[1.7]
                            outline-none min-h-[180px] resize-none
                            placeholder:text-slate-700 placeholder:font-normal
                            transition-all duration-200"
                    />

                    {/* Recording overlay */}
                    <AnimatePresence>
                        {isRecording && (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="absolute inset-0 pointer-events-none flex items-end justify-center pb-6"
                            >
                                {/* Pulsing waveform dots */}
                                <div className="flex items-center gap-1 px-4 py-2
                                    bg-red-500/10 border border-red-500/20 rounded-full backdrop-blur-sm">
                                    {[0.3, 0.5, 0.7, 0.5, 0.3].map((delay, i) => (
                                        <motion.div
                                            key={i}
                                            className="w-1 bg-red-400 rounded-full"
                                            animate={{ height: ['4px', '14px', '4px'] }}
                                            transition={{ duration: 0.6, repeat: Infinity, delay, ease: 'easeInOut' }}
                                        />
                                    ))}
                                    <span className="text-[10px] font-black text-red-400 uppercase tracking-widest ml-2">
                                        Recording
                                    </span>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                {/* Comm score strip */}
                <AnimatePresence>
                    {!simMode && usedVoiceInput && commScore && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                        >
                            <div className="flex items-center justify-between px-5 py-3
                                border-t border-white/[0.04]">
                                <div className="flex items-center gap-2">
                                    <span className="text-sm">🎙️</span>
                                    <p className="text-[11px] font-medium text-slate-500">{commScore.tip}</p>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <span className="text-[10px] font-black text-slate-600 uppercase tracking-widest">
                                        Comm
                                    </span>
                                    <span className="text-sm font-black text-purple-400">
                                        {commScore.score}
                                    </span>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Action bar */}
                <div className="flex items-center justify-between px-5 py-4
                    border-t border-white/[0.04] gap-3">

                    {/* Left: voice + hint */}
                    <div className="flex gap-2">
                        <ActionPill
                            onClick={toggleVoice}
                            active={isRecording}
                            activeClass="bg-red-500/15 border-red-500/40 text-red-400"
                        >
                            {isRecording
                                ? <Square className="w-3.5 h-3.5" />
                                : <Mic className="w-3.5 h-3.5" />
                            }
                            {isRecording ? 'Stop' : 'Voice'}
                        </ActionPill>

                        {!simMode && (
                            <ActionPill
                                onClick={toggleCoachingHint}
                                active={showCoachingHint}
                            >
                                <Lightbulb className="w-3.5 h-3.5" />
                                Hint
                            </ActionPill>
                        )}
                    </div>

                    {/* Submit — mirrors SetupScreen CTA design */}
                    <button
                        onClick={handleSubmit}
                        disabled={submitting || !answer.trim()}
                        className="relative flex items-center gap-2 px-7 py-3 rounded-2xl
                            font-black text-white text-[13px] uppercase tracking-widest
                            transition-all duration-200 overflow-hidden
                            hover:scale-[1.02] active:scale-[0.97]
                            disabled:opacity-35 disabled:cursor-not-allowed disabled:scale-100
                            focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:ring-offset-2
                            focus:ring-offset-[#131C2E] group"
                    >
                        {/* Base gradient */}
                        <span className="absolute inset-0 bg-gradient-to-r from-purple-600 to-violet-600" />
                        {/* Hover glow */}
                        <span className="absolute inset-0 opacity-0 group-hover:opacity-100
                            transition-opacity duration-300
                            bg-gradient-to-r from-purple-500 to-violet-500" />
                        {/* Top highlight */}
                        <span className="absolute inset-x-0 top-0 h-px
                            bg-gradient-to-r from-transparent via-white/20 to-transparent" />

                        <span className="relative z-10 flex items-center gap-2">
                            {submitting ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <>
                                    Submit Answer
                                    <ArrowRight className="w-3.5 h-3.5 opacity-70
                                        group-hover:translate-x-0.5 transition-transform" />
                                </>
                            )}
                        </span>
                    </button>
                </div>
            </div>

            {/* ── Subtle word count guidance ───────────────────────────────────── */}
            <AnimatePresence>
                {wordCount > 0 && wordCount < 30 && (
                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="text-center text-[11px] text-slate-700 font-medium"
                    >
                        Aim for at least 50 words for a strong answer
                    </motion.p>
                )}
            </AnimatePresence>

        </motion.div>
    )
}