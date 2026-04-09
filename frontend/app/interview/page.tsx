'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import Navbar from '@/components/Navbar'
import { toast } from 'sonner'
import { 
  Brain, Loader2, ChevronRight, CheckCircle, XCircle,
  Lightbulb, ArrowRight, Copy, RefreshCw, MessageSquare, Mic, MicOff, Volume2,
  Zap, Trophy, Target, Sparkles, Clock, AlertTriangle, Play, Square, MoreHorizontal
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
      if (questionTimer) clearInterval(questionTimer)
    }
  }, [timerInterval, questionTimer])

  // Initialize speech recognition
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
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`)
      }
      const data = await response.json()
      if (data.questions && data.questions.length > 0) {
        setQuestions(data.questions)
        setCurrentQuestion(0)
        setAnswers([])
        setAnswer('')
        setScreen('interview')
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

  const handleTimeUp = async () => {
    if (questionTimer) {
      clearInterval(questionTimer)
      setQuestionTimer(null)
    }
    setShowTimeUpMsg(true)
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
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`)
      }
      const feedback = await response.json()
      const newAnswer: Answer = {
        question: questions[currentQuestion].question,
        answer,
        feedback
      }
      const updatedAnswers = [...answers, newAnswer]
      setAnswers(updatedAnswers)
      setVoiceStatus('idle')
      setUsedVoiceInput(false)
      setCommScore(null)
      setTimeout(() => {
        setShowTimeUpMsg(false)
        if (currentQuestion < questions.length - 1) {
          setCurrentQuestion(prev => prev + 1)
          setAnswer('')
          setShowHint(false)
          setQuestionTimeLeft(120)
        } else {
          finishInterview(updatedAnswers)
        }
      }, 1500)
    } catch (err) {
      console.error('Error submitting answer:', err)
      toast.error("Failed to submit answer. Please try again.")
    } finally {
      setSubmitting(false)
    }
  }

  const submitAnswer = async () => {
    if (!user) return
    if (questionTimer) {
      clearInterval(questionTimer)
      setQuestionTimer(null)
    }
    if (!answer.trim()) {
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
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`)
      }
      const feedback = await response.json()
      const newAnswer: Answer = {
        question: questions[currentQuestion].question,
        answer,
        feedback
      }
      const updatedAnswers = [...answers, newAnswer]
      setAnswers(updatedAnswers)
      if (currentQuestion < questions.length - 1) {
        setCurrentQuestion(prev => prev + 1)
        setAnswer('')
        setShowHint(false)
        setVoiceStatus('idle')
        setUsedVoiceInput(false)
        setCommScore(null)
      } else {
        finishInterview(updatedAnswers)
      }
    } catch (err) {
      console.error('Error submitting answer:', err)
      toast.error("Failed to submit answer. Please try again.")
      setSubmitting(false)
    } finally {
      // State reset handled in catch block
    }
  }

  const finishInterview = async (finalAnswers?: Answer[]) => {
    if (!user) return
    const answersToUse = finalAnswers || answers
    if (timerInterval) {
      clearInterval(timerInterval)
      setTimerInterval(null)
    }
    const total = answersToUse.reduce((sum, a) => sum + (a.feedback?.score || 0), 0)
    setTotalScore(total)
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
      const streakResponse = await fetch(`${apiUrl}/api/streaks/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: user.id })
      })
      if (streakResponse.ok) {
        const sData = await streakResponse.json()
        setStreakData({
          current_streak: sData.current_streak,
          longest_streak: sData.longest_streak,
          last_practice_date: sData.last_practice_date,
          total_sessions: sData.total_sessions
        })
        setStreakMessage(sData.message)
      }
      const rankResponse = await fetch(`${apiUrl}/api/ranks/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: user.id, score: total })
      })
      if (rankResponse.ok) {
        const rData = await rankResponse.json()
        setRankData({
          xp: rData.xp,
          level: rData.level,
          rank_title: rData.rank_title,
          next_level_xp: rData.next_level_xp,
          progress_percent: ((rData.xp % 100) / 100) * 100
        })
        setXpEarned(rData.xp_earned)
        setLeveledUp(rData.leveled_up)
      }
    } catch (err) { console.error(err) }
    setScreen('results')
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-green-400 bg-green-500/10 border-green-500/20'
    if (score >= 5) return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20'
    return 'text-red-400 bg-red-500/10 border-red-500/20'
  }

  const getPerformanceRating = (score: number) => {
    const percentage = (score / 50) * 100
    if (percentage >= 80) return 'Elite Performance'
    if (percentage >= 60) return 'Strong Contender'
    return 'Growth Phase'
  }

  const calculateCommScore = useCallback((text: string) => {
    const fillerWords = ['um', 'uh', 'like', 'you know', 'basically', 'literally', 'actually', 'sort of', 'kind of', 'right', 'okay', 'so yeah']
    const textLower = text.toLowerCase()
    const fillers: Record<string, number> = {}
    let fillerCount = 0
    fillerWords.forEach(word => {
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
    let tip = score >= 80 ? 'Masterful delivery! 🎙️' : 'Try pausing briefly instead of using fillers.'
    return { score, fillers, tip }
  }, [])

  const toggleVoice = async () => {
    if (!recognition) return
    if (isRecording) {
      recognition.stop()
      setIsRecording(false)
      setVoiceStatus('done')
      if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop()
    } else {
      setAnswer('')
      setAudioURL(null)
      setAudioChunks([])
      if (audioSupported) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
          const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
          const chunks: Blob[] = []
          recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data) }
          recorder.onstop = () => {
            if (chunks.length > 0) {
              const blob = new Blob(chunks, { type: 'audio/webm' })
              setAudioURL(URL.createObjectURL(blob))
              setAudioChunks(chunks)
            }
            stream.getTracks().forEach(track => track.stop())
          }
          recorder.start()
          setMediaRecorder(recorder)
        } catch (err) { 
          console.log(err)
          toast.error("Voice feature failed. Please try again.")
          setIsRecording(false)
        }
      }
      recognition.start()
      setIsRecording(true)
      setVoiceStatus('listening')
    }
  }

  const speakQuestion = () => {
    if (!speechSupported || !questions[currentQuestion]) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(questions[currentQuestion].question)
    utterance.lang = 'en-US'
    utterance.rate = 0.95
    utterance.onstart = () => setIsSpeaking(true)
    utterance.onend = () => setIsSpeaking(false)
    window.speechSynthesis.speak(utterance)
  }

  const fetchCoachingHint = async () => {
    setHintLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/interview/question-hint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: questions[currentQuestion].question, career_path: careerPath })
      })
      const data = await response.json()
      setCoachingHint(data)
    } catch (err) { 
      console.error(err)
      toast.error("Failed to fetch hint. Please try again.")
    }
    finally { setHintLoading(false) }
  }

  // Simulation Timer Logic
  useEffect(() => {
    if (simMode && screen === 'interview' && questions.length > 0) {
      setQuestionTimeLeft(120)
      if (questionTimer) clearInterval(questionTimer)
      const timer = setInterval(() => {
        setQuestionTimeLeft(prev => {
          if (prev <= 1) {
            handleTimeUp()
            return 0
          }
          return prev - 1
        })
      }, 1000)
      setQuestionTimer(timer)
      return () => clearInterval(timer)
    }
  }, [currentQuestion, simMode, screen, questions.length])

  // Communication score update
  useEffect(() => {
    if (voiceStatus === 'done' && answer.trim()) {
      setUsedVoiceInput(true)
      setCommScore(calculateCommScore(answer))
    }
  }, [voiceStatus, calculateCommScore])

  // Auto-speak question
  useEffect(() => {
    if (screen === 'interview' && questions.length > 0) {
      setCoachingHint(null)
      setShowCoachingHint(false)
      if (speechSupported) setTimeout(speakQuestion, 500)
    }
  }, [currentQuestion, screen, questions.length, speechSupported])

  const copyResults = () => {
    const text = `I just finished an AI Interview for ${careerPath} and scored ${totalScore}/50! Check out AI Career Navigator!`
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const createChallenge = () => {
    const url = `${window.location.origin}/interview?challenge=${user?.id}&score=${totalScore}`
    setChallengeURL(url)
    setChallengeModal(true)
  }

  const copyChallengeLink = () => {
    navigator.clipboard.writeText(challengeURL)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const togglePlayback = () => {
    if (!audioURL) return
    if (isPlaying) {
      setIsPlaying(false)
    } else {
      const audio = new Audio(audioURL)
      audio.onended = () => setIsPlaying(false)
      audio.play()
      setIsPlaying(true)
    }
  }

  if (loading && screen === 'setup') {
    return (
      <div className="min-h-screen bg-[#0F172A] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary-violet mx-auto mb-4" />
          <p className="text-slate-400 font-medium tracking-wide">Initializing Coach...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0F172A] text-white">
      <Navbar />
      
      {/* Header Badges */}
      {(streakData || rankData) && (
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="sticky top-[64px] z-40 flex items-center justify-center gap-6 py-3 px-4 bg-[#1E293B]/80 backdrop-blur-md border-b border-white/5"
        >
          {streakData && (
            <div className="flex items-center gap-2 group">
              <div className={`p-2 rounded-full ${streakData.current_streak > 0 ? 'bg-orange-500/20 shadow-[0_0_15px_rgba(249,115,22,0.3)]' : 'bg-slate-700/50'}`}>
                <Zap className={`w-5 h-5 ${streakData.current_streak > 0 ? 'text-orange-400' : 'text-slate-400'}`} />
              </div>
              <div className="text-sm font-black uppercase tracking-widest text-slate-300">
                {streakData.current_streak} Day <span className="text-orange-400">Streak</span>
              </div>
            </div>
          )}
          {rankData && (
            <div className="flex items-center gap-4 border-l border-white/10 pl-6">
              <div className="text-sm font-black uppercase tracking-widest">
                <span className="text-primary-violet">{rankData.rank_title}</span>
                <span className="text-slate-500 ml-2">Lvl {rankData.level}</span>
              </div>
              <div className="w-32 h-2 bg-slate-800 rounded-full overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${rankData.progress_percent}%` }}
                  className="h-full bg-gradient-to-r from-primary-violet to-purple-400"
                />
              </div>
            </div>
          )}
        </motion.div>
      )}

      <main className="container mx-auto px-4 py-12 max-w-5xl">
        <AnimatePresence mode="wait">
          {/* SETUP SCREEN */}
          {screen === 'setup' && (
            <motion.div 
               key="setup"
               initial={{ opacity: 0, scale: 0.95 }}
               animate={{ opacity: 1, scale: 1 }}
               exit={{ opacity: 0, scale: 1.05 }}
               className="max-w-2xl mx-auto"
            >
              <div className="text-center mb-12">
                <h1 className="text-5xl font-black text-white mb-4 tracking-tighter leading-tight">
                  Premium AI <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-violet to-purple-400">Coach</span>
                </h1>
                <p className="text-slate-400 text-lg font-medium">Practice with personalized intelligence based on your verified maturity.</p>
              </div>

              <div className="bg-[#1E293B] rounded-3xl p-8 border border-white/5 shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 right-0 p-8 opacity-5">
                   <Brain className="w-48 h-48" />
                </div>
                
                <div className="relative space-y-8">
                  {/* Career Selector */}
                  <div className="space-y-3">
                    <label htmlFor="career-path" className="text-xs font-black uppercase tracking-widest text-slate-500 flex items-center gap-2">
                       <Target className="w-4 h-4" /> Target Career Path
                    </label>
                    <select
                      id="career-path"
                      value={careerPath}
                      onChange={(e) => setCareerPath(e.target.value)}
                      className="w-full bg-[#0F172A] p-4 text-white rounded-xl border border-white/10 focus:ring-2 focus:ring-primary-violet outline-none appearance-none font-bold"
                    >
                      {careerPaths.map((path, i) => (
                        <option key={i} value={path}>{path}</option>
                      ))}
                    </select>
                  </div>

                  {/* Difficulty */}
                  <div className="space-y-3">
                    <label className="text-xs font-black uppercase tracking-widest text-slate-500">Analysis Depth</label>
                    <div className="flex gap-3">
                      {['easy', 'medium', 'hard'].map((d) => (
                        <button
                          key={d}
                          onClick={() => setDifficulty(d)}
                          className={`flex-1 py-4 rounded-xl font-black uppercase tracking-tighter text-sm transition-all border-2 ${
                            difficulty === d 
                              ? 'bg-primary-violet border-primary-violet text-white shadow-[0_0_20px_rgba(108,63,200,0.3)]' 
                              : 'bg-[#0F172A] border-white/5 text-slate-500 hover:border-white/20'
                          }`}
                        >
                          {d}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Interviewer Personas */}
                  <div className="space-y-3">
                    <label className="text-xs font-black uppercase tracking-widest text-slate-500">Interviewer DNA</label>
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        { id: 'friendly', e: '😊', title: 'Empathetic', d: 'Warm support' },
                        { id: 'strict', e: '😐', title: 'Technical', d: 'Point blank' },
                        { id: 'google', e: '😈', title: 'FAANG', d: 'Stress depth' }
                      ].map((p) => (
                        <button
                          key={p.id}
                          onClick={() => setPersonality(p.id)}
                          className={`p-4 rounded-2xl border-2 text-center transition-all ${
                            personality === p.id
                              ? 'bg-primary-violet/10 border-primary-violet shadow-[0_0_15px_rgba(108,63,200,0.2)]'
                              : 'bg-[#0F172A] border-white/5 grayscale opacity-50 hover:opacity-100 hover:grayscale-0'
                          }`}
                        >
                          <div className="text-3xl mb-2">{p.e}</div>
                          <div className="text-[10px] font-black uppercase tracking-widest mb-1 text-white">{p.title}</div>
                          <div className="text-[9px] text-slate-500 font-bold">{p.d}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Modes */}
                  <div className="flex gap-3">
                     {[
                       { id: false, icon: Target, label: 'Practice', sub: 'Relaxed session', color: 'bg-primary-violet' },
                       { id: true, icon: Zap, label: 'Simulation', sub: 'Real pressure', color: 'bg-orange-500' }
                     ].map((m) => (
                       <button
                         key={String(m.id)}
                         onClick={() => setSimMode(m.id)}
                         className={`flex-1 p-5 rounded-2xl border-2 text-left transition-all relative overflow-hidden group ${
                           simMode === m.id
                             ? `border-white/20 ${m.color}/10 shadow-xl`
                             : 'bg-[#0F172A] border-white/5 opacity-50'
                         }`}
                       >
                         {simMode === m.id && <div className={`absolute top-0 right-0 w-16 h-16 ${m.color} opacity-10 rounded-full blur-2xl -translate-y-1/2 translate-x-1/2`} />}
                         <div className="flex items-center gap-3 mb-1">
                           <m.icon className={`w-5 h-5 ${simMode === m.id ? 'text-white' : 'text-slate-400'}`} />
                           <span className="font-black text-sm uppercase tracking-widest">{m.label}</span>
                         </div>
                         <div className="text-[10px] font-bold text-slate-500">{m.sub}</div>
                       </button>
                     ))}
                  </div>

                  <Button 
                    onClick={startInterview}
                    disabled={loading}
                    className="w-full bg-gradient-to-r from-primary-violet to-purple-400 hover:scale-[1.02] active:scale-95 transition-all h-16 rounded-2xl text-xl font-black uppercase tracking-tighter"
                  >
                    {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : 'Launch Interview'}
                  </Button>
                </div>
              </div>
            </motion.div>
          )}

          {/* INTERVIEW SCREEN */}
          {screen === 'interview' && questions.length > 0 && (
            <motion.div 
               key="interview"
               initial={{ opacity: 0, x: 20 }}
               animate={{ opacity: 1, x: 0 }}
               exit={{ opacity: 0, x: -20 }}
               className="max-w-3xl mx-auto space-y-8"
            >
              {/* Timeline Header */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="px-4 py-1.5 bg-primary-violet/20 border border-primary-violet/30 rounded-full text-xs font-black text-primary-violet uppercase tracking-widest">
                       Phase {currentQuestion + 1} / {questions.length}
                    </div>
                    {simMode && (
                      <div className="px-4 py-1.5 bg-orange-500/20 border border-orange-500/30 rounded-full text-xs font-black text-orange-400 uppercase tracking-widest flex items-center gap-2">
                        <Zap className="w-3 h-3" /> Simulated
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-slate-400 font-bold">
                    <Clock className="w-4 h-4" />
                    {formatTime(elapsedTime)}
                  </div>
                </div>
                {/* Progress bar */}
                <div className="h-3 bg-slate-800 rounded-full overflow-hidden flex gap-0.5">
                   {questions.map((_, i) => (
                      <div 
                        key={i} 
                        className={`h-full flex-1 transition-all duration-700 ${
                          i < currentQuestion ? 'bg-primary-violet' : 
                          i === currentQuestion ? 'bg-primary-violet/50 animate-pulse' : 
                          'bg-slate-700/50'
                        }`} 
                      />
                   ))}
                </div>
              </div>

              {/* Sim Timer Gradient */}
              {simMode && (
                <div className="bg-[#1E293B] p-6 rounded-3xl border border-white/5">
                   <div className="flex justify-between items-baseline mb-3">
                      <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Answer Threshold</span>
                      <span className={`text-2xl font-black tracking-tighter ${
                        questionTimeLeft > 60 ? 'text-green-400' : questionTimeLeft > 20 ? 'text-yellow-400' : 'text-red-500 animate-pulse'
                      }`}>
                         {formatTime(questionTimeLeft)}
                      </span>
                   </div>
                   <div className="h-2 w-full bg-[#0F172A] rounded-full overflow-hidden">
                      <motion.div 
                        initial={false}
                        animate={{ width: `${(questionTimeLeft / 120) * 100}%` }}
                        className={`h-full ${
                          questionTimeLeft > 60 ? 'bg-green-500' : questionTimeLeft > 20 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                      />
                   </div>
                </div>
              )}

              {/* Question Card */}
              <div className="bg-[#1E293B] rounded-3xl p-10 border border-white/5 border-l-8 border-l-primary-violet relative overflow-hidden group">
                <div className="relative z-10">
                  <div className="flex items-center gap-4 mb-6">
                    <div className="bg-primary-violet/20 px-4 py-1 rounded-lg text-[10px] font-black text-primary-violet uppercase tracking-widest">
                       {questions[currentQuestion].type}
                    </div>
                    {speechSupported && (
                      <button onClick={speakQuestion} aria-label="Read question aloud" className={`p-2 rounded-xl transition-all ${isSpeaking ? 'bg-primary-violet text-white shadow-lg' : 'bg-slate-800 text-slate-400 hover:text-white'}`}>
                        <Volume2 className="w-5 h-5" />
                      </button>
                    )}
                  </div>
                  <h2 className="text-3xl font-black leading-tight text-white mb-8 group-hover:scale-[1.01] transition-transform origin-left">
                    {questions[currentQuestion].question}
                  </h2>

                  {/* Coaching Hints */}
                  <AnimatePresence>
                  {!simMode && showCoachingHint && (
                    <motion.div 
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      className="mb-8 p-6 bg-[#0F172A] rounded-2xl border border-primary-violet/20 space-y-4"
                    >
                      {hintLoading ? (
                        <div className="flex items-center gap-3 text-slate-400 italic">
                          <Loader2 className="w-5 h-5 animate-spin text-primary-violet" /> Decoding strategy...
                        </div>
                      ) : coachingHint ? (
                        <div className="space-y-4">
                          <div className="flex items-center gap-2 text-primary-violet">
                            <Sparkles className="w-5 h-5" />
                            <span className="text-sm font-black uppercase tracking-widest">Strategic Intel</span>
                          </div>
                          <div>
                            <span className="text-[10px] font-black text-slate-500 uppercase">Core Objective</span>
                            <p className="text-sm text-slate-100 mt-1">{coachingHint.looking_for}</p>
                          </div>
                          <div>
                            <span className="text-[10px] font-black text-slate-500 uppercase">Optimal Structure</span>
                            <p className="text-sm text-slate-300 mt-1 italic">"{coachingHint.structure}"</p>
                          </div>
                        </div>
                      ) : null}
                    </motion.div>
                  )}
                  </AnimatePresence>
                  
                  {/* Textarea */}
                  <div className="relative">
                    <textarea
                      value={answer}
                      onChange={(e) => setAnswer(e.target.value)}
                      placeholder="Synthesize your response..."
                      aria-label="Your answer to the interview question"
                      className="w-full bg-[#0F172A] p-8 rounded-2xl border border-white/5 focus:border-primary-violet/50 focus:ring-4 focus:ring-primary-violet/10 outline-none min-h-[250px] text-lg font-medium leading-relaxed"
                    />
                    {isRecording && (
                      <div className="absolute inset-0 bg-primary-violet/5 flex items-center justify-center rounded-2xl border-4 border-dashed border-primary-violet/40 pointer-events-none">
                         <div className="flex flex-col items-center gap-3">
                            <Mic className="w-12 h-12 text-primary-violet animate-pulse" />
                            <span className="text-xs font-black uppercase tracking-widest text-primary-violet">Listening to Intel...</span>
                         </div>
                      </div>
                    )}
                  </div>

                  {/* Comm Score Bubble */}
                  {!simMode && usedVoiceInput && commScore && (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-4 p-4 bg-slate-900 rounded-xl border border-white/5 flex items-center justify-between">
                       <div className="flex items-center gap-3">
                          <div className="text-2xl">🎙️</div>
                          <div>
                             <div className="text-[10px] font-black uppercase tracking-widest text-slate-500">Comm Signal</div>
                             <div className="text-sm font-bold text-slate-100">{commScore.tip}</div>
                          </div>
                       </div>
                       <div className="text-2xl font-black text-primary-violet">{commScore.score}</div>
                    </motion.div>
                  )}

                  {/* Bottom Actions */}
                  <div className="mt-8 flex items-center justify-between pt-8 border-t border-white/5">
                    <div className="flex gap-4">
                      <button 
                        onClick={toggleVoice} 
                        className={`flex items-center gap-3 px-6 py-3 rounded-xl font-black uppercase tracking-tighter text-sm transition-all shadow-lg ${
                          isRecording ? 'bg-red-500/20 text-red-400 border border-red-500/50 shadow-[0_0_20px_rgba(239,68,68,0.3)] animate-pulse' : 'bg-slate-800 text-slate-300 border border-white/5 hover:border-white/20'
                        }`}
                      >
                         {isRecording ? <Square className="w-4 h-4 border-2 border-red-400" /> : <Mic className="w-4 h-4" />}
                         {isRecording ? 'Capturing' : 'Voice Input'}
                      </button>
                      {!simMode && (
                        <button onClick={() => setShowCoachingHint(!showCoachingHint)} className={`flex items-center gap-3 px-6 py-3 rounded-xl font-black uppercase tracking-tighter text-sm border-2 transition-all ${showCoachingHint ? 'bg-primary-violet border-primary-violet text-white shadow-xl' : 'bg-transparent border-white/10 text-slate-400 hover:border-white/30'}`}>
                           <Lightbulb className="w-4 h-4" /> Coaching
                        </button>
                      )}
                    </div>

                    <Button 
                      onClick={submitAnswer}
                      disabled={submitting || !answer.trim()}
                      className="bg-gradient-to-r from-primary-violet to-purple-400 px-10 py-7 text-lg font-black uppercase tracking-tighter rounded-2xl shadow-2xl hover:scale-105 active:scale-95 transition-all disabled:opacity-50"
                    >
                      {submitting ? <Loader2 className="w-6 h-6 animate-spin" /> : 'Sumbit Wave'}
                    </Button>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* RESULTS SCREEN */}
          {screen === 'results' && (
            <motion.div 
               key="results"
               initial={{ opacity: 0, y: 30 }}
               animate={{ opacity: 1, y: 0 }}
               className="max-w-4xl mx-auto space-y-12 pb-20"
            >
              {/* Score Visualization */}
              <div className="bg-[#1E293B] rounded-3xl p-16 border border-white/5 text-center shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-primary-violet opacity-5 rounded-full blur-[100px]" />
                
                <div className="relative flex flex-col items-center">
                  <div className="relative w-56 h-56 mb-10">
                    <svg className="w-full h-full transform -rotate-90">
                      <circle cx="112" cy="112" r="100" stroke="currentColor" strokeWidth="12" fill="transparent" className="text-slate-800" />
                      <motion.circle 
                        cx="112" cy="112" r="100" 
                        stroke="currentColor" strokeWidth="12" 
                        fill="transparent" 
                        strokeLinecap="round"
                        strokeDasharray={2 * Math.PI * 100}
                        strokeDashoffset={2 * Math.PI * 100}
                        animate={{ strokeDashoffset: 2 * Math.PI * 100 * (1 - totalScore / 50) }}
                        transition={{ duration: 2, ease: "easeOut" }}
                        className={totalScore >= 40 ? 'text-yellow-400 drop-shadow-[0_0_15px_rgba(250,204,21,0.4)]' : 'text-primary-violet drop-shadow-[0_0_15px_rgba(108,63,200,0.4)]'}
                      />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                       <span className="text-7xl font-black tracking-tighter text-white">{totalScore}</span>
                       <span className="text-xs font-black uppercase tracking-widest text-slate-500">Total Points</span>
                    </div>
                  </div>
                  
                  <h2 className={`text-5xl font-black tracking-tighter mb-4 ${totalScore >= 40 ? 'text-yellow-400' : 'text-primary-violet'}`}>
                    {getPerformanceRating(totalScore)}
                  </h2>
                  <p className="text-slate-400 font-bold text-lg max-w-md">Precision intelligence verified for {careerPath} maturity profile.</p>
                </div>
              </div>

              {/* Badges Earned? */}
              {newBadge && (
                <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="p-8 bg-gradient-to-r from-yellow-500/20 to-orange-500/20 rounded-3xl border border-yellow-500/30 flex items-center gap-6">
                   <div className="text-6xl">{newBadge.emoji}</div>
                   <div>
                      <div className="text-[10px] font-black uppercase tracking-widest text-yellow-400">Elite Reward Acquired</div>
                      <div className="text-2xl font-black text-white">{newBadge.name}</div>
                   </div>
                </motion.div>
              )}

              {/* Summary Cards */}
              <div className="space-y-4">
                <h3 className="text-lg font-black uppercase tracking-widest text-slate-400 flex items-center gap-3">
                   <MessageSquare className="w-5 h-5" /> Critical Breakdown
                </h3>
                <div className="grid grid-cols-1 gap-4">
                   {answers.map((a, i) => (
                      <div key={i} className="bg-[#1E293B] p-6 rounded-2xl border border-white/5 flex items-center justify-between hover:bg-slate-800 transition-colors">
                         <div className="flex-1">
                            <div className="flex items-center gap-3 mb-1">
                              <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Question {i + 1}</span>
                            </div>
                            <p className="font-bold text-slate-100">{a.question.length > 100 ? a.question.substring(0, 100) + '...' : a.question}</p>
                         </div>
                         <div className={`px-5 py-2 rounded-xl text-xl font-black border-2 ${getScoreColor(a.feedback?.score || 0)}`}>
                            {a.feedback?.score}/10
                         </div>
                      </div>
                   ))}
                </div>
              </div>

              {/* Main Actions */}
              <div className="flex flex-wrap gap-4 justify-center pt-8 border-t border-white/5">
                <Button onClick={() => setScreen('setup')} className="bg-primary-violet hover:bg-primary-violet/90 text-white font-black uppercase tracking-widest px-8 py-6 rounded-xl">
                   <RefreshCw className="w-4 h-4 mr-2" /> Reset Cycle
                </Button>
                <Button onClick={copyResults} variant="outline" className="border-white/10 text-slate-400 hover:text-white font-black uppercase tracking-widest px-8 py-6 rounded-xl">
                   <Copy className="w-4 h-4 mr-2" /> Share Intel
                </Button>
                <Link href="/dashboard" className="flex-1 sm:flex-initial">
                  <Button variant="outline" className="w-full border-white/10 text-slate-400 hover:text-white font-black uppercase tracking-widest py-6 rounded-xl">
                    Back to Terminal
                  </Button>
                </Link>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Challenge Modal */}
      {challengeModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[100]">
          <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="bg-[#1E293B] rounded-3xl p-8 max-w-md w-full mx-4 border border-white/5 shadow-2xl">
            <div className="flex justify-between items-center mb-6">
               <h3 className="text-xl font-black uppercase tracking-tighter text-white flex items-center gap-2">
                 <Trophy className="w-5 h-5 text-yellow-400" /> Challenge Wave
               </h3>
               <button onClick={() => setChallengeModal(false)} aria-label="Close modal" className="text-slate-500 hover:text-white"><XCircle className="w-6 h-6" /></button>
            </div>
            <p className="text-slate-400 text-sm mb-6 font-medium">Broadcast your performance to your network. Top scorers gain verification status.</p>
            <div className="relative mb-6">
              <input 
                readOnly 
                value={challengeURL}
                aria-label="Challenge URL"
                className="w-full bg-[#0F172A] text-white text-xs rounded-xl px-4 py-3 border border-white/10 pr-12 font-mono" />
              <button onClick={copyChallengeLink} aria-label="Copy challenge link" className="absolute right-2 top-1.5 p-2 text-primary-violet hover:text-white transition-colors"><Copy className="w-4 h-4" /></button>
            </div>
            <Button onClick={copyChallengeLink} className="w-full bg-primary-violet hover:bg-primary-violet/90 text-white font-bold py-4 rounded-xl">
                {copied ? 'Link Copied!' : 'Broadcast Challenge'}
            </Button>
          </motion.div>
        </div>
      )}
    </div>
  )
}
