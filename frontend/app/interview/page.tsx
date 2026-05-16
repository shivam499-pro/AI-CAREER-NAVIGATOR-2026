'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { AnimatePresence } from 'framer-motion'
import { motion } from 'framer-motion'
import { supabase } from '@/lib/supabase'
import Navbar from '@/components/Navbar'
import { Loader2 } from 'lucide-react'

import { useInterviewSession } from './hooks/useInterviewSession'
import { useVoiceInput } from './hooks/useVoiceInput'
import { useSimTimer } from './hooks/useSimTimer'
import { useWeeklyChallenge } from './hooks/useWeeklyChallenge'
import { getCareerBrain, type CareerBrain } from '@/lib/career-orchestrator'

import SetupScreen from '@/app/interview/components/SetupScreen'
import InterviewScreen from '@/app/interview/components/InterviewScreen'
import ResultsScreen from '@/app/interview/components/ResultsScreen'

export default function InterviewPage() {
  const router = useRouter()
  const [user, setUser] = useState<{ id: string; email: string } | null>(null)
  const [pageLoading, setPageLoading] = useState(true)
  const [careerBrain, setCareerBrain] = useState<CareerBrain | null>(null)

  // ── Weekly challenge ────────────────────────────────────────────────────────
  const weekly = useWeeklyChallenge({ userId: user?.id })

  // ── Core session ────────────────────────────────────────────────────────────
  const session = useInterviewSession({
    user,
    isWeeklyMode: weekly.isWeeklyMode,
    resumeData: weekly.resumeData,
    onSaveProgress: weekly.saveProgress,
    onClearProgress: weekly.clearProgress,
  })

  // ── Voice ───────────────────────────────────────────────────────────────────
  const voice = useVoiceInput({
    onTranscript: (text) => session.setAnswer(prev => prev + ' ' + text),
    currentQuestion: session.questions[session.currentQuestion]?.question || '',
    screen: session.screen,
  })

  // ── Simulation timer ────────────────────────────────────────────────────────
  const timer = useSimTimer({
    enabled: session.simMode,
    screen: session.screen,
    currentQuestion: session.currentQuestion,
    onTimeUp: session.handleTimeUp,
  })

  // ── Auth + career brain ─────────────────────────────────────────────────────
  useEffect(() => {
    const init = async () => {
      const { data: { user: authUser } } = await supabase.auth.getUser()
      if (!authUser) { router.push('/auth/login'); return }
      setUser({ id: authUser.id, email: authUser.email || '' })

      // Load career brain for AI coach panel (non-blocking)
      try {
        const brain = await getCareerBrain(authUser.id)
        setCareerBrain(brain)
      } catch { /* coach panel shows loading state */ }

      setPageLoading(false)
    }
    init()
  }, [router])

  // ── Streak + rank bar (shown at top when data is available) ─────────────────
  const showStatusBar = !!(session.streakData || session.rankData)

  if (pageLoading) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-purple-500 mx-auto mb-4" />
          <p className="text-slate-400 font-medium">Initializing Coach...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0F172A] text-white">
      <Navbar />

      {/* ── Streak + Rank Bar ─────────────────────────────────────────────── */}
      {showStatusBar && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="sticky top-[64px] z-40 flex items-center justify-center gap-6 py-3 px-4 bg-[#1E293B]/80 backdrop-blur-md border-b border-white/5"
        >
          {session.streakData && (
            <div className="flex items-center gap-2">
              <div className={`p-1.5 rounded-full ${session.streakData.current_streak > 0
                ? 'bg-orange-500/20'
                : 'bg-slate-700/50'
                }`}>
                <span className="text-lg">⚡</span>
              </div>
              <span className="text-sm font-black uppercase tracking-widest text-slate-300">
                {session.streakData.current_streak} Day{' '}
                <span className="text-orange-400">Streak</span>
              </span>
            </div>
          )}
          {session.rankData && (
            <div className="flex items-center gap-4 border-l border-white/10 pl-6">
              <span className="text-sm font-black uppercase tracking-widest">
                <span className="text-purple-400">{session.rankData.rank_title}</span>
                <span className="text-slate-500 ml-2">Lvl {session.rankData.level}</span>
              </span>
              <div className="w-28 h-2 bg-slate-800 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${session.rankData.progress_percent}%` }}
                  className="h-full bg-gradient-to-r from-purple-600 to-violet-400 rounded-full"
                />
              </div>
            </div>
          )}
        </motion.div>
      )}

      <main className="container mx-auto px-4 py-12 max-w-5xl">
        <AnimatePresence mode="wait">

          {session.screen === 'setup' && (
            <SetupScreen
              key="setup"
              careerPath={session.careerPath}
              difficulty={session.difficulty}
              personality={session.personality}
              interviewMode={session.interviewMode}
              simMode={session.simMode}
              careerPaths={session.careerPaths}
              pastSessions={session.pastSessions}
              loading={pageLoading}
              setCareerPath={session.setCareerPath}
              setDifficulty={session.setDifficulty}
              setPersonality={session.setPersonality}
              setInterviewMode={session.setInterviewMode}
              setSimMode={session.setSimMode}
              onStart={session.startInterview}
            />
          )}

          {session.screen === 'interview' && session.questions.length > 0 && (
            <InterviewScreen
              key="interview"
              questions={session.questions}
              currentQuestion={session.currentQuestion}
              answer={session.answer}
              submitting={session.submitting}
              elapsedTime={session.elapsedTime}
              messages={session.messages}
              interviewMode={session.interviewMode}
              careerPath={session.careerPath}
              simMode={session.simMode}
              typingBehavior={session.typingBehavior}
              authenticityStatus={session.authenticityStatus}
              setAnswer={session.setAnswer}
              setTypingBehavior={session.setTypingBehavior}
              setPasteAttempted={session.setPasteAttempted}
              isRecording={voice.isRecording}
              voiceStatus={voice.voiceStatus}
              speechSupported={voice.speechSupported}
              isSpeaking={voice.isSpeaking}
              usedVoiceInput={voice.usedVoiceInput}
              commScore={voice.commScore}
              toggleVoice={voice.toggleVoice}
              speakQuestion={voice.speakQuestion}
              simTimeLeft={timer.timeLeft}
              timerColor={timer.timerColor}
              barColor={timer.barColor}
              barWidth={timer.barWidth}
              isUrgent={timer.isUrgent}
              stopTimer={timer.stopTimer}
              weakestPath={careerBrain?.weakestPath || null}
              aiTip={careerBrain?.aiTip || 'Focus on fundamentals'}
              readinessScore={careerBrain?.intelligenceScore || 0}
              brainLoaded={!!careerBrain}
              formatTime={session.formatTime}
              getAiLabel={session.getAiLabel}
              submitAnswer={session.submitAnswer}
              handleTimeUp={session.handleTimeUp}
            />
          )}

          {session.screen === 'results' && (
            <ResultsScreen
              key="results"
              totalScore={session.totalScore}
              careerPath={session.careerPath}
              answers={session.answers}
              interviewMode={session.interviewMode}
              streakData={session.streakData}
              streakMessage={session.streakMessage}
              rankData={session.rankData}
              xpEarned={session.xpEarned}
              leveledUp={session.leveledUp}
              newBadge={session.newBadge}
              isWeeklyMode={weekly.isWeeklyMode}
              challengeRank={session.challengeRank}
              challengeTotalParticipants={session.challengeTotalParticipants}
              getScoreColor={session.getScoreColor}
              getPerformanceRating={session.getPerformanceRating}
              onReset={() => session.setScreen('setup')}
            />
          )}

        </AnimatePresence>
      </main>
    </div>
  )
}