'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { supabase } from '@/lib/supabase'
import { toast } from 'sonner'

// ─── Exported Types ───────────────────────────────────────────────────────────

export interface Question {
    id: number
    question: string
    type: string
    difficulty: string
    hint: string
}

export interface AnswerFeedback {
    score: number
    good_points: string[]
    missing_points: string[]
    model_answer: string
    tip: string
}

export interface Answer {
    question: string
    answer: string
    feedback: AnswerFeedback
}

export type ScreenState = 'setup' | 'interview' | 'results'
export type InterviewMode = 'hr' | 'technical' | 'system_design'
export type AuthenticityStatus = 'analyzing' | 'genuine' | 'suspicious'

export interface StreakData {
    current_streak: number
    longest_streak: number
    last_practice_date: string | null
    total_sessions: number
}

export interface RankData {
    xp: number
    level: number
    rank_title: string
    next_level_xp: number
    progress_percent: number
}

export interface ChatMessage {
    role: 'ai' | 'user'
    text: string
}

interface UseInterviewSessionProps {
    user: { id: string } | null
    isWeeklyMode?: boolean
    resumeData?: any | null
    onSaveProgress?: (state: any) => void
    onClearProgress?: () => void
}

// ─── Transition message pools (outside hook — no re-creation) ─────────────────

const HR_MESSAGES = [
    'Tell me more about your experience.',
    'How did you handle that situation?',
    'Can you elaborate on your role?',
]
const TECHNICAL_MESSAGES = [
    'Explain the logic clearly.',
    'Be precise.',
    'What is the complexity?',
]
const SYSTEM_DESIGN_MESSAGES = [
    'Design perspective: Think about scalability.',
    'How would this work at scale?',
    'Consider architecture decisions.',
]
const FRIENDLY_MESSAGES = [
    "That's a great start!",
    "Nice! Let's explore more.",
    "You're doing well, next question...",
]
const STRICT_MESSAGES = [
    'Be more precise.',
    "That's vague. Clarify.",
    'Focus on technical depth.',
]
const FAANG_MESSAGES = [
    "That's not strong enough.",
    'You need a better answer.',
    "Let's push deeper.",
]

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useInterviewSession({
    user,
    isWeeklyMode = false,
    resumeData = null,
    onSaveProgress,
    onClearProgress,
}: UseInterviewSessionProps) {

    // ── Screen ──────────────────────────────────────────────────────────────────
    const [screen, setScreen] = useState<ScreenState>('setup')

    // ── Setup config ────────────────────────────────────────────────────────────
    const [careerPath, setCareerPath] = useState('Full Stack Developer')
    const [difficulty, setDifficulty] = useState('medium')
    const [personality, setPersonality] = useState('friendly')
    const [interviewMode, setInterviewMode] = useState<InterviewMode>('technical')
    const [simMode, setSimMode] = useState(false)
    const [careerPaths, setCareerPaths] = useState<string[]>([])
    const [pastSessions, setPastSessions] = useState(0)

    // ── Interview core ──────────────────────────────────────────────────────────
    const [questions, setQuestions] = useState<Question[]>([])
    const [currentQuestion, setCurrentQuestion] = useState(0)
    const [answer, setAnswer] = useState('')
    const [answers, setAnswers] = useState<Answer[]>([])
    const [submitting, setSubmitting] = useState(false)
    const [elapsedTime, setElapsedTime] = useState(0)
    const [messages, setMessages] = useState<ChatMessage[]>([])
    const [showingTransition, setShowingTransition] = useState(false)

    // Refs — don't trigger re-renders
    const timerRef = useRef<NodeJS.Timeout | null>(null)
    const finishingRef = useRef(false)  // prevents double session save
    const elapsedRef = useRef(0)       // shadow of elapsedTime for use inside callbacks

    // ── Post-session ────────────────────────────────────────────────────────────
    const [totalScore, setTotalScore] = useState(0)
    const [streakData, setStreakData] = useState<StreakData | null>(null)
    const [streakMessage, setStreakMessage] = useState<string | null>(null)
    const [rankData, setRankData] = useState<RankData | null>(null)
    const [xpEarned, setXpEarned] = useState<number | null>(null)
    const [leveledUp, setLeveledUp] = useState(false)
    const [newBadge, setNewBadge] = useState<{ emoji: string; name: string } | null>(null)

    // Weekly challenge
    const [challengeRank, setChallengeRank] = useState<number | null>(null)
    const [challengeLeaderboard, setChallengeLeaderboard] = useState<{ rank: number; user_email: string; score: number }[]>([])
    const [challengeTotalParticipants, setChallengeTotalParticipants] = useState(0)

    // ── Anti-cheat ──────────────────────────────────────────────────────────────
    const [pasteAttempted, setPasteAttempted] = useState(false)
    const [authenticityStatus, setAuthenticityStatus] = useState<AuthenticityStatus>('analyzing')
    const [typingBehavior, setTypingBehavior] = useState<{
        startTime: number | null
        keystrokes: number
        typingDuration: number
    }>({ startTime: null, keystrokes: 0, typingDuration: 0 })

    // ── Helpers ──────────────────────────────────────────────────────────────────

    const getAuthHeaders = async () => {
        const { data: { session } } = await supabase.auth.getSession()
        return {
            'Content-Type': 'application/json',
            ...(session?.access_token
                ? { Authorization: `Bearer ${session.access_token}` }
                : {}),
        }
    }

    const formatTime = (seconds: number) => {
        const m = Math.floor(seconds / 60)
        const s = seconds % 60
        return `${m}:${s.toString().padStart(2, '0')}`
    }

    const getScoreColor = (score: number) => {
        if (score >= 8) return 'text-green-400 bg-green-500/10 border-green-500/20'
        if (score >= 5) return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20'
        return 'text-red-400 bg-red-500/10 border-red-500/20'
    }

    const getPerformanceRating = (score: number) => {
        const pct = (score / 50) * 100
        if (pct >= 80) return 'Elite Performance'
        if (pct >= 60) return 'Strong Contender'
        return 'Growth Phase'
    }

    const getAiLabel = useCallback(() => {
        switch (personality) {
            case 'strict': return 'Technical Interviewer'
            case 'google': return 'FAANG Interviewer'
            default: return 'AI Coach'
        }
    }, [personality])

    const getRandomTransitionMessage = useCallback(() => {
        const modePool =
            interviewMode === 'hr' ? HR_MESSAGES :
                interviewMode === 'system_design' ? SYSTEM_DESIGN_MESSAGES :
                    TECHNICAL_MESSAGES

        const tonePool =
            personality === 'strict' ? STRICT_MESSAGES :
                personality === 'google' ? FAANG_MESSAGES :
                    FRIENDLY_MESSAGES

        const pool = Math.random() > 0.5 ? modePool : tonePool
        return pool[Math.floor(Math.random() * pool.length)]
    }, [interviewMode, personality])

    // ── Init: load user data ────────────────────────────────────────────────────

    const loadUserData = useCallback(async (userId: string) => {
        try {
            const { data: analysisData } = await supabase
                .from('analyses')
                .select('career_paths')
                .eq('user_id', userId)
                .single()

            if (analysisData?.career_paths) {
                const paths = analysisData.career_paths
                    .map((p: any) => p.name || p.career_name)
                    .filter(Boolean)
                setCareerPaths(paths)
                if (paths.length > 0) setCareerPath(paths[0])
            }

            const { count } = await supabase
                .from('interview_sessions')
                .select('*', { count: 'exact', head: true })
                .eq('user_id', userId)
            setPastSessions(count || 0)
        } catch (err) {
            console.error('Error loading user data:', err)
        }
    }, [])

    useEffect(() => {
        if (user) loadUserData(user.id)
    }, [user, loadUserData])

    // Keep elapsedRef in sync for use inside callbacks without stale closure
    useEffect(() => {
        elapsedRef.current = elapsedTime
    }, [elapsedTime])

    // Cleanup timer on unmount
    useEffect(() => {
        return () => {
            if (timerRef.current) clearInterval(timerRef.current)
        }
    }, [])

    // ── Core: evaluate answer and advance ──────────────────────────────────────
    // All parameters passed explicitly → no stale closure risk

    const evaluateAndAdvance = useCallback(async (
        currentIndex: number,
        currentAnswer: string,
        currentQuestions: Question[],
        currentAnswers: Answer[],
    ) => {
        if (!user) return

        try {
            const headers = await getAuthHeaders()
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

            const res = await fetch(`${apiUrl}/api/v1/interview/evaluate-answer`, {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    question: currentQuestions[currentIndex].question,
                    answer: currentAnswer,
                    career_path: careerPath,
                    user_id: user.id,
                }),
            })

            if (!res.ok) throw new Error(`Server error: ${res.status}`)
            const feedback = await res.json()

            if (feedback.success === false || feedback.error) {
                toast.error(feedback.message || 'Failed to evaluate answer.')
                return
            }

            const newAnswer: Answer = {
                question: currentQuestions[currentIndex].question,
                answer: currentAnswer,
                feedback,
            }
            const updatedAnswers = [...currentAnswers, newAnswer]
            setAnswers(updatedAnswers)

            // Save weekly challenge progress
            if (isWeeklyMode) {
                onSaveProgress?.({
                    currentQuestion: currentIndex,
                    answers: updatedAnswers,
                    elapsedTime: elapsedRef.current,
                })
            }

            // Add user message to chat
            setMessages(prev => [...prev, { role: 'user', text: currentAnswer }])

            const nextIndex = currentIndex + 1
            const isLast = nextIndex >= currentQuestions.length

            if (!isLast) {
                // Transition message → next question
                const transition = getRandomTransitionMessage()
                setShowingTransition(true)
                setMessages(prev => [...prev, { role: 'ai', text: transition }])

                setTimeout(() => {
                    setShowingTransition(false)
                    setCurrentQuestion(nextIndex)
                    setMessages(prev => [
                        ...prev,
                        { role: 'ai', text: currentQuestions[nextIndex].question },
                    ])
                    setAnswer('')
                    setTypingBehavior({ startTime: null, keystrokes: 0, typingDuration: 0 })
                    setAuthenticityStatus('analyzing')
                }, 500)
            } else {
                // Last question — finish
                await finishInterview(updatedAnswers, currentQuestions)
            }
        } catch (err) {
            console.error('Error evaluating answer:', err)
            toast.error('Failed to submit answer. Please try again.')
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [user, careerPath, isWeeklyMode, onSaveProgress, getRandomTransitionMessage])

    // ── Submit Answer ───────────────────────────────────────────────────────────

    const submitAnswer = useCallback(async () => {
        if (!user || !answer.trim() || submitting) return
        setSubmitting(true)

        // Anti-cheat: classify answer authenticity
        if (typingBehavior.startTime) {
            const duration = Date.now() - typingBehavior.startTime
            const len = answer.trim().length
            const keystrokesPerChar = len > 0 ? typingBehavior.keystrokes / len : 0
            const isTooFast = duration < 5000 && len > 50
            const isLowKeystrokes = keystrokesPerChar < 0.3 && len > 100
            setAuthenticityStatus(isTooFast || isLowKeystrokes ? 'suspicious' : 'genuine')
        }

        await evaluateAndAdvance(currentQuestion, answer, questions, answers)
        setSubmitting(false)
    }, [user, answer, submitting, typingBehavior, currentQuestion, questions, answers, evaluateAndAdvance])

    // ── Handle Time Up (simulation mode) ───────────────────────────────────────

    const handleTimeUp = useCallback(async () => {
        if (submitting) return
        setSubmitting(true)
        const timedOutAnswer = answer.trim() || '(No answer provided — time expired)'
        await evaluateAndAdvance(currentQuestion, timedOutAnswer, questions, answers)
        setSubmitting(false)
    }, [submitting, answer, currentQuestion, questions, answers, evaluateAndAdvance])

    // ── Finish Interview ────────────────────────────────────────────────────────

    const finishInterview = useCallback(async (
        finalAnswers: Answer[],
        finalQuestions: Question[],
    ) => {
        // Guard: prevent double save if submitAnswer + timer both fire
        if (finishingRef.current) return
        finishingRef.current = true

        // Stop elapsed timer
        if (timerRef.current) {
            clearInterval(timerRef.current)
            timerRef.current = null
        }

        const total = finalAnswers.reduce((sum, a) => sum + (a.feedback?.score || 0), 0)
        setTotalScore(total)

        try {
            const headers = await getAuthHeaders()
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

            // 1. Save session
            const sessionRes = await fetch(`${apiUrl}/api/v1/interview/save-session`, {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    user_id: user!.id,
                    career_path: careerPath,
                    questions: finalQuestions.map(q => q.question),
                    answers: finalAnswers.map(a => ({ question: a.question, answer: a.answer })),
                    scores: finalAnswers.map(a => a.feedback?.score || 0),
                    total_score: total,
                    difficulty,
                    interview_mode: interviewMode,
                    is_simulation: simMode,
                    is_voice: false,
                }),
            })
            const sessionData = await sessionRes.json()

            // Badge toasts
            if (sessionData.new_badges?.length > 0) {
                sessionData.new_badges.forEach((badge: { name: string; emoji: string; description: string }) => {
                    toast.success(`🎖️ Badge Unlocked: ${badge.name}!`, {
                        description: badge.description,
                        duration: 5000,
                    })
                    setNewBadge({ emoji: badge.emoji, name: badge.name })
                })
            }
            if (sessionData.total_xp_earned > 0) {
                toast.info(`✨ +${sessionData.total_xp_earned} XP earned!`)
            }

            // 2. Update streak
            const streakRes = await fetch(`${apiUrl}/api/v1/streaks/update`, {
                method: 'POST',
                headers,
                body: JSON.stringify({ user_id: user!.id }),
            })
            if (streakRes.ok) {
                const s = await streakRes.json()
                setStreakData({
                    current_streak: s.current_streak,
                    longest_streak: s.longest_streak,
                    last_practice_date: s.last_practice_date,
                    total_sessions: s.total_sessions,
                })
                setStreakMessage(s.message)
            }

            // 3. Update rank
            const rankRes = await fetch(`${apiUrl}/api/v1/ranks/update`, {
                method: 'POST',
                headers,
                body: JSON.stringify({ user_id: user!.id, score: total }),
            })
            if (rankRes.ok) {
                const r = await rankRes.json()
                setRankData({
                    xp: r.xp,
                    level: r.level,
                    rank_title: r.rank_title,
                    next_level_xp: r.next_level_xp,
                    progress_percent: ((r.xp % 100) / 100) * 100,
                })
                setXpEarned(r.xp_earned)
                setLeveledUp(r.leveled_up)
            }

            // 4. Weekly challenge leaderboard (non-critical)
            if (isWeeklyMode) {
                onClearProgress?.()
                try {
                    const lbRes = await fetch(`${apiUrl}/api/v1/weekly-challenge/leaderboard`)
                    if (lbRes.ok) {
                        const lb = await lbRes.json()
                        setChallengeLeaderboard(lb)
                        setChallengeTotalParticipants(lb.length)
                        const { data: { user: authUser } } = await supabase.auth.getUser()
                        const entry = lb.find((e: any) => e.user_email === authUser?.email)
                        if (entry) setChallengeRank(entry.rank)
                    }
                } catch { /* leaderboard non-critical — don't block results screen */ }
            }
        } catch (err) {
            console.error('Error finishing interview:', err)
            // Still show results even if save fails
        }

        setScreen('results')
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [user, careerPath, difficulty, interviewMode, simMode, isWeeklyMode, onClearProgress])

    // ── Start Interview ─────────────────────────────────────────────────────────

    const startInterview = useCallback(async () => {
        if (!user) return

        try {
            const headers = await getAuthHeaders()
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

            const res = await fetch(`${apiUrl}/api/v1/interview/generate-questions`, {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    user_id: user.id,
                    career_path: careerPath,
                    difficulty,
                    personality,
                    interview_mode: interviewMode,
                }),
            })

            if (!res.ok) throw new Error(`Server error: ${res.status}`)
            const data = await res.json()

            if (!data.questions?.length) throw new Error('No questions returned')

            setQuestions(data.questions)
            finishingRef.current = false  // reset guard for new session

            // Resume weekly challenge or start fresh
            if (isWeeklyMode && resumeData) {
                const idx = resumeData.currentQuestion || 0
                setCurrentQuestion(idx)
                setAnswers(
                    (resumeData.answers || []).map((a: any) => ({
                        question: a.question,
                        answer: a.answer,
                        feedback: { score: 0, good_points: [], missing_points: [], model_answer: '', tip: '' },
                    }))
                )
                setElapsedTime(resumeData.elapsedTime || 0)
                setMessages([{
                    role: 'ai',
                    text: data.questions[idx]?.question || data.questions[0].question,
                }])
            } else {
                setCurrentQuestion(0)
                setAnswers([])
                setElapsedTime(0)
                setMessages([{ role: 'ai', text: data.questions[0].question }])
            }

            setAnswer('')
            setScreen('interview')

            // Start elapsed timer
            if (timerRef.current) clearInterval(timerRef.current)
            timerRef.current = setInterval(() => {
                setElapsedTime(prev => prev + 1)
            }, 1000)

        } catch (err) {
            console.error('Error starting interview:', err)
            toast.error('Failed to start interview. Please try again.')
        }
    }, [user, careerPath, difficulty, personality, interviewMode, isWeeklyMode, resumeData])

    // ── Return ──────────────────────────────────────────────────────────────────

    return {
        // Screen
        screen, setScreen,

        // Setup config — used by SetupScreen
        careerPath, setCareerPath,
        difficulty, setDifficulty,
        personality, setPersonality,
        interviewMode, setInterviewMode,
        simMode, setSimMode,
        careerPaths,
        pastSessions,

        // Interview state — used by InterviewScreen
        questions,
        currentQuestion,
        answer, setAnswer,
        answers,
        submitting,
        elapsedTime,
        messages,
        showingTransition,

        // Post-session — used by ResultsScreen
        totalScore,
        streakData, streakMessage,
        rankData, xpEarned, leveledUp, newBadge,
        challengeRank, challengeLeaderboard, challengeTotalParticipants,

        // Anti-cheat — used by InterviewScreen
        pasteAttempted, setPasteAttempted,
        typingBehavior, setTypingBehavior,
        authenticityStatus, setAuthenticityStatus,

        // Actions
        startInterview,
        submitAnswer,
        handleTimeUp,

        // Pure helpers — used by multiple screens
        formatTime,
        getScoreColor,
        getPerformanceRating,
        getAiLabel,
    }
}