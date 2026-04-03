'use client'

import { useState, useEffect } from 'react'
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
  
  // Results state
  const [totalScore, setTotalScore] = useState(0)

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        router.push('/auth/login')
        return
      }
      setUser(user)
      await loadUserData(user.id)
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
  }, [voiceStatus])

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
          difficulty
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
    if (!user || !answer.trim()) return
    
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

  const copyResults = () => {
    const text = `🎯 My AI Interview Coach Results

Career: ${careerPath}
Overall Score: ${totalScore}/50 (${getPerformanceRating(totalScore)})

${answers.map((a, i) => `Q${i+1}: ${a.question.substring(0, 50)}... - Score: ${a.feedback?.score || 0}/10`).join('\n')}

Powered by AI Career Navigator`
    
    navigator.clipboard.writeText(text)
  }

  // Toggle voice recording
  const toggleVoice = () => {
    if (!recognition) {
      alert('Voice input not supported in this browser. Please type your answer.')
      return
    }
    
    if (isRecording) {
      recognition.stop()
      setIsRecording(false)
      setVoiceStatus('done')
    } else {
      setAnswer('') // Clear previous answer for new recording
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
  const calculateCommScore = (text: string) => {
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
  }

  // Update communication score when voiceStatus changes to done
  useEffect(() => {
    if (voiceStatus === 'done' && answer.trim()) {
      setUsedVoiceInput(true)
      const scoreResult = calculateCommScore(answer)
      setCommScore(scoreResult)
    }
  }, [voiceStatus, answer])

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

              {/* AI Coaching Hint Card */}
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

              <div className="flex items-center gap-2">
                <textarea
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder="Type your answer here..."
                  className="w-full p-4 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none min-h-[200px]"
                />
              </div>

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
                
                <Button 
                  variant="outline" 
                  onClick={() => setShowHint(!showHint)}
                >
                  <Lightbulb className="w-4 h-4 mr-2" />
                  {showHint ? 'Hide Hint' : 'Show Hint'}
                </Button>
                
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
    </div>
  )
}
