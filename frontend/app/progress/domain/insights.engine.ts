import type { ProgressData } from '@/lib/career-safe'
import type {
  InsightResult,
  WeaknessEntry,
} from './types'

// Safe data accessors - PREVENT NULL CRASHES
export function getSafeSessions(sessions: any): any[] {
  return Array.isArray(sessions) ? sessions : []
}
export function getSafeNum(val: any, fallback = 0): number {
  return typeof val === 'number' && !isNaN(val) ? val : fallback
}
export function getSafeStr(val: any, fallback = '—'): string {
  return typeof val === 'string' && val.trim() ? val : fallback
}
export function safeDate(val: any): number {
  const d = new Date(getSafeStr(val))
  return isNaN(d.getTime()) ? 0 : d.getTime()
}

// AI Intelligence Layer - Analyzes session data to generate career insights
// PHASE 5: Uses safe accessors, no inline logic, debug logging
export function generateInsights(sessions: ProgressData['sessions']): InsightResult {
  const safe = getSafeSessions(sessions)
  
  // Debug logging (temporary, easily removable)
  if (typeof window !== 'undefined') {
    console.log('[AI Progress] Sessions:', safe.length)
  }
  
  if (safe.length === 0) {
    return {
      weaknessMap: [],
      trend: 'Stable',
      readinessScore: 0,
      aiSummary: 'Start your first interview to unlock career insights.'
    }
  }

  // FEATURE 1: WEAKNESS DETECTION ENGINE
  const careerScores: Record<string, { total: number; count: number }> = {}
  
  safe.forEach(session => {
    const careerPath = getSafeStr(session?.career_path)
    if (!careerPath) return
    if (!careerScores[careerPath]) {
      careerScores[careerPath] = { total: 0, count: 0 }
    }
    careerScores[careerPath].total += getSafeNum(session?.total_score)
    careerScores[careerPath].count += 1
  })

  const weaknessMap: WeaknessEntry[] = Object.entries(careerScores)
    .filter(([_, data]) => data.count > 0)
    .map(([career, data]) => {
      const rawAvgScore = Math.round((data.total / data.count) * 2) // Convert to 0-100 scale (score is out of 50)
      // FIX: clamp to the documented 0-100 scale. There is no upstream
      // validation guaranteeing an individual session's total_score stays
      // within its expected 0-50 range, so a corrupted/out-of-range value
      // could otherwise produce an avgScore far outside 0-100 (e.g. 1998),
      // which would still get bucketed as "Strong" below and could render
      // nonsensically anywhere this number is displayed directly (e.g. a
      // percentage label or progress bar width). This is the same class of
      // gap documented in lib/career-safe.ts's calculateIntelligenceScore -
      // this is the second independent place it shows up, suggesting the
      // real fix may belong further upstream (validating total_score at the
      // API boundary) rather than being patched separately in every
      // consumer. Flagging that pattern for the team; clamping here in the
      // meantime since this value is rendered directly.
      const avgScore = Math.min(100, Math.max(0, rawAvgScore))
      let level: 'Weak' | 'Moderate' | 'Strong'
      if (avgScore < 40) {
        level = 'Weak'
      } else if (avgScore <= 70) {
        level = 'Moderate'
      } else {
        level = 'Strong'
      }
      return { category: career, avgScore, level }
    })
    .sort((a, b) => a.avgScore - b.avgScore)

  // FEATURE 2: SKILL TREND ANALYSIS
  const sortedSessions = [...safe].sort(
    (a, b) => safeDate(a?.created_at) - safeDate(b?.created_at)
  )
  const midpoint = Math.floor(sortedSessions.length / 2)
  
  const firstHalf = sortedSessions.slice(0, midpoint)
  const secondHalf = sortedSessions.slice(midpoint)
  
  let trend: 'Improving' | 'Stable' | 'Declining' = 'Stable'
  
  if (firstHalf.length > 0 && secondHalf.length > 0) {
    const firstHalfAvg = firstHalf.reduce((sum, s) => sum + getSafeNum(s?.total_score), 0) / firstHalf.length
    const secondHalfAvg = secondHalf.reduce((sum, s) => sum + getSafeNum(s?.total_score), 0) / secondHalf.length
    
    if (secondHalfAvg > firstHalfAvg + 2) {
      trend = 'Improving'
    } else if (secondHalfAvg < firstHalfAvg - 2) {
      trend = 'Declining'
    }
    // NOTE (documented, not changed): the `else if (safe.length >= 4)` branch
    // below is DEAD CODE. Given midpoint = Math.floor(n/2), both firstHalf
    // and secondHalf are non-empty for every n >= 2, so this branch's
    // condition (`firstHalf.length > 0 && secondHalf.length > 0` being
    // false) can only be true at n=0 or n=1 - and n=0 is already handled by
    // the early return above, while n=1 never satisfies `safe.length >= 4`.
    // No test exercises this branch because no input can reach it; that is
    // correct, not a coverage gap. Left in place since removing it is a
    // refactor decision for the team, not a correctness fix.
  } else if (safe.length >= 4) {
    const recentSessions = sortedSessions.slice(-2)
    const oldestSessions = sortedSessions.slice(0, 2)
    const recentAvg = recentSessions.reduce((sum, s) => sum + (s.total_score ?? 0), 0) / recentSessions.length
    const oldestAvg = oldestSessions.reduce((sum, s) => sum + (s.total_score ?? 0), 0) / oldestSessions.length
    
    if (recentAvg > oldestAvg + 2) {
      trend = 'Improving'
    } else if (recentAvg < oldestAvg - 2) {
      trend = 'Declining'
    }
  }

  // FEATURE 3: CAREER READINESS SCORE
  // Compute a single score (0-100) using avg score, streak, and consistency
  const avgScoreAll = safe.reduce((sum, s) => sum + getSafeNum(s?.total_score), 0 ) / safe.length
  const avgScoreNormalized = (avgScoreAll / 50) * 100 // Normalize to 0-100
  
  // Use session count as consistency factor (max at 10 sessions)
  const consistencyFactor = Math.min(safe.length, 10) * 5 // 0-50 points
  
  // Calculate readiness score with weighted factors
  // NOTE (documented, not changed): these three components can sum to up to
  // 110 (50 from avgScoreNormalized*0.5, 50 from consistencyFactor, 10 from
  // the session-count bonus) before the clamp below caps it at 100. The
  // "50% weight" framing in the comment is therefore not quite literal -
  // the clamp absorbs the overflow rather than the weights summing exactly
  // to 100. Functionally harmless (the clamp is correct and always applied),
  // but worth knowing if this formula is ever retuned.
  const readinessScore = Math.round(
    (avgScoreNormalized * 0.5) + // 50% weight on average score
    (consistencyFactor) + // 0-50 points from consistency
    (Math.min(safe.length, 5) * 2) // Bonus for having 5+ sessions
  )
  // Cap at 100
  const finalReadinessScore = Math.min(100, Math.max(0, readinessScore))

  // Determine label based on score
  // NOTE (documented, not changed): readinessLabel is computed but never
  // included in the returned InsightResult (see ./types.ts) - it is dead
  // output, not a bug, just unused.
  let readinessLabel: string
  if (finalReadinessScore < 40) {
    readinessLabel = 'Beginner'
  } else if (finalReadinessScore < 70) {
    readinessLabel = 'Intermediate'
  } else {
    readinessLabel = 'Advanced'
  }

  // FEATURE 4: AI INSIGHT SUMMARY (RULE-BASED)
  // Generate insight based on weaknessMap, trend, and readiness
  let aiSummary: string
  
  if (safe.length < 3) {
    aiSummary = 'Keep practicing to generate career insights. Complete more interviews to unlock personalized recommendations.'
  } else {
    // Count weak categories
    const weakCategories = weaknessMap.filter(w => w.level === 'Weak')
    const strongCategories = weaknessMap.filter(w => w.level === 'Strong')
    
    if (weakCategories.length >= 2 && trend === 'Declining') {
      aiSummary = `Your performance shows declining results with ${weakCategories.length} areas needing attention. Focus on consistent practice and revisit fundamentals in ${weakCategories[0].category}.`
    } else if (weakCategories.length >= 2) {
      aiSummary = `You have ${weakCategories.length} areas to strengthen: ${weakCategories.map(w => w.category).join(', ')}. Consider focused practice in these categories.`
    } else if (trend === 'Improving' && strongCategories.length >= 2) {
      aiSummary = 'Strong growth detected across multiple categories. Your consistent effort is paying off. Maintain this momentum for best results.'
    } else if (trend === 'Improving') {
      aiSummary = 'You are improving steadily. Keep focusing on regular practice sessions to build on this positive momentum.'
    } else if (trend === 'Declining') {
      aiSummary = 'Your performance is showing a slight decline. Consider revisiting core concepts and scheduling more frequent practice sessions.'
    } else if (sessions.length < 5) {
      // NOTE (documented, not changed): uses the original `sessions` param
      // rather than `safe` (every other branch in this function uses
      // `safe`). Currently provably equivalent: this line is only reached
      // when safe.length >= 3, and safe is only non-empty when `sessions`
      // was already a real array (getSafeSessions returns [] otherwise) -
      // so sessions.length === safe.length on every path that reaches here.
      // Harmless today, but fragile if getSafeSessions' filtering logic
      // ever changes to do more than an Array.isArray check.
      aiSummary = 'Your foundation is developing well. Complete more sessions to get accurate trend analysis and personalized recommendations.'
    } else {
      aiSummary = 'Your performance is stable. Focus on consistency and try expanding into new career paths for well-rounded growth.'
    }
  }

  return {
    weaknessMap,
    trend,
    readinessScore: finalReadinessScore,
    aiSummary
  }
}