'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { supabase } from '@/lib/supabase'
import { toast } from 'sonner'
import {
    Brain, Loader2, Lightbulb, Mic, Square,
    Volume2, Sparkles, Clock, Zap, ChevronRight
} from 'lucide-react'
import AICoachPanel from './AICoachPanel'
import type { Question, AuthenticityStatus } from '../hooks/useInterviewSession'
import type { VoiceStatus, CommScore } from '../hooks/useVoiceInput'

// ─── Types ────────────────────────────────────────────────────────────────────

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

// ─── Coaching hint fetch ──────────────────────────────────────────────────────

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

function getPersonaConfig(aiLabel: string) {
    switch (aiLabel) {
        case 'FAANG Interviewer':
            return { initials: 'FA', color: 'bg-orange-500/20 text-orange-400 border-orange-500/30', label: aiLabel }
        case 'Technical Interviewer':
            return { initials: 'TI', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', label: aiLabel }
        default:
            return { initials: 'AI', color: 'bg-purple-500/20 text-purple-400 border-purple-500/30', label: 'AI Coach' }
    }
}

// ─── Component ────────────────────────────────────────────────────────────────

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

    const [showCoachingHint, setShowCoachingHint] = useState(false)
    const [coachingHint, setCoachingHint] = useState<CoachingHint | null>(null)
    const [hintLoading, setHintLoading] = useState(false)
    const [showAICoachPanel, setShowAICoachPanel] = useState(false)
    const [showHistory, setShowHistory] = useState(false)

    const q = questions[currentQuestion]
    const persona = getPersonaConfig(getAiLabel())

    // Reset coaching hint on question change
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

    const modeLabel =
        interviewMode === 'hr' ? 'HR Round' :
            interviewMode === 'system_design' ? 'System Design' :
                'Technical Round'

    const wordCount = answer.trim() ? answer.trim().split(/\s+/).length : 0

    return (
        <motion.div
            key="interview"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="max-w-3xl mx-auto space-y-5"
        >

            {/* ── Top bar ──────────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between gap-3">
                {/* Left: question counter + mode */}
                <div className="flex items-center gap-2">
                    <span className="text-xs font-black text-white uppercase tracking-widest">
                        {currentQuestion + 1}
                        <span className="text-slate-500"> / {questions.length}</span>
                    </span>
                    <span className="w-1 h-1 rounded-full bg-slate-600" />
                    <span className="text-xs font-bold text-slate-400">{modeLabel}</span>
                    {simMode && (
                        <span className="flex items-center gap-1 px-2 py-0.5 bg-orange-500/15 rounded-full text-[10px] font-black text-orange-400 uppercase tracking-widest">
                            <Zap className="w-2.5 h-2.5" /> Timed
                        </span>
                    )}
                </div>

                {/* Right: timer + coach toggle */}
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 text-slate-400">
                        <Clock className="w-3.5 h-3.5" />
                        <span className="text-xs font-bold tabular-nums">{formatTime(elapsedTime)}</span>
                    </div>
                    <button
                        onClick={() => setShowAICoachPanel(!showAICoachPanel)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest transition-all ${showAICoachPanel
                            ? 'bg-purple-600 text-white'
                            : 'bg-[#1E293B] text-slate-400 border border-white/5 hover:border-white/15'
                            }`}
                    >
                        <Brain className="w-3 h-3" /> Coach
                    </button>
                </div>
            </div>

            {/* ── Progress bar ─────────────────────────────────────────────────── */}
            <div className="flex gap-1">
                {questions.map((_, i) => (
                    <div
                        key={i}
                        className={`h-1 flex-1 rounded-full transition-all duration-500 ${i < currentQuestion ? 'bg-purple-600' :
                            i === currentQuestion ? 'bg-purple-400' :
                                'bg-slate-800'
                            }`}
                    />
                ))}
            </div>

            {/* ── Simulation countdown ─────────────────────────────────────────── */}
            {simMode && (
                <div className="flex items-center gap-4 px-5 py-3 bg-[#1E293B] rounded-2xl border border-white/5">
                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-500 flex-shrink-0">
                        Time left
                    </span>
                    <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <motion.div
                            animate={{ width: barWidth }}
                            className={`h-full rounded-full transition-colors duration-300 ${barColor}`}
                        />
                    </div>
                    <span className={`text-base font-black tabular-nums flex-shrink-0 ${timerColor} ${isUrgent ? 'animate-pulse' : ''}`}>
                        {formatTime(simTimeLeft)}
                    </span>
                </div>
            )}

            {/* ── Interviewer question card ────────────────────────────────────── */}
            <div className="bg-[#1E293B] rounded-3xl border border-white/5 overflow-hidden">

                {/* Interviewer identity strip */}
                <div className="flex items-center gap-3 px-6 pt-5 pb-4 border-b border-white/5">
                    <div className={`w-9 h-9 rounded-xl border flex items-center justify-center text-xs font-black flex-shrink-0 ${persona.color}`}>
                        {persona.initials}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-xs font-black text-white">{persona.label}</p>
                        <p className="text-[10px] text-slate-500 font-medium">{careerPath}</p>
                    </div>
                    <div className="flex items-center gap-2">
                        {speechSupported && (
                            <button
                                onClick={speakQuestion}
                                aria-label="Read question aloud"
                                className={`p-2 rounded-lg transition-all ${isSpeaking
                                    ? 'bg-purple-600 text-white'
                                    : 'text-slate-500 hover:text-white hover:bg-white/5'
                                    }`}
                            >
                                <Volume2 className="w-4 h-4" />
                            </button>
                        )}
                        <span className="px-2 py-1 bg-slate-800 rounded-lg text-[10px] font-black text-slate-400 uppercase tracking-widest">
                            {q.type}
                        </span>
                    </div>
                </div>

                {/* Question text — single, clean, right-sized */}
                <div className="px-6 py-5">
                    <p className="text-lg font-bold text-white leading-relaxed">
                        {q.question}
                    </p>
                </div>

                {/* Coaching hint */}
                <AnimatePresence>
                    {!simMode && showCoachingHint && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                        >
                            <div className="mx-6 mb-5 p-5 bg-[#0F172A] rounded-2xl border border-purple-500/20 space-y-4">
                                {hintLoading ? (
                                    <div className="flex items-center gap-3 text-slate-400 text-sm">
                                        <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                                        Getting strategy...
                                    </div>
                                ) : coachingHint ? (
                                    <>
                                        <div className="flex items-center gap-2">
                                            <Sparkles className="w-4 h-4 text-purple-400" />
                                            <span className="text-xs font-black text-purple-400 uppercase tracking-widest">
                                                Strategy hint
                                            </span>
                                        </div>
                                        <div className="space-y-3">
                                            <div>
                                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">
                                                    What they want to hear
                                                </p>
                                                <p className="text-sm text-slate-200 leading-relaxed">{coachingHint.looking_for}</p>
                                            </div>
                                            <div>
                                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">
                                                    Best structure
                                                </p>
                                                <p className="text-sm text-slate-300 italic">"{coachingHint.structure}"</p>
                                            </div>
                                            {coachingHint.example && (
                                                <div>
                                                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">
                                                        Direction
                                                    </p>
                                                    <p className="text-sm text-slate-400">{coachingHint.example}</p>
                                                </div>
                                            )}
                                        </div>
                                    </>
                                ) : null}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* AI Coach panel */}
                <AnimatePresence>
                    {showAICoachPanel && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                        >
                            <div className="mx-6 mb-5">
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

            {/* ── Past responses (collapsible) ─────────────────────────────────── */}
            {messages.length > 2 && (
                <button
                    onClick={() => setShowHistory(!showHistory)}
                    className="flex items-center gap-2 text-[11px] text-slate-500 hover:text-slate-300 transition-colors font-bold"
                >
                    <ChevronRight className={`w-3.5 h-3.5 transition-transform ${showHistory ? 'rotate-90' : ''}`} />
                    {showHistory ? 'Hide' : 'Show'} conversation history ({Math.floor(messages.length / 2)} answered)
                </button>
            )}

            <AnimatePresence>
                {showHistory && messages.length > 2 && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                    >
                        <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                            {messages.slice(0, -1).map((msg, idx) => (
                                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`max-w-[82%] rounded-xl px-4 py-3 text-sm ${msg.role === 'ai'
                                        ? 'bg-[#1E293B] text-slate-400 border border-white/5'
                                        : 'bg-purple-500/10 text-slate-300 border border-purple-500/20'
                                        }`}>
                                        {msg.text.length > 120 ? msg.text.substring(0, 120) + '…' : msg.text}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ── Answer area ──────────────────────────────────────────────────── */}
            <div className="bg-[#1E293B] rounded-3xl border border-white/5 overflow-hidden">
                <div className="flex items-center justify-between px-5 pt-4 pb-3 border-b border-white/5">
                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
                        Your answer
                    </p>
                    <div className="flex items-center gap-3">
                        {/* Authenticity dot */}
                        {authenticityStatus !== 'analyzing' && (
                            <span className={`flex items-center gap-1.5 text-[10px] font-black ${authenticityStatus === 'genuine' ? 'text-green-400' : 'text-yellow-400'
                                }`}>
                                <span className={`w-1.5 h-1.5 rounded-full ${authenticityStatus === 'genuine' ? 'bg-green-400' : 'bg-yellow-400'
                                    }`} />
                                {authenticityStatus === 'genuine' ? 'Genuine' : 'Suspicious'}
                            </span>
                        )}
                        {/* Word count */}
                        <span className={`text-[10px] font-bold tabular-nums ${wordCount < 30 ? 'text-slate-600' :
                            wordCount < 80 ? 'text-yellow-500' :
                                'text-green-500'
                            }`}>
                            {wordCount} words
                        </span>
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
                        className="w-full bg-transparent px-5 py-4 text-white text-base font-medium leading-relaxed outline-none min-h-[180px] resize-none placeholder:text-slate-700"
                    />
                    {isRecording && (
                        <div className="absolute inset-0 bg-red-500/5 border-2 border-dashed border-red-500/30 rounded-b-3xl flex items-center justify-center pointer-events-none">
                            <div className="flex items-center gap-2 px-4 py-2 bg-red-500/20 rounded-full">
                                <div className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
                                <span className="text-xs font-black text-red-400 uppercase tracking-widest">
                                    Recording...
                                </span>
                            </div>
                        </div>
                    )}
                </div>

                {/* Communication score */}
                <AnimatePresence>
                    {!simMode && usedVoiceInput && commScore && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            className="px-5 pb-3 overflow-hidden"
                        >
                            <div className="flex items-center justify-between py-3 border-t border-white/5">
                                <div className="flex items-center gap-2">
                                    <span className="text-sm">🎙️</span>
                                    <p className="text-xs font-bold text-slate-400">{commScore.tip}</p>
                                </div>
                                <span className="text-sm font-black text-purple-400">
                                    Comm: {commScore.score}
                                </span>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Action bar */}
                <div className="flex items-center justify-between px-5 py-4 border-t border-white/5 gap-3">
                    <div className="flex gap-2">
                        {/* Voice */}
                        <button
                            onClick={toggleVoice}
                            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-black uppercase tracking-widest text-[11px] transition-all border ${isRecording
                                ? 'bg-red-500/15 border-red-500/40 text-red-400 animate-pulse'
                                : 'bg-transparent border-white/10 text-slate-500 hover:text-white hover:border-white/20'
                                }`}
                        >
                            {isRecording ? <Square className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />}
                            {isRecording ? 'Stop' : 'Voice'}
                        </button>

                        {/* Hint (practice only) */}
                        {!simMode && (
                            <button
                                onClick={toggleCoachingHint}
                                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-black uppercase tracking-widest text-[11px] transition-all border ${showCoachingHint
                                    ? 'bg-purple-600 border-purple-600 text-white'
                                    : 'bg-transparent border-white/10 text-slate-500 hover:text-white hover:border-white/20'
                                    }`}
                            >
                                <Lightbulb className="w-3.5 h-3.5" /> Hint
                            </button>
                        )}
                    </div>

                    {/* Submit */}
                    <Button
                        onClick={handleSubmit}
                        disabled={submitting || !answer.trim()}
                        className="bg-purple-600 hover:bg-purple-700 px-8 py-5 font-black uppercase tracking-widest text-sm rounded-2xl transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed disabled:scale-100 disabled:hover:bg-purple-600"
                    >
                        {submitting
                            ? <Loader2 className="w-5 h-5 animate-spin" />
                            : 'Submit Answer →'
                        }
                    </Button>
                </div>
            </div>

            {/* ── Word count guidance ───────────────────────────────────────────── */}
            {wordCount > 0 && wordCount < 30 && (
                <p className="text-center text-[11px] text-slate-600 font-medium">
                    Aim for at least 50 words for a strong answer
                </p>
            )}

        </motion.div>
    )
}