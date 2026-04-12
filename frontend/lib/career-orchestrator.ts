/**
 * 🎯 CAREER ORCHESTRATOR - Unified Brain Decision System
 * 
 * This is the single source of truth for all AI career decisions.
 * It fuses progress, evolution, readiness, and intelligenceScore into
 * one structured decision system.
 * 
 * Usage:
 *   import { getCareerBrain } from '@/lib/career-orchestrator'
 *   const brain = await getCareerBrain(userId)
 * 
 * DO NOT modify UI - this is pure backend logic layer.
 */

import { 
  fetchCareerIntelligence,
  safeNumber,
  safeString,
  safeArray,
  safeEvolution,
  safeProgress,
  getWeakestPath,
  getStrongestPath,
  hasValidScores,
  type CareerIntelligence,
  type EvolutionData,
  type ProgressData,
  type SafeCareerPath,
  type SafeSession
} from './career-safe'

// ============================================
// TYPE DEFINITIONS - Structured Decision Output
// ============================================

/** Single source of truth for all AI decisions */
export interface CareerBrain {
  // Core metrics
  intelligenceScore: number
  readiness: 'FOUNDATION' | 'GROWTH' | 'JOB_READY'
  confidence: number
  
  // Analysis
  trend: 'Improving' | 'Stable' | 'Declining'
  strengthCount: number
  weaknessCount: number
  
  // Decisions (single source of truth)
  nextAction: string
  focusArea: string
  aiTip: string
  
  // Detailed breakdown
  strongestPath: string | null
  weakestPath: string | null
  totalSessions: number
  averageScore: number
  
  // Raw data for reference
  raw: {
    progress: ProgressData | null
    evolution: EvolutionData | null
  }
}

/** Action priorities based on career state */
export type ActionPriority = 'URGENT' | 'HIGH' | 'MEDIUM' | 'LOW'

/** Detailed recommendation */
export interface Recommendation {
  priority: ActionPriority
  action: string
  reason: string
  targetScore: number
  timeFrame: string
}

// ============================================
// CORE ORCHESTRATOR FUNCTION
// ============================================

/**
 * 🎯 getCareerBrain - Single brain function that fuses all career data
 * 
 * This is the single source of truth for all AI decisions.
 * It replaces all scattered decision logic across pages.
 * 
 * @param userId - The user's ID
 * @returns CareerBrain object with all decisions unified
 */
export async function getCareerBrain(userId: string): Promise<CareerBrain> {
  // Fetch all intelligence data
  const intelligence = await fetchCareerIntelligence(userId)
  
  // Extract safe data
  const progress = intelligence.progress
  const evolution = intelligence.evolution
  
  // Calculate metrics
  const trend = calculateTrend(progress, evolution)
  const confidence = calculateConfidence(evolution, progress)
  const { strengthCount, weaknessCount } = analyzeStrengthsWeaknesses(evolution, progress)
  
  // Make decisions
  const nextAction = determineNextAction(intelligence, trend, confidence)
  const focusArea = determineFocusArea(evolution, progress)
  const aiTip = generateAITip(intelligence, trend, confidence)
  
  // Get path analysis
  const weakest = getWeakestPath(evolution)
  const strongest = getStrongestPath(evolution)
  
  // Calculate session stats
  const sessions = progress?.sessions || []
  const totalSessions = sessions.length
  const averageScore = calculateAverageScore(sessions)
  
  return {
    // Core metrics
    intelligenceScore: intelligence.intelligenceScore,
    readiness: intelligence.readiness,
    confidence,
    
    // Analysis
    trend,
    strengthCount,
    weaknessCount,
    
    // Decisions (single source of truth)
    nextAction,
    focusArea,
    aiTip,
    
    // Detailed breakdown
    strongestPath: strongest?.career_path || null,
    weakestPath: weakest?.career_path || null,
    totalSessions,
    averageScore,
    
    // Raw data for reference
    raw: {
      progress,
      evolution
    }
  }
}

// ============================================
// ANALYTICAL HELPERS
// ============================================

/**
 * Calculate trend from progress and evolution data
 */
function calculateTrend(progress: ProgressData | null, evolution: EvolutionData | null): 'Improving' | 'Stable' | 'Declining' {
  // First try evolution data
  if (evolution?.overall_growth_state) {
    const state = evolution.overall_growth_state
    if (state === 'growing') return 'Improving'
    if (state === 'declining') return 'Declining'
  }
  
  // Fall back to progress data analysis
  const sessions = progress?.sessions || []
  if (sessions.length < 3) return 'Stable'
  
  // Sort by date
  const sorted = [...sessions].sort((a, b) => {
    const dateA = new Date(a.created_at).getTime()
    const dateB = new Date(b.created_at).getTime()
    return dateA - dateB
  })
  
  // Compare first half to second half
  const midpoint = Math.floor(sorted.length / 2)
  const firstHalf = sorted.slice(0, midpoint)
  const secondHalf = sorted.slice(midpoint)
  
  if (firstHalf.length === 0 || secondHalf.length === 0) return 'Stable'
  
  const firstAvg = firstHalf.reduce((sum, s) => sum + safeNumber(s.total_score), 0) / firstHalf.length
  const secondAvg = secondHalf.reduce((sum, s) => sum + safeNumber(s.total_score), 0) / secondHalf.length
  
  if (secondAvg > firstAvg + 3) return 'Improving'
  if (secondAvg < firstAvg - 3) return 'Declining'
  
  return 'Stable'
}

/**
 * Calculate confidence score (0-100)
 */
function calculateConfidence(evolution: EvolutionData | null, progress: ProgressData | null): number {
  let score = 50 // Base confidence
  let weights = 50
  
  // Evolution confidence (40%)
  if (evolution?.career_paths && evolution.career_paths.length > 0) {
    const avgConfidence = evolution.career_paths.reduce(
      (sum, cp) => sum + safeNumber(cp.confidence, 0.5), 0
    ) / evolution.career_paths.length
    score += avgConfidence * 40
    weights += 40
  }
  
  // Session count bonus (10%)
  const sessionCount = progress?.sessions?.length || 0
  if (sessionCount >= 10) {
    score += 10
    weights += 10
  } else if (sessionCount >= 5) {
    score += 5
    weights += 5
  }
  
  return weights > 0 ? Math.round((score / weights) * 100) : 50
}

/**
 * Analyze strengths and weaknesses
 */
function analyzeStrengthsWeaknesses(evolution: EvolutionData | null, progress: ProgressData | null): {
  strengthCount: number
  weaknessCount: number
} {
  let strengthCount = 0
  let weaknessCount = 0
  
  // From evolution
  if (evolution?.career_paths) {
    evolution.career_paths.forEach(path => {
      const score = safeNumber(path.avg_score)
      if (score >= 70) strengthCount++
      else if (score < 40) weaknessCount++
    })
  }
  
  // From progress
  const sessions = progress?.sessions || []
  const careerScores: Record<string, { total: number; count: number }> = {}
  
  sessions.forEach(session => {
    const path = safeString(session.career_path)
    if (!path || path === 'Unknown') return
    
    if (!careerScores[path]) {
      careerScores[path] = { total: 0, count: 0 }
    }
    careerScores[path].total += safeNumber(session.total_score)
    careerScores[path].count += 1
  })
  
  Object.values(careerScores).forEach(data => {
    if (data.count > 0) {
      const avg = data.total / data.count
      if (avg >= 35) strengthCount++ // On 50-point scale, 35+ is good
      if (avg < 20) weaknessCount++
    }
  })
  
  return { strengthCount, weaknessCount }
}

// ============================================
// DECISION HELPERS
// ============================================

/**
 * Determine next action - single source of truth for action decisions
 */
function determineNextAction(
  intelligence: CareerIntelligence,
  trend: 'Improving' | 'Stable' | 'Declining',
  confidence: number
): string {
  const { readiness, intelligenceScore } = intelligence
  
  // First priority: declining trend
  if (trend === 'Declining') {
    return 'Address declining performance. Review fundamentals and schedule more frequent practice.'
  }
  
  // Readiness-based actions
  if (readiness === 'FOUNDATION') {
    if (confidence < 40) {
      return 'Focus on fundamentals and basics practice. Start with core concepts and build foundation.'
    }
    return 'Continue building foundation with consistent practice. Focus on core skills.'
  }
  
  if (readiness === 'GROWTH') {
    if (trend === 'Improving') {
      return 'Maintain momentum. Build on improvements with targeted advanced practice.'
    }
    return 'Improve weak areas with consistent structured practice and daily problem-solving.'
  }
  
  if (readiness === 'JOB_READY') {
    return 'Attempt advanced mock interviews and system design practice to refine performance.'
  }
  
  return 'Continue regular practice to build consistency and improve overall performance.'
}

/**
 * Determine focus area - single source of truth for focus decisions
 */
function determineFocusArea(evolution: EvolutionData | null, progress: ProgressData | null): string {
  const weakest = getWeakestPath(evolution)
  
  if (weakest) {
    return weakest.career_path
  }
  
  // Fall back to progress analysis
  const sessions = progress?.sessions || []
  if (sessions.length === 0) {
    return 'General Practice'
  }
  
  const careerScores: Record<string, { total: number; count: number }> = {}
  
  sessions.forEach(session => {
    const path = safeString(session.career_path)
    if (!path || path === 'Unknown') return
    
    if (!careerScores[path]) {
      careerScores[path] = { total: 0, count: 0 }
    }
    careerScores[path].total += safeNumber(session.total_score)
    careerScores[path].count += 1
  })
  
  // Find lowest scoring path
  let lowestPath = 'General Practice'
  let lowestScore = Infinity
  
  Object.entries(careerScores).forEach(([path, data]) => {
    if (data.count > 0) {
      const avg = data.total / data.count
      if (avg < lowestScore) {
        lowestScore = avg
        lowestPath = path
      }
    }
  })
  
  return lowestPath
}

/**
 * Generate AI tip - single source of truth for tips
 */
function generateAITip(
  intelligence: CareerIntelligence,
  trend: 'Improving' | 'Stable' | 'Declining',
  confidence: number
): string {
  const { intelligenceScore } = intelligence
  
  if (intelligenceScore < 30) {
    return 'Focus on fundamentals + clarity in answers'
  }
  
  if (intelligenceScore < 50) {
    return 'Use STAR method to structure behavioral answers'
  }
  
  if (intelligenceScore < 70) {
    if (trend === 'Improving') {
      return 'Keep building momentum - you are on the right track'
    }
    return 'Focus on consistency + expand knowledge areas'
  }
  
  if (intelligenceScore < 85) {
    return 'Focus on system design depth + confidence building'
  }
  
  return 'Maintain excellence - focus on advanced scenarios and leadership questions'
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Calculate average score from sessions
 */
function calculateAverageScore(sessions: SafeSession[]): number {
  if (sessions.length === 0) return 0
  
  const total = sessions.reduce((sum, s) => sum + safeNumber(s.total_score), 0)
  return Math.round((total / sessions.length) * 2) // Scale to 0-100
}

/**
 * Get recommendations based on career brain state
 */
export function getRecommendations(brain: CareerBrain): Recommendation[] {
  const recommendations: Recommendation[] = []
  
  // Urgent: Declining trend
  if (brain.trend === 'Declining' && brain.totalSessions >= 3) {
    recommendations.push({
      priority: 'URGENT',
      action: 'Address declining performance',
      reason: 'Your recent performance is declining. Review fundamentals immediately.',
      targetScore: 35,
      timeFrame: '1 week'
    })
  }
  
  // High: Low confidence
  if (brain.confidence < 40) {
    recommendations.push({
      priority: 'HIGH',
      action: 'Build foundational skills',
      reason: 'Low confidence detected. Focus on basics before advancing.',
      targetScore: 40,
      timeFrame: '2-4 weeks'
    })
  }
  
  // High: Weak areas exist
  if (brain.weaknessCount > 0) {
    recommendations.push({
      priority: 'HIGH',
      action: `Focus on ${brain.weakestPath || 'weak areas'}`,
      reason: `You have ${brain.weaknessCount} area(s) that need improvement.`,
      targetScore: 40,
      timeFrame: '2-3 weeks'
    })
  }
  
  // Medium: Growth opportunity
  if (brain.strengthCount > 0 && brain.readiness !== 'JOB_READY') {
    recommendations.push({
      priority: 'MEDIUM',
      action: 'Build on strengths',
      reason: `You have ${brain.strengthCount} strong area(s). Leverage them while improving others.`,
      targetScore: 50,
      timeFrame: '1-2 months'
    })
  }
  
  // Medium: Ready for advancement
  if (brain.readiness === 'GROWTH' && brain.trend === 'Improving') {
    recommendations.push({
      priority: 'MEDIUM',
      action: 'Push to job-ready level',
      reason: 'You are on track. Increase practice intensity to reach job-ready.',
      targetScore: 70,
      timeFrame: '1-2 months'
    })
  }
  
  // Low: Maintenance
  if (brain.readiness === 'JOB_READY') {
    recommendations.push({
      priority: 'LOW',
      action: 'Maintain job-ready status',
      reason: 'You are job-ready! Keep practicing to maintain excellence.',
      targetScore: 75,
      timeFrame: 'Ongoing'
    })
  }
  
  return recommendations.sort((a, b) => {
    const priorityOrder = { URGENT: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }
    return priorityOrder[a.priority] - priorityOrder[b.priority]
  })
}

/**
 * Quick check if user is ready for job applications
 */
export function isJobReady(brain: CareerBrain): boolean {
  return (
    brain.readiness === 'JOB_READY' ||
    (brain.intelligenceScore >= 70 && brain.trend === 'Improving' && brain.totalSessions >= 10)
  )
}

/**
 * Get summary text for the brain state
 */
export function getBrainSummary(brain: CareerBrain): string {
  const parts: string[] = []
  
  // Readiness
  parts.push(`Status: ${brain.readiness}`)
  
  // Trend
  parts.push(`Trend: ${brain.trend}`)
  
  // Score
  parts.push(`Score: ${brain.intelligenceScore}/100`)
  
  // Sessions
  parts.push(`${brain.totalSessions} sessions`)
  
  return parts.join(' • ')
}