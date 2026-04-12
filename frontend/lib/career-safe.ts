/**
 * 🎯 CAREER SAFE - Unified Data Contract Layer
 * 
 * This is the single source of truth for all career data safety.
 * All pages (interview, progress, evolution API, profile API) use these
 * safe accessors to prevent null/undefined crashes.
 * 
 * Usage:
 *   import { safeSession, safeNumber, safeArray, fetchCareerIntelligence } from '@/lib/career-safe'
 */

import { supabase } from './supabase'

// ============================================
// TYPE DEFINITIONS
// ============================================

/** Career path with score from evolution API */
export interface SafeCareerPath {
  career_path: string
  avg_score: number
  trend: 'improving' | 'stable' | 'declining'
  volatility: number
  total_sessions: number
  confidence: number
}

/** Session data from progress API */
export interface SafeSession {
  career_path: string
  total_score: number
  created_at: string
}

/** Rank data from profile API */
export interface SafeRank {
  xp: number
  level: number
  rank_title: string
  next_level_xp?: number
  progress_percent?: number
}

/** Streak data */
export interface SafeStreak {
  current_streak: number
  longest_streak: number
  last_practice_date: string | null
  total_sessions: number
}

/** Profile progress data */
export interface SafeProfileProgress {
  total: number
  status: string
  steps: Array<{
    id: string
    value: number
    status: string
  }>
}

/** Evolution data type */
export interface EvolutionData {
  user_id: string
  career_paths: SafeCareerPath[]
  overall_growth_state: 'growing' | 'stagnating' | 'declining'
}

/** Progress data type */
export interface ProgressData {
  sessions: SafeSession[]
  rank: SafeRank | null
  streaks: SafeStreak | null
}

/** Overall career intelligence return type */
export interface CareerIntelligence {
  progress: ProgressData | null
  evolution: EvolutionData | null
  readiness: 'FOUNDATION' | 'GROWTH' | 'JOB_READY'
  intelligenceScore: number
}

/** Loading state enum */
export type CareerLoadingState = 'idle' | 'loading' | 'ready' | 'error'

// ============================================
// SAFE ACCESSORS
// ============================================

/**
 * Safe number converter - prevents NaN and undefined
 */
export function safeNumber(val: unknown, fallback = 0): number {
  if (typeof val === 'number' && !isNaN(val) && isFinite(val)) {
    return val
  }
  return fallback
}

/**
 * Safe string converter - prevents empty strings
 */
export function safeString(val: unknown, fallback = '—'): string {
  if (typeof val === 'string' && val.trim().length > 0) {
    return val.trim()
  }
  return fallback
}

/**
 * Safe array converter - always returns array
 */
export function safeArray<T = unknown>(val: unknown): T[] {
  if (Array.isArray(val)) {
    return val as T[]
  }
  return []
}

/**
 * Safe date converter - returns timestamp
 */
export function safeDate(val: unknown): number {
  if (!val) return 0
  
  try {
    const date = new Date(val as string)
    const timestamp = date.getTime()
    if (!isNaN(timestamp)) {
      return timestamp
    }
  } catch {
    // Fall through
  }
  return 0
}

/**
 * Safe session accessor - always returns valid session object
 */
export function safeSession(session: unknown): SafeSession {
  if (!session || typeof session !== 'object') {
    return {
      career_path: 'Unknown',
      total_score: 0,
      created_at: ''
    }
  }
  
  const s = session as Record<string, unknown>
  return {
    career_path: safeString(s.career_path, 'Unknown'),
    total_score: safeNumber(s.total_score),
    created_at: safeString(s.created_at)
  }
}

/**
 * Safe evolution accessor - always returns valid evolution object
 * Handles empty arrays as valid (new user) not null (error)
 */
export function safeEvolution(evolution: unknown): EvolutionData | null {
  if (!evolution || typeof evolution !== 'object') {
    return null
  }
  
  const e = evolution as Record<string, unknown>
  
  // Handle both null/undefined AND empty array as valid empty state
  if (!e.career_paths) {
    return null
  }
  
  // Empty array is a valid empty state (new user), not null
  if (!Array.isArray(e.career_paths)) {
    return null
  }
  
  // Normalize trend values from backend (could be lowercase or uppercase)
  const normalizeTrend = (trend: unknown): EvolutionData['overall_growth_state'] => {
    const t = safeString(trend, 'stagnating').toLowerCase()
    if (t === 'growing' || t === 'improving') return 'growing'
    if (t === 'declining') return 'declining'
    return 'stagnating'
  }

  return {
    user_id: safeString(e.user_id),
    career_paths: safeArray<SafeCareerPath>(e.career_paths),
    overall_growth_state: normalizeTrend(e.overall_growth_state)
  }
}

/**
 * Safe progress accessor - always returns valid progress object
 * Handles empty arrays as valid (new user) not null (error)
 */
export function safeProgress(progress: unknown): ProgressData | null {
  if (!progress || typeof progress !== 'object') {
    return null
  }
  
  const p = progress as Record<string, unknown>
  
  // Handle sessions - empty array is valid (new user)
  const sessions = Array.isArray(p.sessions) ? p.sessions : []
  
  return {
    sessions: safeArray<SafeSession>(sessions),
    rank: p.rank ? safeRank(p.rank) : null,
    streaks: p.streaks ? safeStreak(p.streaks) : null
  }
}

/**
 * Safe rank accessor
 */
export function safeRank(rank: unknown): SafeRank {
  if (!rank || typeof rank !== 'object') {
    return {
      xp: 0,
      level: 1,
      rank_title: 'Novice'
    }
  }
  
  const r = rank as Record<string, unknown>
  return {
    xp: safeNumber(r.xp),
    level: safeNumber(r.level, 1),
    rank_title: safeString(r.rank_title, 'Novice'),
    next_level_xp: safeNumber(r.next_level_xp),
    progress_percent: safeNumber(r.progress_percent)
  }
}

/**
 * Safe streak accessor
 */
export function safeStreak(streak: unknown): SafeStreak {
  if (!streak || typeof streak !== 'object') {
    return {
      current_streak: 0,
      longest_streak: 0,
      last_practice_date: null,
      total_sessions: 0
    }
  }
  
  const s = streak as Record<string, unknown>
  // Handle last_practice_date - could be ISO string or null
  const lastDate = s.last_practice_date
  let formattedDate: string | null = null
  
  if (lastDate && typeof lastDate === 'string') {
    // Validate it's a valid date string
    const dateObj = new Date(lastDate)
    if (!isNaN(dateObj.getTime())) {
      formattedDate = lastDate
    }
  }
  
  return {
    current_streak: safeNumber(s.current_streak),
    longest_streak: safeNumber(s.longest_streak),
    last_practice_date: formattedDate,
    total_sessions: safeNumber(s.total_sessions)
  }
}

/**
 * Safe profile progress accessor
 */
export function safeProfileProgress(progress: unknown): SafeProfileProgress | null {
  if (!progress || typeof progress !== 'object') {
    return null
  }
  
  const p = progress as Record<string, unknown>
  
  return {
    total: safeNumber(p.total),
    status: safeString(p.status, 'unknown'),
    steps: safeArray(p.steps)
  }
}

// ============================================
// READINESS HELPERS
// ============================================

/**
 * Determine readiness mode from progress
 */
export function determineReadiness(profileProgress: SafeProfileProgress | null): 'FOUNDATION' | 'GROWTH' | 'JOB_READY' {
  if (!profileProgress) return 'FOUNDATION'
  
  if (profileProgress.total >= 75 && profileProgress.status === 'ELITE') {
    return 'JOB_READY'
  } else if (profileProgress.total >= 50) {
    return 'GROWTH'
  }
  return 'FOUNDATION'
}

/**
 * Calculate intelligence score from multiple sources
 */
export function calculateIntelligenceScore(
  progress: ProgressData | null,
  evolution: EvolutionData | null,
  profileProgress: SafeProfileProgress | null
): number {
  let score = 0
  let weights = 0
  
  // Progress sessions (40%)
  if (progress?.sessions && progress.sessions.length > 0) {
    const avgScore = progress.sessions.reduce((sum: number, s: SafeSession) => sum + safeNumber(s.total_score), 0) / progress.sessions.length
    score += (avgScore / 50) * 40
    weights += 40
  }
  
  // Evolution confidence (30%)
  if (evolution?.career_paths && evolution.career_paths.length > 0) {
    const avgConfidence = evolution.career_paths.reduce((sum: number, cp: SafeCareerPath) => sum + safeNumber(cp.confidence), 0) / evolution.career_paths.length
    score += avgConfidence * 0.3
    weights += 30
  }
  
  // Profile completion (30%)
  if (profileProgress) {
    score += profileProgress.total * 0.3
    weights += 30
  }
  
  if (weights > 0) {
    return Math.round((score / weights) * 100)
  }
  
  return 0
}

// ============================================
// VALIDATION HELPERS
// ============================================

/**
 * Check if career path data is valid
 */
export function isValidCareerPath(path: SafeCareerPath | null | undefined): boolean {
  if (!path) return false
  return path.career_path.length > 0 && path.total_sessions > 0
}

/**
 * Check if session data has valid scores
 */
export function hasValidScores(sessions: SafeSession[]): boolean {
  return sessions.some(s => s.total_score > 0)
}

/**
 * Get weakest career path from evolution
 */
export function getWeakestPath(evolution: EvolutionData | null): SafeCareerPath | null {
  if (!evolution?.career_paths || evolution.career_paths.length === 0) {
    return null
  }
  
  return [...evolution.career_paths]
    .sort((a, b) => a.avg_score - b.avg_score)[0] || null
}

/**
 * Get strongest career path from evolution
 */
export function getStrongestPath(evolution: EvolutionData | null): SafeCareerPath | null {
  if (!evolution?.career_paths || evolution.career_paths.length === 0) {
    return null
  }
  
  return [...evolution.career_paths]
    .sort((a, b) => b.avg_score - a.avg_score)[0] || null
}

// ============================================
// STEP 3.2: UNIFIED API LAYER - fetchCareerIntelligence
// ============================================

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// =============================================================================
// DEBUG LOGGING SYSTEM
// =============================================================================

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogEntry {
  level: LogLevel
  message: string
  data?: unknown
  timestamp: string
}

const isDev = process.env.NODE_ENV !== 'production'
const logBuffer: LogEntry[] = []
const MAX_LOG_ENTRIES = 50

function addLog(level: LogLevel, message: string, data?: unknown): void {
  if (!isDev && level === 'debug') return // Skip debug in prod
  
  const entry: LogEntry = {
    level,
    message,
    data: isDev ? data : undefined, // Only log data in dev
    timestamp: new Date().toISOString()
  }
  
  logBuffer.push(entry)
  if (logBuffer.length > MAX_LOG_ENTRIES) {
    logBuffer.shift()
  }
  
  // Console output based on level
  const prefix = `[CareerSafe:${level.toUpperCase()}]`
  switch (level) {
    case 'debug':
      console.debug(prefix, message, data || '')
      break
    case 'info':
      console.info(prefix, message, data || '')
      break
    case 'warn':
      console.warn(prefix, message, data || '')
      break
    case 'error':
      console.error(prefix, message, data || '')
      break
  }
}

export const careerLogger = {
  debug: (msg: string, data?: unknown) => addLog('debug', msg, data),
  info: (msg: string, data?: unknown) => addLog('info', msg, data),
  warn: (msg: string, data?: unknown) => addLog('warn', msg, data),
  error: (msg: string, data?: unknown) => addLog('error', msg, data),
  getLogs: () => [...logBuffer],
  clear: () => logBuffer.length = 0
}

/**
 * 🎯 fetchCareerIntelligence - Single brain API layer
 * 
 * Fetches all career intelligence data in one call:
 * - Progress data from /api/interview/progress/{userId}
 * - Evolution data from /api/career/evolution/{userId}
 * - Profile progress from /api/profile/progress/{userId}
 * 
 * IMPROVED: Handles partial API failures gracefully.
 * If one endpoint fails, we still return what we have.
 */
export async function fetchCareerIntelligence(userId: string): Promise<CareerIntelligence> {
  const defaultResult: CareerIntelligence = {
    progress: null,
    evolution: null,
    readiness: 'FOUNDATION',
    intelligenceScore: 0
  }

  if (!userId) {
    console.warn('[CareerSafe] No userId provided')
    return defaultResult
  }

  // Track which APIs succeeded/failed for debugging
  const apiStatus = {
    progress: false,
    evolution: false,
    profile: false
  }

  try {
    // Get session for authorization header
    const { data: { session } } = await supabase.auth.getSession()
    const authHeaders = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${session?.access_token}`
    }

    // Use Promise.allSettled to handle partial failures
    const [progressResult, evolutionResult, profileResult] = await Promise.allSettled([
      fetch(`${API_URL}/api/interview/progress/${userId}`, { headers: authHeaders }),
      fetch(`${API_URL}/api/career/evolution/${userId}`, { headers: authHeaders }),
      fetch(`${API_URL}/api/profile/progress`, { headers: authHeaders })
    ])

    // Process progress API (most important)
    let progress: ProgressData | null = null
    if (progressResult.status === 'fulfilled' && progressResult.value.ok) {
      try {
        const data = await progressResult.value.json()
        // Check if we got actual data or just error response
        if (data && (data as any).error && !(data as any).sessions?.length) {
          console.warn('[CareerSafe] Progress API returned error response')
        } else {
          progress = safeProgress(data)
          apiStatus.progress = true
        }
      } catch (e) {
        console.warn('[CareerSafe] Failed to parse progress data:', e)
      }
    } else {
      console.warn('[CareerSafe] Progress API failed:', progressResult.status)
    }

    // Process evolution API
    let evolution: EvolutionData | null = null
    if (evolutionResult.status === 'fulfilled' && evolutionResult.value.ok) {
      try {
        const data = await evolutionResult.value.json()
        evolution = safeEvolution(data)
        apiStatus.evolution = true
      } catch (e) {
        console.warn('[CareerSafe] Failed to parse evolution data:', e)
      }
    } else {
      console.warn('[CareerSafe] Evolution API failed:', evolutionResult.status)
    }

    // Process profile progress API
    let profileProgress: SafeProfileProgress | null = null
    if (profileResult.status === 'fulfilled' && profileResult.value.ok) {
      try {
        const data = await profileResult.value.json()
        profileProgress = safeProfileProgress(data)
        apiStatus.profile = true
      } catch (e) {
        console.warn('[CareerSafe] Failed to parse profile progress data:', e)
      }
    } else {
      console.warn('[CareerSafe] Profile progress API failed:', profileResult.status)
    }

    // Log API status for debugging
    console.log('[CareerSafe] API Status:', apiStatus)

    const readiness = determineReadiness(profileProgress)
    const intelligenceScore = calculateIntelligenceScore(progress, evolution, profileProgress)

    return {
      progress,
      evolution,
      readiness,
      intelligenceScore
    }
  } catch (error) {
    console.error('[CareerSafe] Critical failure in fetchCareerIntelligence:', error)
    return defaultResult
  }
}

// ============================================
// STEP 3.3: STANDARDIZED LOADING STATE SYSTEM
// ============================================

/**
 * Check if loading state is considered "loading"
 */
export function isLoading(state: CareerLoadingState): boolean {
  return state === 'loading'
}

/**
 * Check if loading state has data ready
 */
export function isReady(state: CareerLoadingState): boolean {
  return state === 'ready'
}

/**
 * Check if loading state has error
 */
export function hasError(state: CareerLoadingState): boolean {
  return state === 'error'
}

// ============================================
// STEP 3.4: FALLBACK DATA
// ============================================

/**
 * Fallback questions for interview page when no questions available
 * This ensures the interview page NEVER shows a blank screen
 */
export const FALLBACK_QUESTIONS = [
  {
    id: 1,
    question: "Tell me about a challenging project you worked on.",
    type: "behavioral",
    difficulty: "medium",
    hint: "Use the STAR method to structure your answer: Situation, Task, Action, Result."
  },
  {
    id: 2,
    question: "What are your greatest strengths and weaknesses?",
    type: "behavioral",
    difficulty: "easy",
    hint: "Be honest about weaknesses but show you are working on improving them."
  },
  {
    id: 3,
    question: "Where do you see yourself in 5 years?",
    type: "behavioral",
    difficulty: "easy",
    hint: "Show ambition but also stability. Align with the company's growth trajectory."
  }
]

/**
 * Check if questions array is valid, return fallback if not
 */
export function getValidQuestions(questions: unknown): typeof FALLBACK_QUESTIONS {
  const validQuestions = safeArray<{id: number; question: string; type: string; difficulty: string; hint: string}>(questions)
  if (validQuestions.length === 0) {
    return FALLBACK_QUESTIONS
  }
  return validQuestions as typeof FALLBACK_QUESTIONS
}

/**
 * Empty progress data structure for fallback
 */
export const EMPTY_PROGRESS_DATA: ProgressData = {
  sessions: [],
  rank: { xp: 0, level: 1, rank_title: 'Novice' },
  streaks: { current_streak: 0, longest_streak: 0, last_practice_date: null, total_sessions: 0 }
}

/**
 * Empty evolution data structure for fallback
 */
export const EMPTY_EVOLUTION_DATA: EvolutionData = {
  user_id: '',
  career_paths: [],
  overall_growth_state: 'stagnating'
}

// ============================================
// STEP 6.7: DEBUG MODE FLAG
// ============================================

/**
 * DEBUG MODE FLAG
 * Set to true in browser console to see career brain logs
 * Usage: In console type: window.__DEV_SHOW_CAREER_BRAIN = true
 */
export function enableBrainDebug() {
  if (typeof window !== 'undefined') {
    (window as any).__DEV_SHOW_CAREER_BRAIN = true
    console.log('%c🎯 Career Brain Debug Mode Enabled', 'color: #6C3FC8; font-size: 14px; font-weight: bold;')
  }
}