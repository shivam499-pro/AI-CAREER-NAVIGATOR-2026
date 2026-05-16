'use client'

import { useState, useEffect, useRef, useCallback } from 'react'

// ─── Constants ────────────────────────────────────────────────────────────────

const DEFAULT_SECONDS = 120

// ─── Hook ─────────────────────────────────────────────────────────────────────

interface UseSimTimerProps {
    enabled: boolean          // true when simMode is on
    screen: string            // only runs on 'interview' screen
    currentQuestion: number   // resets timer when question changes
    onTimeUp: () => void      // calls handleTimeUp from useInterviewSession
}

export function useSimTimer({
    enabled,
    screen,
    currentQuestion,
    onTimeUp,
}: UseSimTimerProps) {

    const [timeLeft, setTimeLeft] = useState(DEFAULT_SECONDS)
    const [showTimeUpMsg, setShowTimeUpMsg] = useState(false)

    const timerRef = useRef<NodeJS.Timeout | null>(null)
    const onTimeUpRef = useRef(onTimeUp)
    const firedRef = useRef(false)   // prevents double-fire on same question

    // Keep onTimeUp ref fresh without re-triggering the effect
    useEffect(() => {
        onTimeUpRef.current = onTimeUp
    }, [onTimeUp])

    // ── Start / reset timer when question changes ────────────────────────────────

    useEffect(() => {
        // Clear any running timer first
        if (timerRef.current) {
            clearInterval(timerRef.current)
            timerRef.current = null
        }

        // Only run in sim mode on the interview screen
        if (!enabled || screen !== 'interview') return

        // Reset state for new question
        setTimeLeft(DEFAULT_SECONDS)
        setShowTimeUpMsg(false)
        firedRef.current = false

        timerRef.current = setInterval(() => {
            setTimeLeft(prev => {
                if (prev <= 1) {
                    // Clear the interval immediately
                    if (timerRef.current) {
                        clearInterval(timerRef.current)
                        timerRef.current = null
                    }

                    // Fire onTimeUp exactly once per question
                    if (!firedRef.current) {
                        firedRef.current = true
                        setShowTimeUpMsg(true)
                        onTimeUpRef.current()
                    }

                    return 0
                }
                return prev - 1
            })
        }, 1000)

        return () => {
            if (timerRef.current) {
                clearInterval(timerRef.current)
                timerRef.current = null
            }
        }
    }, [enabled, screen, currentQuestion])  // resets on every question change

    // ── Manual stop (called when user submits before time up) ────────────────────

    const stopTimer = useCallback(() => {
        if (timerRef.current) {
            clearInterval(timerRef.current)
            timerRef.current = null
        }
        setShowTimeUpMsg(false)
    }, [])

    // ── Derived: color based on time remaining ───────────────────────────────────

    const timerColor =
        timeLeft > 60 ? 'text-green-400' :
            timeLeft > 20 ? 'text-yellow-400' :
                'text-red-500'

    const barColor =
        timeLeft > 60 ? 'bg-green-500' :
            timeLeft > 20 ? 'bg-yellow-500' :
                'bg-red-500'

    const barWidth = `${(timeLeft / DEFAULT_SECONDS) * 100}%`

    const isUrgent = timeLeft <= 20 && timeLeft > 0

    return {
        timeLeft,
        showTimeUpMsg,
        timerColor,
        barColor,
        barWidth,
        isUrgent,
        stopTimer,
    }
}