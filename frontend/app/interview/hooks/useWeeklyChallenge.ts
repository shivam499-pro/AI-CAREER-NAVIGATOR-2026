'use client'

import { useState, useEffect, useCallback } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ChallengeProgress {
    currentQuestion: number
    answers: { question: string; answer: string }[]
    elapsedTime: number
    timestamp: number
}

interface UseWeeklyChallengeProps {
    userId: string | undefined
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useWeeklyChallenge({ userId }: UseWeeklyChallengeProps) {

    // ── State ───────────────────────────────────────────────────────────────────
    const [isWeeklyMode, setIsWeeklyMode] = useState(false)
    const [weekNumber, setWeekNumber] = useState(0)
    const [year, setYear] = useState(new Date().getFullYear())
    const [showResumeModal, setShowResumeModal] = useState(false)
    const [resumeData, setResumeData] = useState<ChallengeProgress | null>(null)

    // ── Storage key ─────────────────────────────────────────────────────────────

    const getStorageKey = useCallback((): string | null => {
        if (!userId || !isWeeklyMode || !weekNumber) return null
        return `challenge_progress_${userId}_${weekNumber}_${year}`
    }, [userId, isWeeklyMode, weekNumber, year])

    // ── Detect weekly mode from URL params ──────────────────────────────────────

    useEffect(() => {
        if (typeof window === 'undefined') return

        const params = new URLSearchParams(window.location.search)
        const mode = params.get('mode')
        const weekParam = params.get('week_number')
        const yearParam = params.get('year')

        if (mode !== 'weekly') return

        setIsWeeklyMode(true)
        if (weekParam) setWeekNumber(parseInt(weekParam, 10))
        if (yearParam) setYear(parseInt(yearParam, 10))
    }, [])

    // ── Check for saved progress once weekly mode + userId are ready ─────────────

    useEffect(() => {
        if (!isWeeklyMode || !userId || !weekNumber) return

        const key = `challenge_progress_${userId}_${weekNumber}_${year}`
        try {
            const saved = localStorage.getItem(key)
            if (saved) {
                const parsed: ChallengeProgress = JSON.parse(saved)
                setResumeData(parsed)
                setShowResumeModal(true)
            }
        } catch {
            // Corrupted storage — ignore, start fresh
        }
    }, [isWeeklyMode, userId, weekNumber, year])

    // ── Save progress ────────────────────────────────────────────────────────────

    const saveProgress = useCallback((state: Omit<ChallengeProgress, 'timestamp'>) => {
        const key = getStorageKey()
        if (!key) return

        try {
            localStorage.setItem(key, JSON.stringify({
                ...state,
                timestamp: Date.now(),
            }))
        } catch {
            console.error('Failed to save challenge progress')
        }
    }, [getStorageKey])

    // ── Clear progress ───────────────────────────────────────────────────────────

    const clearProgress = useCallback(() => {
        const key = getStorageKey()
        if (!key) return

        try {
            localStorage.removeItem(key)
        } catch {
            console.error('Failed to clear challenge progress')
        }
    }, [getStorageKey])

    // ── Resume modal handlers ────────────────────────────────────────────────────

    // User chose to continue saved session
    const handleResumeConfirm = useCallback(() => {
        setShowResumeModal(false)
        // resumeData stays set — startInterview will pick it up
    }, [])

    // User chose to start fresh
    const handleStartFresh = useCallback(() => {
        setShowResumeModal(false)
        setResumeData(null)
        clearProgress()
    }, [clearProgress])

    // ── Return ──────────────────────────────────────────────────────────────────

    return {
        // Mode flags
        isWeeklyMode,
        weekNumber,
        year,

        // Resume modal
        showResumeModal,
        resumeData,
        handleResumeConfirm,
        handleStartFresh,

        // Progress management — passed to useInterviewSession
        saveProgress,
        clearProgress,
    }
}