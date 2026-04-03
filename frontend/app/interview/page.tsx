'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import Navbar from '@/components/Navbar'
import { 
  Brain, Loader2, ChevronRight, CheckCircle, XCircle,
  Lightbulb, ArrowRight, Copy, RefreshCw, MessageSquare, Mic, MicOff, Volume2
} from 'lucide-react'

interface Question {
  id: number
  question: string
  type: string
  difficulty: string
  hint: string
}

interface Answer {
  question: string
  answer: string
  feedback: {
    score: number
    good_points: string[]
    missing_points: string[]
    model_answer: string
    tip: string
  }
}

type ScreenState = 'setup' | 'interview' | 'results'

export default function InterviewPage() {
  const router = useRouter()
  const [screen, setScreen] = useState<ScreenState>('setup')
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState<{ id: string } | null>(null)
  
  // Setup state
  const [careerPath, setCareerPath] = useState('Full Stack Developer')
  const [difficulty, setDifficulty] = useState('medium')
  const [personality, setPersonality] = useState('friendly')
  const [pastSessions, setPastSessions] = useState(0)
  const [careerPaths, setCareerPaths] = useState<string[]>([])
  
  // Interview state
  const [questions, setQuestions] = useState<Question[]>([])
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [answer, setAnswer] = useState('')
  const [showHint, setShowHint] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [answers, setAnswers] = useState<Answer[]>([])
  const [elapsedTime, setElapsedTime] = useState(0)
  const [timerInterval, setTimerInterval] = useState<NodeJS.Timeout | null>(null)
  
  // Voice recognition state
  const [isRecording, setIsRecording] = useState(false)
  const [voiceStatus, setVoiceStatus] = useState<'idle' | 'listening' | 'done'>('idle')
  const [recognition, setRecognition] = useState<any>(null)
  
  // Text-to-Speech state
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [speechSupported, setSpeechSupported] = useState(true)
  
  // AI Coaching hint state
  const [coachingHint, setCoachingHint] = useState<{looking_for: string, structure: string, example: string} | null>(null)
  const [hintLoading, setHintLoading] = useState(false)
  const [showCoachingHint, setShowCoachingHint] = useState(false)
  
  // Communication score state (for voice input)
  const [usedVoiceInput, setUsedVoiceInput] = useState(false)
  const [commScore, setCommScore] = useState<{score: number, fillers: Record<string, number>, tip: string} | null>(null)
  
  // Audio recording state (for voice playback)
  const [audioURL, setAudioURL] = useState<string | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null)
  const [audioChunks, setAudioChunks] = useState<Blob[]>([])
  const [audioSupported, setAudioSupported] = useState(true)
  
  // Simulation mode state
  const [simMode, setSimMode] = useState(false)
  const [questionTimeLeft, setQuestionTimeLeft] = useState(120)
  const [questionTimer, setQuestionTimer] = useState<NodeJS.Timeout | null>(null)
  const [showTimeUpMsg, setShowTimeUpMsg] = useState(false)
  
  // Results state
  const [totalScore, setTotalScore] = useState(0)
  
  // Streak state
  const [streakData, setStreakData] = useState<{current_streak: number, longest_streak: number, last_practice_date: string | null, total_sessions: number} | null>(null)
  const [streakMessage, setStreakMessage] = useState<string | null>(null)
  
  // Rank state
  const [rankData, setRankData] = useState<{xp: number, level: number, rank_title: string, next_level_xp: number, progress_percent: number} | null>(null)
  const [xpEarned, setXpEarned] = useState<number | null>(null)
  const [leveledUp, setLeveledUp] = useState(false)
  
  // Badge popup state
  const [newBadge, setNewBadge] = useState<{emoji: string, name: string} | null>(null)

  // Challenge modal
  const [challengeModal, setChallengeModal] = useState(false)
  const [challengeURL, setChallengeURL] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        router.push('/auth/login')
        return
      }
      setUser(user)
      await loadUserData(user.id)
      
      // Fetch streak data
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const streakResponse = await fetch(`${apiUrl}/api/streaks/${user.id}`)
        if (streakResponse.ok) {
          const data = await streakResponse.json()
          setStreakData(data)
        }
      } catch (err) {
        console.error('Error fetching streak:', err)
      }
      
      // Fetch rank data
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const rankResponse = await fetch(`${apiUrl}/api/ranks/${user.id}`)
        if (rankResponse.ok) {
          const data = await rankResponse.json()
          setRankData(data)
        }
      } catch (err) {
        console.error('Error fetching rank:', err)
      }
    }
    checkAuth()
  }, [router])

  useEffect(() => {
    return () => {
      if (timerInterval) clearInterval(timerInterval)
    }
  }, [timerInterval])

  // Initialize speech recognition on component mount
  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (SpeechRecognition) {
      const recognitionInstance = new SpeechRecognition()
      recognitionInstance.continuous = true
      recognitionInstance.interimResults = true
      recognitionInstance.lang = 'en-US'
      
      recognitionInstance.onresult = (event: any) => {
        let finalTranscript = ''
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript
          if (event.results[i].isFinal) {
            finalTranscript += transcript + ' '
          }
        }
        
        if (finalTranscript) {
          setAnswer(prev => prev + finalTranscript.trim())
          setVoiceStatus('done')
        }
      }
      
      recognitionInstance.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error)
        setIsRecording(false)
        setVoiceStatus('idle')
      }
      
      recognitionInstance.onend = () => {
        setIsRecording(false)
        if (voiceStatus !== 'done') {
          setVoiceStatus('idle')
        }
      }
      
      setRecognition(recognitionInstance)
    }
  }, [])

  const loadUserData = async (userId: string) => {
    try {
      // Get user's analysis for career paths
      const { data: analysisData } = await supabase
        .from('analyses')
        .select('career_paths')
        .eq('user_id', userId)
        .single()
      
      if (analysisData?.career_paths) {
        const paths = analysisData.career_paths.map((p: any) => p.name || p.career_name)
        setCareerPaths(paths)
        if (paths.length > 0) setCareerPath(paths[0])
      }
      
      // Get past sessions count
      const { count } = await supabase
        .from('interview_sessions')
        .select('*', { count: 'exact', head: true })
        .eq('user_id', userId)
      
      setPastSessions(count || 0)
    } catch (err) {
      console.error('Error loading user data:', err)
    } finally {
      setLoading(false)
    }
  }

  const startInterview = async () => {
    if (!user) return
    
    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/interview/generate-questions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          career_path: careerPath,
          difficulty,
          personality
        })
      })
      
      const data = await response.json()
      
      if (data.questions) {
        setQuestions(data.questions)
        setCurrentQuestion(0)
        setAnswers([])
        setAnswer('')
        setScreen('interview')
        
        // Start timer
        const interval = setInterval(() => {
          setElapsedTime(prev => prev + 1)
        }, 1000)
        setTimerInterval(interval)
      }
    } catch (err) {
      console.error('Error generating questions:', err)
    } finally {
      setLoading(false)
    }
  }

  const submitAnswer = async () => {
    if (!user) return
    
    // Clear question timer if running
    if (questionTimer) {
      clearInterval(questionTimer)
      setQuestionTimer(null)
    }
    
    if (!answer.trim()) {
      // In simulation mode, submit even if empty when time is up
      if (simMode) {
        await handleTimeUp()
        return
      }
      return
    }
    
    setSubmitting(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/interview/evaluate-answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: questions[currentQuestion].question,
          answer,
          career_path: careerPath,
          user_id: user.id
        })
      })
      
      const feedback = await response.json()
      
      const newAnswer: Answer = {
        question: questions[currentQuestion].question,
        answer,
        feedback
      }

      const updatedAnswers = [...answers, newAnswer]
      setAnswers(updatedAnswers)
      
      // Move to next or finish
      if (currentQuestion < questions.length - 1) {
        setCurrentQuestion(prev => prev + 1)
        setAnswer('')
        setShowHint(false)
        // Reset voice-related states for next question
        setVoiceStatus('idle')
        setUsedVoiceInput(false)
        setCommScore(null)
      } else {
        finishInterview(updatedAnswers)
      }
    } catch (err) {
      console.error('Error submitting answer:', err)
    } finally {
      setSubmitting(false)
    }
  }

  const finishInterview = async (finalAnswers?: Answer[]) => {
    if (!user) return

    const answersToUse = finalAnswers || answers
    
    // Stop timer
    if (timerInterval) {
      clearInterval(timerInterval)
      setTimerInterval(null)
    }
    
    // Calculate total score
    const total = answersToUse.reduce((sum, a) => sum + (a.feedback?.score || 0), 0)
    setTotalScore(total)
    
    // Save session
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      await fetch(`${apiUrl}/api/interview/save-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          career_path: careerPath,
          questions: questions.map(q => q.question),
          answers: answersToUse.map(a => ({ question: a.question, answer: a.answer })),
          scores: answersToUse.map(a => a.feedback?.score || 0),
          total_score: total
        })
      })
      
      // Update streak after successful session save
      try {
        const streakResponse = await fetch(`${apiUrl}/api/streaks/update`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: user.id })
        })
        if (streakResponse.ok) {
          const streakData = await streakResponse.json()
          setStreakData({
            current_streak: streakData.current_streak,
            longest_streak: streakData.longest_streak,
            last_practice_date: streakData.last_practice_date,
            total_sessions: streakData.total_sessions
          })
          setStreakMessage(streakData.message)
        }
      } catch (streakErr) {
        console.error('Error updating streak:', streakErr)
      }
      
      // Update rank after successful session save
      try {
        const rankResponse = await fetch(`${apiUrl}/api/ranks/update`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: user.id, score: total })
        })
        if (rankResponse.ok) {
          const rankData = await rankResponse.json()
          setRankData({
            xp: rankData.xp,
            level: rankData.level,
            rank_title: rankData.rank_title,
            next_level_xp: rankData.next_level_xp,
            progress_percent: ((rankData.xp % 100) / 100) * 100
          })
          setXpEarned(rankData.xp_earned)
          setLeveledUp(rankData.leveled_up)
        }
      } catch (rankErr) {
        console.error('Error updating rank:', rankErr)
      }
      
      // Check for badges - session_complete always
      try {
        const sessionBadgeResponse = await fetch(`${apiUrl}/api/badges/check`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: user.id, event: 'session_complete' })
        })
        if (sessionBadgeResponse.ok) {
          const sessionBadgeData = await sessionBadgeResponse.json()
          if (sessionBadgeData.newly_earned && sessionBadgeData.newly_earned.length > 0) {
            const badge = sessionBadgeData.newly_earned[0]
            setNewBadge({ emoji: badge.emoji, name: badge.name })
            setTimeout(() => setNewBadge(null), 3000)
          }
        }
      } catch (badgeErr) {
        console.error('Error checking session badges:', badgeErr)
      }
      
      // Check for hard_mode badge if difficulty was hard
      if (difficulty === 'hard') {
        try {
          await fetch(`${apiUrl}/api/badges/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: user.id, event: 'hard_mode' })
          })
        } catch (hardBadgeErr) {
          console.error('Error checking hard mode badge:', hardBadgeErr)
        }
      }
      
      // Check for simulation badge if simMode was true
      if (simMode) {
        try {
          await fetch(`${apiUrl}/api/badges/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: user.id, event: 'simulation' })
          })
        } catch (simBadgeErr) {
          console.error('Error checking simulation badge:', simBadgeErr)
        }
      }
      
      // Check for perfect_score badge if total === 50
      if (total === 50) {
        try {
          const perfectBadgeResponse = await fetch(`${apiUrl}/api/badges/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: user.id, event: 'perfect_score' })
          })
          if (perfectBadgeResponse.ok) {
            const perfectBadgeData = await perfectBadgeResponse.json()
            if (perfectBadgeData.newly_earned && perfectBadgeData.newly_earned.length > 0) {
              const badge = perfectBadgeData.newly_earned[0]
              setNewBadge({ emoji: badge.emoji, name: badge.name })
              setTimeout(() => setNewBadge(null), 3000)
            }
          }
        } catch (perfectBadgeErr) {
          console.error('Error checking perfect score badge:', perfectBadgeErr)
        }
      }
    } catch (err) {
      console.error('Error saving session:', err)
    }
    
    setScreen('results')
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-600 bg-green-100'
    if (score >= 5) return 'text-yellow-600 bg-yellow-100'
    return 'text-red-600 bg-red-100'
  }

  const getPerformanceRating = (score: number) => {
    const percentage = (score / 50) * 100
    if (percentage >= 80) return 'Excellent'
    if (percentage >= 60) return 'Good'
    return 'Needs Work'
  }

  // Create challenge function
  const createChallenge = async () => {
    if (!user || !questions.length) return
    
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const questionTexts = questions.map(q => q.question)
      const response = await fetch(`${apiUrl}/api/challenges/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          career_path: careerPath,
          questions: questionTexts
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setChallengeURL(data.share_url)
        setChallengeModal(true)
        setCopied(false)
      }
    } catch (err) {
      console.error('Error creating challenge:', err)
    }
  }

  // Copy challenge link to clipboard
  const copyChallengeLink = async () => {
    if (!challengeURL) return
    
    await navigator.clipboard.writeText(challengeURL)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const copyResults = () => {
    const text = `🎯 My AI Interview Coach Results

Career: ${careerPath}
Overall Score: ${totalScore}/50 (${getPerformanceRating(totalScore)})

${answers.map((a, i) => `Q${i+1}: ${a.question.substring(0, 50)}... - Score: ${a.feedback?.score || 0}/10`).join('\n')}

Powered by AI Career Navigator`
    
    navigator.clipboard.writeText(text)
  }

  // Handle time up in simulation mode
  const handleTimeUp = async () => {
    if (questionTimer) {
      clearInterval(questionTimer)
      setQuestionTimer(null)
    }
    
    setShowTimeUpMsg(true)
    
    // Auto submit the answer (may be empty)
    if (!user) return
    
    setSubmitting(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/interview/evaluate-answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: questions[currentQuestion].question,
          answer,
          career_path: careerPath,
          user_id: user.id
        })
      })
      
      const feedback = await response.json()
      
      const newAnswer: Answer = {
        question: questions[currentQuestion].question,
        answer,
        feedback
      }

      const updatedAnswers = [...answers, newAnswer]
      setAnswers(updatedAnswers)
      
      // Reset voice-related states for next question
      setVoiceStatus('idle')
      setUsedVoiceInput(false)
      setCommScore(null)
      
      // Move to next or finish after delay
      setTimeout(() => {
        setShowTimeUpMsg(false)
        if (currentQuestion < questions.length - 1) {
          setCurrentQuestion(prev => prev + 1)
          setAnswer('')
          setShowHint(false)
          setQuestionTimeLeft(120) // Reset timer for next question
        } else {
          finishInterview(updatedAnswers)
        }
      }, 1500)
    } catch (err) {
      console.error('Error submitting answer:', err)
    } finally {
      setSubmitting(false)
    }
  }

  // Start question timer when entering a new question in simulation mode
  useEffect(() => {
    if (simMode && screen === 'interview' && questions.length > 0) {
      setQuestionTimeLeft(120)
      
      // Clear any existing timer
      if (questionTimer) {
        clearInterval(questionTimer)
      }
      
      // Start countdown
      const timer = setInterval(() => {
        setQuestionTimeLeft(prev => {
          if (prev <= 1) {
            // Time's up - trigger auto submit
            handleTimeUp()
            return 0
          }
          return prev - 1
        })
      }, 1000)
      
      setQuestionTimer(timer)
      
      return () => {
        if (timer) clearInterval(timer)
      }
    }
  }, [currentQuestion, simMode, screen, questions.length])

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (questionTimer) {
        clearInterval(questionTimer)
      }
    }
  }, [])

  // Toggle voice recording
  const toggleVoice = async () => {
    if (!recognition) {
      alert('Voice input not supported in this browser. Please type your answer.')
      return
    }
    
    if (isRecording) {
      // Stop voice recognition
      recognition.stop()
      setIsRecording(false)
      setVoiceStatus('done')
      
      // Stop audio recording if active
      if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop()
      }
    } else {
      setAnswer('') // Clear previous answer for new recording
      setAudioURL(null) // Clear previous audio
      setAudioChunks([]) // Reset audio chunks
      
      // Start audio recording if supported
      if (audioSupported) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
          const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
          const chunks: Blob[] = []
          
          recorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
              chunks.push(event.data)
            }
          }
          
          recorder.onstop = () => {
            if (chunks.length > 0) {
              const blob = new Blob(chunks, { type: 'audio/webm' })
              const url = URL.createObjectURL(blob)
              setAudioURL(url)
              setAudioChunks(chunks)
            }
            // Stop all tracks in the stream
            stream.getTracks().forEach(track => track.stop())
          }
          
          recorder.start()
          setMediaRecorder(recorder)
        } catch (err) {
          // Silently fail - playback button will be hidden
          console.log('Audio recording not available')
        }
      }
      
      try {
        recognition.start()
        setIsRecording(true)
        setVoiceStatus('listening')
      } catch (e) {
        console.error('Error starting recognition:', e)
      }
    }
  }

  // Check for SpeechSynthesis support and initialize
  useEffect(() => {
    if (typeof window !== 'undefined' && !window.speechSynthesis) {
      setSpeechSupported(false)
    }
    // Check for MediaRecorder support
    if (typeof window !== 'undefined' && !window.MediaRecorder) {
      setAudioSupported(false)
    }
  }, [])

  // Speak the current question
  const speakQuestion = () => {
    if (!speechSupported || !questions[currentQuestion]) return
    
    // Stop any current speech
    window.speechSynthesis.cancel()
    
    const utterance = new SpeechSynthesisUtterance(questions[currentQuestion].question)
    utterance.lang = 'en-US'
    utterance.rate = 0.9
    
    utterance.onstart = () => setIsSpeaking(true)
    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)
    
    window.speechSynthesis.speak(utterance)
  }

  // Fetch AI coaching hint for current question
  const fetchCoachingHint = async () => {
    setHintLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/interview/question-hint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: questions[currentQuestion].question,
          career_path: careerPath
        })
      })
      
      const data = await response.json()
      setCoachingHint(data)
    } catch (err) {
      console.error('Error fetching coaching hint:', err)
    } finally {
      setHintLoading(false)
    }
  }

  // Calculate communication score from voice input
  const calculateCommScore = useCallback((text: string) => {
    const fillerWords = ['um', 'uh', 'like', 'you know', 'basically', 'literally', 'actually', 'sort of', 'kind of', 'right', 'okay', 'so yeah']
    const textLower = text.toLowerCase()
    
    // Count filler words
    const fillers: Record<string, number> = {}
    let fillerCount = 0
    
    fillerWords.forEach(word => {
      const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      const regex = new RegExp('\\b' + escaped + '\\b', 'gi')
      const matches = textLower.match(regex)
      if (matches && matches.length > 0) {
        fillers[word] = matches.length
        fillerCount += matches.length
      }
    })
    const fetchCoachingHint = async () => {
    setHintLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/interview/question-hint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: questions[currentQuestion].question,
          career_path: careerPath
        })
      })
      const data = await response.json()
      setCoachingHint(data)
    } catch (err) {
      console.error('Error fetching coaching hint:', err)
    } finally {
      setHintLoading(false)
    }
  }    
    // Calculate score
    let score = 100
    score -= Math.min(fillerCount * 5, 40) // -5 per filler, max -40
    
    const wordCount = text.split(/\s+/).filter(w => w.length > 0).length
    if (wordCount < 20) score -= 20 // Too short
    if (wordCount > 200) score -= 10 // Too long
    
    score = Math.max(0, score)
    
    // Generate tip
    let tip = ''
    if (fillerCount > 3) {
      tip = 'Try pausing instead of using filler words'
    } else if (wordCount < 20) {
      tip = 'Try to elaborate more on your answer'
    } else if (wordCount > 200) {
      tip = 'Try to be more concise with your answers'
    } else if (score >= 80) {
      tip = 'Great communication! Keep it up 🎉'
    } else {
      tip = 'Keep practicing to improve your communication skills'
    }
    
    return { score, fillers, tip }
  }, [])

  // Playback control functions
  const playAudio = () => {
    if (!audioURL) return
    
    const audio = new Audio(audioURL)
    audio.onended = () => setIsPlaying(false)
    audio.onerror = () => setIsPlaying(false)
    audio.play()
    setIsPlaying(true)
  }

  const stopAudio = () => {
    const audioElements = document.querySelectorAll('audio')
    audioElements.forEach(audio => {
      audio.pause()
      audio.currentTime = 0
    })
    setIsPlaying(false)
  }

  const togglePlayback = () => {
    if (isPlaying) {
      stopAudio()
    } else {
      playAudio()
    }
  }

  // Cleanup audio when question changes
  useEffect(() => {
    if (audioURL) {
      URL.revokeObjectURL(audioURL)
      setAudioURL(null)
    }
    setIsPlaying(false)
    setAudioChunks([])
  }, [currentQuestion])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioURL) {
        URL.revokeObjectURL(audioURL)
      }
    }
  }, [audioURL])

  // Update communication score when voiceStatus changes to done
  useEffect(() => {
    if (voiceStatus === 'done' && answer.trim()) {
      setUsedVoiceInput(true)
      const scoreResult = calculateCommScore(answer)
      setCommScore(scoreResult)
    }
  }, [voiceStatus, answer, calculateCommScore])

  // When question changes, auto-speak and fetch coaching hint
  useEffect(() => {
    if (screen === 'interview' && questions.length > 0) {
      // Reset coaching hint state
      setCoachingHint(null)
      setShowCoachingHint(false)
      
      // Auto-speak the question after a short delay
      if (speechSupported) {
        setTimeout(() => {
          speakQuestion()
        }, 500)
      }
    }
  }, [currentQuestion, screen, questions.length, speechSupported])

  if (loading && screen === 'setup') {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      
      {/* Streak Badge - Always visible at top */}
      {(streakData || rankData) && (
        <div className="flex items-center justify-center gap-4 py-2 px-4 bg-gradient-to-r from-gray-900 to-gray-800 text-white">
          {/* Streak Badge */}
          {streakData && (
            <div className={`text-sm font-medium ${
              streakData.current_streak >= 30 ? 'animate-pulse' : 
              streakData.current_streak >= 7 ? 'shadow-lg' : ''
            }`}>
              {streakData.current_streak >= 30 ? '🏆 ' : streakData.current_streak > 0 ? '🔥 ' : 'Start '}
              {streakData.current_streak > 0 ? `${streakData.current_streak} day streak` : 'streak today! 🔥'}
            </div>
          )}
          
          {/* Rank Badge */}
          {rankData && (
            <div className="text-sm border-l border-gray-600 pl-4">
              <span className="font-semibold">{rankData.rank_title} — Level {rankData.level}</span>
              <div className="text-xs text-gray-400 mt-1">
                {rankData.xp} / {rankData.next_level_xp} XP to next level
              </div>
              <div className="w-24 h-1.5 bg-gray-700 rounded-full mt-1">
                <div 
                  className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
                  style={{ width: `${rankData.progress_percent}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}
      
      <main className="container mx-auto px-4 py-8">
        {/* STATE 1: SETUP SCREEN */}
        {screen === 'setup' && (
          <div className="max-w-2xl mx-auto text-center">
            <div className="mb-8">
              <h1 className="text-4xl font-bold text-[#1E3A5F] mb-2">AI Interview Coach</h1>
              <p className="text-muted-foreground text-lg">
                Practice with personalized questions based on your profile
              </p>
            </div>

            {pastSessions > 0 && (
              <div className="mb-6 p-4 bg-[#6C3FC8]/10 rounded-lg">
                <p className="text-[#6C3FC8] font-medium">
                  You have completed {pastSessions} interview session{pastSessions > 1 ? 's' : ''} before
                </p>
              </div>
            )}

            <div className="bg-card rounded-xl border p-6 text-left">
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Career Path</label>
                <select
                  value={careerPath}
                  onChange={(e) => setCareerPath(e.target.value)}
                  aria-label="Select career path"
                  className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
                >
                  {careerPaths.length > 0 ? (
                    careerPaths.map((path, i) => (
                      <option key={i} value={path}>{path}</option>
                    ))
                  ) : (
                    <>
                      <option value="Full Stack Developer">Full Stack Developer</option>
                      <option value="Data Scientist">Data Scientist</option>
                      <option value="DevOps Engineer">DevOps Engineer</option>
                      <option value="Product Manager">Product Manager</option>
                    </>
                  )}
                </select>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Difficulty</label>
                <div className="flex gap-2">
                  {['easy', 'medium', 'hard'].map((d) => (
                    <button
                      key={d}
                      onClick={() => setDifficulty(d)}
                      className={`flex-1 py-2 px-4 rounded-lg font-medium capitalize transition-colors ${
                        difficulty === d 
                          ? 'bg-[#6C3FC8] text-white' 
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {d}
                    </button>
                  ))}
                </div>
              </div>

              {/* Personality Selector */}
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Choose Your Interviewer</label>
                <div className="grid grid-cols-3 gap-3">
                  <button
                    type="button"
                    onClick={() => setPersonality('friendly')}
                    className={`p-4 rounded-lg border-2 transition-colors ${
                      personality === 'friendly'
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <div className="text-2xl mb-1">😊</div>
                    <div className="text-sm font-medium">Friendly</div>
                    <div className="text-xs text-muted-foreground mt-1">Warm & encouraging</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setPersonality('strict')}
                    className={`p-4 rounded-lg border-2 transition-colors ${
                      personality === 'strict'
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <div className="text-2xl mb-1">😐</div>
                    <div className="text-sm font-medium">Strict</div>
                    <div className="text-xs text-muted-foreground mt-1">Direct & challenging</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setPersonality('google')}
                    className={`p-4 rounded-lg border-2 transition-colors ${
                      personality === 'google'
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <div className="text-2xl mb-1">😈</div>
                    <div className="text-sm font-medium">Google-style</div>
                    <div className="text-xs text-muted-foreground mt-1">Pressure & depth</div>
                  </button>
                </div>
              </div>

              {/* Mode Selection */}
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Interview Mode</label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setSimMode(false)}
                    className={`flex-1 py-3 px-4 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                      !simMode 
                        ? 'bg-[#6C3FC8] text-white' 
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    🎯 Practice Mode
                  </button>
                  <button
                    type="button"
                    onClick={() => setSimMode(true)}
                    className={`flex-1 py-3 px-4 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                      simMode 
                        ? 'bg-[#FF6B35] text-white' 
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    ⚡ Simulation Mode
                  </button>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  {simMode 
                    ? '⚡ Real interview feel — 2 min per question, no hints, auto-submit'
                    : '🎯 Relaxed practice — no timer, hints available'}
                </p>
              </div>

              <Button 
                onClick={startInterview}
                disabled={loading}
                className="w-full bg-[#1E3A5F] hover:bg-[#1E3A5F]/90 py-3 text-lg"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Generating Questions...
                  </>
                ) : (
                  <>
                    Start Interview
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

        {/* STATE 2: INTERVIEW SCREEN */}
        {screen === 'interview' && questions.length > 0 && (
          <div className="max-w-3xl mx-auto">
            {/* Progress */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">
                  Question {currentQuestion + 1} of {questions.length}
                </span>
                <span className="text-sm text-muted-foreground">
                  ⏱️ {formatTime(elapsedTime)}
                </span>
              </div>
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-[#1E3A5F] to-[#6C3FC8] transition-all"
                  style={{ width: `${((currentQuestion + 1) / questions.length) * 100}%` }}
                                  
                />                
              </div>
            </div>

            {/* Simulation Mode Banner */}
            {simMode && (
              <div className="mb-4 p-3 bg-orange-50 border border-orange-200 rounded-lg text-center text-orange-700 font-medium">
                ⚡ Simulation Mode — Answer like a real interview
              </div>
            )}

            {/* Personality Badge */}
            <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg text-center">
              <span className="text-blue-700 dark:text-blue-300 font-medium">
                {personality === 'friendly' && '😊 Friendly Interviewer'}
                {personality === 'strict' && '😐 Strict Interviewer'}
                {personality === 'google' && '😈 Google-style Interviewer'}
              </span>
            </div>

            {/* Simulation Mode Timer */}
            {simMode && (
              <div className="mb-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">⏱ Time Remaining:</span>
                  <span className={`text-lg font-bold ${
                    questionTimeLeft > 60 ? 'text-green-600' :
                    questionTimeLeft > 30 ? 'text-yellow-600' :
                    'text-red-600 animate-pulse'
                  }`}>
                    {Math.floor(questionTimeLeft / 60)}:{String(questionTimeLeft % 60).padStart(2, '0')}
                  </span>
                </div>
                <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                  <div 
                    className={`h-full transition-all ${
                      questionTimeLeft > 60 ? 'bg-green-500' :
                      questionTimeLeft > 30 ? 'bg-yellow-500' :
                      'bg-red-500 animate-pulse'
                    }`}
                    style={{ width: `${(questionTimeLeft / 120) * 100}%` }}
                  />
                </div>
              </div>
            )}

            {/* Time's up message */}
            {showTimeUpMsg && (
              <div className="mb-4 p-4 bg-red-100 border border-red-300 rounded-lg text-center text-red-700 animate-pulse">
                ⏰ Time's up! Moving to next question...
              </div>
            )}

            {/* Question Card */}
            <div className="bg-card rounded-xl border p-6 mb-6">
              <div className="flex items-center gap-2 mb-4">
                <span className="px-3 py-1 bg-[#1E3A5F]/10 text-[#1E3A5F] rounded-full text-sm font-medium">
                  {(questions[currentQuestion]?.type || 'technical').replace('_', ' ').toUpperCase()}
                </span>
                <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm capitalize">
                  {questions[currentQuestion]?.difficulty || 'medium'}
                </span>
                {speechSupported && (
                  <button
                    type="button"
                    onClick={speakQuestion}
                    className={`ml-2 p-2 rounded-full transition-colors ${
                      isSpeaking 
                        ? 'bg-[#6C3FC8]/20 text-[#6C3FC8] animate-pulse' 
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                    title={isSpeaking ? 'Speaking...' : 'Read question aloud'}
                  >
                    <Volume2 className="w-4 h-4" />
                  </button>
                )}
              </div>
              
              <h2 className="text-xl font-semibold text-foreground mb-4">
                {questions[currentQuestion]?.question || 'Loading question...'}
              </h2>

              {showHint && (
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg mb-4">
                  <div className="flex items-center gap-2 text-yellow-800">
                    <Lightbulb className="w-4 h-4" />
                    <span className="font-medium">Hint:</span>
                  </div>
                  <p className="text-yellow-700 mt-1">{questions[currentQuestion]?.hint || 'No hint available'}</p>
                </div>
              )}

              {/* AI Coaching Hint Card - Only in Practice Mode */}
              {!simMode && (
                <>
                  {!showCoachingHint ? (
                <button
                  type="button"
                  onClick={() => {
                    setShowCoachingHint(true)
                    fetchCoachingHint()
                  }}
                  className="w-full p-3 mb-4 bg-[#6C3FC8]/10 border border-[#6C3FC8]/30 rounded-lg text-[#6C3FC8] font-medium hover:bg-[#6C3FC8]/20 transition-colors flex items-center justify-center gap-2"
                >
                  <Lightbulb className="w-4 h-4" />
                  💡 Get AI Coaching Hint
                </button>
              ) : hintLoading ? (
                <div className="p-4 mb-4 bg-gray-50 border rounded-lg flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-[#6C3FC8]" />
                  <span className="text-gray-600">Loading coaching hint...</span>
                </div>
              ) : coachingHint ? (
                <div className="p-4 mb-4 bg-gradient-to-r from-[#6C3FC8]/10 to-[#1E3A5F]/10 border border-[#6C3FC8]/30 rounded-lg">
                  <div className="flex items-center gap-2 mb-3">
                    <Lightbulb className="w-5 h-5 text-[#6C3FC8]" />
                    <span className="font-semibold text-[#6C3FC8]">AI Coaching Hint</span>
                  </div>
                  
                  <div className="space-y-3">
                    <div>
                      <p className="text-sm font-medium text-gray-700">💡 What the interviewer is looking for:</p>
                      <p className="text-sm text-gray-600 mt-1">{coachingHint.looking_for}</p>
                    </div>
                    
                    <div>
                      <p className="text-sm font-medium text-gray-700">📝 How to structure your answer:</p>
                      <p className="text-sm text-gray-600 mt-1">{coachingHint.structure}</p>
                    </div>
                    
                    <div>
                      <p className="text-sm font-medium text-gray-700">✅ Example direction:</p>
                      <p className="text-sm text-gray-600 mt-1 italic">{coachingHint.example}</p>
                    </div>
                  </div>
                </div>
              ) : null}
                </>
              )}

              <div className="flex items-center gap-2">
                <textarea
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder="Type your answer here..."
                  className="w-full p-4 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none min-h-[200px]"
                />
              </div>

              {/* Communication Score Card (Voice Input) - Only in Practice Mode */}
              {!simMode && usedVoiceInput && commScore && (
                <div className="mt-3 p-4 rounded-xl border border-gray-700 bg-gray-800/50">
                  {/* Score Header */}
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-sm font-semibold text-gray-300">
                      🎙️ Voice Communication Score
                    </span>
                    <span className={`text-sm font-bold px-2 py-0.5 rounded-full ${
                      commScore.score >= 80 ? 'bg-green-500/20 text-green-400' :
                      commScore.score >= 60 ? 'bg-yellow-500/20 text-yellow-400' :
                      commScore.score >= 40 ? 'bg-orange-500/20 text-orange-400' :
                      'bg-red-500/20 text-red-400'
                    }`}>
                      {commScore.score}/100 — {
                        commScore.score >= 80 ? '🟢 Excellent' :
                        commScore.score >= 60 ? '🟡 Good' :
                        commScore.score >= 40 ? '🟠 Needs Improvement' :
                        '🔴 Needs Practice'
                      }
                    </span>
                  </div>

                  {/* Filler Words */}
                  {Object.keys(commScore.fillers).length > 0 && (
                    <div className="mb-2 text-sm text-gray-400">
                      <span className="text-gray-300 font-medium">Filler words detected: </span>
                      {Object.entries(commScore.fillers).map(([word, count]) => (
                        <span key={word} className="mr-2 text-orange-400">
                          "{word}" ({count}x)
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Tip */}
                  <div className="text-sm text-blue-400 mt-1">
                    💡 {commScore.tip}
                  </div>

                  {/* Audio Playback Button */}
                  {audioSupported && audioURL && (
                    <button
                      type="button"
                      onClick={togglePlayback}
                      className={`mt-3 text-sm px-3 py-1.5 rounded-lg border transition-colors ${
                        isPlaying 
                          ? 'bg-red-50 border-red-300 text-red-600 hover:bg-red-100'
                          : 'bg-gray-50 border-gray-300 text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      {isPlaying ? '⏹ Stop Playback' : '🎧 Play Back Your Answer'}
                    </button>
                  )}

                </div>
              )}

              <div className="flex items-center justify-between mt-3">
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={toggleVoice}
                    disabled={!recognition}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                      !recognition 
                        ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
                        : isRecording 
                          ? 'bg-red-100 text-red-600 animate-pulse' 
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                    title={!recognition ? 'Voice input not supported in this browser' : 'Click to speak your answer'}
                  >
                    {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                    <span className="text-sm">
                      {isRecording ? 'Stop' : 'Voice'}
                    </span>
                  </button>
                  <span className="text-sm text-muted-foreground">
                    {voiceStatus === 'idle' && 'Click mic to speak your answer'}
                    {voiceStatus === 'listening' && '🔴 Listening...'}
                    {voiceStatus === 'done' && '✅ Done! Review your answer'}
                  </span>
                </div>
                
                {/* Show Hint button - Only in Practice Mode */}
                {!simMode && (
                  <Button 
                    variant="outline" 
                    onClick={() => setShowHint(!showHint)}
                  >
                    <Lightbulb className="w-4 h-4 mr-2" />
                    {showHint ? 'Hide Hint' : 'Show Hint'}
                  </Button>
                )}
                
                <Button 
                  onClick={submitAnswer}
                  disabled={submitting || !answer.trim()}
                  className="bg-[#6C3FC8] hover:bg-[#6C3FC8]/90"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Evaluating...
                    </>
                  ) : (
                    <>
                      Submit Answer
                      <ChevronRight className="w-4 h-4 ml-2" />
                    </>
                  )}
                </Button>
              </div>
            </div>

            {/* Previous Answers Summary */}
            {answers.length > 0 && (
              <div className="bg-card rounded-xl border p-4">
                <h3 className="font-medium mb-2">Your Progress</h3>
                <div className="flex gap-2 flex-wrap">
                  {answers.map((a, i) => (
                    <div 
                      key={i} 
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${getScoreColor(a.feedback?.score || 0)}`}
                    >
                      {i + 1}
                    </div>
                  ))}
                  {Array.from({ length: questions.length - answers.length }).map((_, i) => (
                    <div 
                      key={answers.length + i} 
                      className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-sm text-gray-500"
                    >
                      {answers.length + i + 1}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* STATE 3: RESULTS SCREEN */}
        {screen === 'results' && (
          <div className="max-w-3xl mx-auto">
            {/* Badge Popup */}
            {newBadge && (
              <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-gradient-to-r from-[#6C3FC8] to-[#4A2F8A] text-white px-6 py-4 rounded-xl shadow-2xl animate-bounce">
                <div className="text-center">
                  <div className="text-3xl mb-2">{newBadge.emoji}</div>
                  <div className="font-bold">New Badge Earned!</div>
                  <div className="text-lg">{newBadge.name}</div>
                </div>
              </div>
            )}

            {/* Overall Score */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-32 h-32 rounded-full bg-gradient-to-br from-[#1E3A5F] to-[#6C3FC8] text-white mb-4">
                <div className="text-center">
                  <div className="text-4xl font-bold">{totalScore}</div>
                  <div className="text-sm">out of 50</div>
                </div>
              </div>
              <h2 className="text-2xl font-bold text-[#1E3A5F]">
                {getPerformanceRating(totalScore)}
              </h2>
              <p className="text-muted-foreground">
                Interview Performance for {careerPath}
              </p>
            </div>

            {/* Streak Update Message */}
            {streakMessage && (
              <div className="mb-4 p-3 bg-gradient-to-r from-orange-50 to-red-50 border border-orange-200 rounded-lg text-center">
                <p className="text-orange-700 font-medium">{streakMessage}</p>
              </div>
            )}
            
            {/* XP Earned Message */}
            {xpEarned && (
              <div className={`mb-4 p-4 rounded-lg text-center ${
                leveledUp 
                  ? 'bg-gradient-to-r from-yellow-50 to-amber-50 border-2 border-yellow-400 animate-pulse' 
                  : 'bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200'
              }`}>
                {leveledUp ? (
                  <p className="text-amber-700 font-bold text-lg">
                    🎉 LEVEL UP! You are now a {rankData?.rank_title}! 🚀
                  </p>
                ) : (
                  <p className="text-purple-700 font-medium">
                    +{xpEarned} XP earned! 🎉
                  </p>
                )}
              </div>
            )}

            {/* Question Summaries */}
            <div className="space-y-4 mb-8">
              <h3 className="font-semibold text-lg">Question Summary</h3>
              {answers.map((a, i) => (
                <div key={i} className="bg-card rounded-xl border p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <span className="text-sm text-muted-foreground">Q{i + 1}:</span>
                      <p className="font-medium">{a.question.substring(0, 80)}...</p>
                    </div>
                    <div className={`px-3 py-1 rounded-full text-sm font-medium ${getScoreColor(a.feedback?.score || 0)}`}>
                      {a.feedback?.score || 0}/10
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button onClick={copyResults} variant="outline" className="border-[#1E3A5F] text-[#1E3A5F]">
                <Copy className="w-4 h-4 mr-2" />
                Share Results
              </Button>
              <Button onClick={createChallenge} variant="outline" className="border-[#FF6B35] text-[#FF6B35]">
                🤜 Challenge a Friend
              </Button>
              <Link href="/progress">
                <Button variant="outline">
                  📊 View My Progress
                </Button>
              </Link>
              <Button onClick={() => { setScreen('setup'); setElapsedTime(0); }} className="bg-[#6C3FC8] hover:bg-[#6C3FC8]/90">
                <RefreshCw className="w-4 h-4 mr-2" />
                Practice Again
              </Button>
              <Link href="/analysis">
                <Button variant="outline">
                  Go to Analysis
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
            </div>
          </div>
        )}
      </main>
      
      {/* Challenge Modal */}
      {challengeModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-white mb-2">🤜 Challenge Created!</h3>
            <p className="text-gray-400 text-sm mb-3">Share this link with your friends:</p>
            <input 
              readOnly 
              value={challengeURL}
              aria-label="Challenge link"
              title="Share this link with friends"
              className="w-full bg-gray-700 text-white text-sm rounded-lg px-3 py-2 mb-3" />
            <div className="flex gap-2">
              <button onClick={copyChallengeLink}
                className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm">
                {copied ? '✅ Copied!' : '📋 Copy Link'}
              </button>
              <button onClick={() => setChallengeModal(false)}
                className="px-4 py-2 rounded-lg bg-gray-600 hover:bg-gray-700 text-white text-sm">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
