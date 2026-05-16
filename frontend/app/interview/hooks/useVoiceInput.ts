'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { toast } from 'sonner'

// ─── Types ────────────────────────────────────────────────────────────────────

export type VoiceStatus = 'idle' | 'listening' | 'done'

export interface CommScore {
    score: number
    fillers: Record<string, number>
    tip: string
}

interface UseVoiceInputProps {
    onTranscript: (text: string) => void   // called when voice input produces text
    currentQuestion: string                 // spoken aloud on question change
    screen: string                          // only speak on 'interview' screen
}

// ─── Filler words for communication score ────────────────────────────────────

const FILLER_WORDS = [
    'um', 'uh', 'like', 'you know', 'basically', 'literally',
    'actually', 'sort of', 'kind of', 'right', 'okay', 'so yeah',
]

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useVoiceInput({
    onTranscript,
    currentQuestion,
    screen,
}: UseVoiceInputProps) {

    // ── State ───────────────────────────────────────────────────────────────────
    const [isRecording, setIsRecording] = useState(false)
    const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>('idle')
    const [isSpeaking, setIsSpeaking] = useState(false)
    const [speechSupported, setSpeechSupported] = useState(false)
    const [voiceSupported, setVoiceSupported] = useState(false)
    const [usedVoiceInput, setUsedVoiceInput] = useState(false)
    const [commScore, setCommScore] = useState<CommScore | null>(null)
    const [audioURL, setAudioURL] = useState<string | null>(null)
    const [isPlaying, setIsPlaying] = useState(false)

    // ── Refs ────────────────────────────────────────────────────────────────────
    const recognitionRef = useRef<any>(null)
    const mediaRecorderRef = useRef<MediaRecorder | null>(null)
    const audioChunksRef = useRef<Blob[]>([])
    const audioRef = useRef<HTMLAudioElement | null>(null)

    // ── Init: detect browser support ────────────────────────────────────────────

    useEffect(() => {
        // Text-to-speech support
        if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
            setSpeechSupported(true)
        }

        // Speech recognition support
        if (typeof window !== 'undefined') {
            const SpeechRecognition =
                (window as any).SpeechRecognition ||
                (window as any).webkitSpeechRecognition

            if (SpeechRecognition) {
                setVoiceSupported(true)

                const instance = new SpeechRecognition()
                instance.continuous = true
                instance.interimResults = true
                instance.lang = 'en-US'

                instance.onresult = (event: any) => {
                    let finalTranscript = ''
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        if (event.results[i].isFinal) {
                            finalTranscript += event.results[i][0].transcript + ' '
                        }
                    }
                    if (finalTranscript.trim()) {
                        onTranscript(finalTranscript.trim())
                        setVoiceStatus('done')
                    }
                }

                instance.onerror = (event: any) => {
                    console.error('Speech recognition error:', event.error)
                    setIsRecording(false)
                    setVoiceStatus('idle')
                    if (event.error === 'not-allowed') {
                        toast.error('Microphone access denied. Please allow microphone permissions.')
                    }
                }

                instance.onend = () => {
                    setIsRecording(false)
                }

                recognitionRef.current = instance
            }
        }

        // Cleanup on unmount
        return () => {
            if (recognitionRef.current) {
                try { recognitionRef.current.stop() } catch { /* ignore */ }
            }
            if (typeof window !== 'undefined') {
                window.speechSynthesis?.cancel()
            }
            if (audioRef.current) {
                audioRef.current.pause()
                audioRef.current = null
            }
        }
    }, [onTranscript])

    // ── Auto-speak question when it changes ─────────────────────────────────────

    useEffect(() => {
        if (screen === 'interview' && currentQuestion && speechSupported) {
            // Brief delay so the UI settles before speaking
            const t = setTimeout(() => speakText(currentQuestion), 500)
            return () => clearTimeout(t)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [currentQuestion, screen, speechSupported])

    // ── Reset voice state between questions ─────────────────────────────────────

    const resetVoiceState = useCallback(() => {
        setVoiceStatus('idle')
        setUsedVoiceInput(false)
        setCommScore(null)
        setAudioURL(null)
    }, [])

    // ── Speak text (TTS) ────────────────────────────────────────────────────────

    const speakText = useCallback((text: string) => {
        if (!speechSupported || !text) return
        window.speechSynthesis.cancel()
        const utterance = new SpeechSynthesisUtterance(text)
        utterance.lang = 'en-US'
        utterance.rate = 0.95
        utterance.onstart = () => setIsSpeaking(true)
        utterance.onend = () => setIsSpeaking(false)
        utterance.onerror = () => setIsSpeaking(false)
        window.speechSynthesis.speak(utterance)
    }, [speechSupported])

    const speakQuestion = useCallback(() => {
        speakText(currentQuestion)
    }, [speakText, currentQuestion])

    // ── Toggle voice recording ───────────────────────────────────────────────────

    const toggleVoice = useCallback(async () => {
        if (!recognitionRef.current) return

        if (isRecording) {
            // Stop recording
            try { recognitionRef.current.stop() } catch { /* ignore */ }
            if (mediaRecorderRef.current?.state === 'recording') {
                mediaRecorderRef.current.stop()
            }
            setIsRecording(false)
            setVoiceStatus('done')
            return
        }

        // Start recording
        setAudioURL(null)
        audioChunksRef.current = []

        // Request mic + start MediaRecorder for playback
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })

            recorder.ondataavailable = (e) => {
                if (e.data.size > 0) audioChunksRef.current.push(e.data)
            }

            recorder.onstop = () => {
                if (audioChunksRef.current.length > 0) {
                    const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
                    setAudioURL(URL.createObjectURL(blob))
                }
                stream.getTracks().forEach(track => track.stop())
            }

            recorder.start()
            mediaRecorderRef.current = recorder
        } catch (err) {
            // Mic permission denied or not available — still allow speech recognition
            console.warn('MediaRecorder not available:', err)
        }

        // Start speech recognition
        try {
            recognitionRef.current.start()
            setIsRecording(true)
            setVoiceStatus('listening')
        } catch (err) {
            console.error('Failed to start speech recognition:', err)
            toast.error('Voice input failed. Please try again.')
        }
    }, [isRecording])

    // ── Toggle audio playback ────────────────────────────────────────────────────

    const togglePlayback = useCallback(() => {
        if (!audioURL) return

        if (isPlaying) {
            audioRef.current?.pause()
            setIsPlaying(false)
            return
        }

        const audio = new Audio(audioURL)
        audio.onended = () => setIsPlaying(false)
        audio.onerror = () => setIsPlaying(false)
        audio.play()
        audioRef.current = audio
        setIsPlaying(true)
    }, [audioURL, isPlaying])

    // ── Calculate communication score ───────────────────────────────────────────

    const calculateCommScore = useCallback((text: string): CommScore => {
        const textLower = text.toLowerCase()
        const fillers: Record<string, number> = {}
        let fillerCount = 0

        FILLER_WORDS.forEach(word => {
            const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
            const regex = new RegExp('\\b' + escaped + '\\b', 'gi')
            const matches = textLower.match(regex)
            if (matches) {
                fillers[word] = matches.length
                fillerCount += matches.length
            }
        })

        let score = 100
        score -= Math.min(fillerCount * 5, 40)
        const wordCount = text.split(/\s+/).filter(w => w.length > 0).length
        if (wordCount < 20) score -= 20
        if (wordCount > 200) score -= 10
        score = Math.max(0, score)

        const tip = score >= 80
            ? 'Masterful delivery! 🎙️'
            : 'Try pausing briefly instead of using filler words.'

        return { score, fillers, tip }
    }, [])

    // ── Track comm score when voice input finishes ────────────────────────────

    const finalizeVoiceAnswer = useCallback((answerText: string) => {
        if (voiceStatus === 'done' && answerText.trim()) {
            setUsedVoiceInput(true)
            setCommScore(calculateCommScore(answerText))
        }
    }, [voiceStatus, calculateCommScore])

    // ── Return ──────────────────────────────────────────────────────────────────

    return {
        // State
        isRecording,
        voiceStatus,
        isSpeaking,
        speechSupported,
        voiceSupported,
        usedVoiceInput,
        commScore,
        audioURL,
        isPlaying,

        // Actions
        toggleVoice,
        speakQuestion,
        speakText,
        togglePlayback,
        calculateCommScore,
        finalizeVoiceAnswer,
        resetVoiceState,
    }
}