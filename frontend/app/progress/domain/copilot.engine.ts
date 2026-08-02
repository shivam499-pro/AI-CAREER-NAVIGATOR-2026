import type {
  InsightResult,
  CopilotResult,
} from './types'

/**
 * Generates AI-powered career copilot recommendations
 * based on the current user analysis.
 *
 * NOTE:
 * During the first refactor pass, copy the exact logic
 * from page.tsx into this function without modifying it.
 */

// Career Copilot AI Decision Layer - Action generator system
export function generateCopilotInsights(analysis: InsightResult, sessionCount: number): CopilotResult {
  const { weaknessMap, trend, readinessScore, aiSummary } = analysis
  
  // FEATURE 1: NEXT ACTION ENGINE
  let nextAction: string
  if (readinessScore < 40) {
    nextAction = 'Focus on fundamentals and basics practice. Start with core Data Structures and Algorithms.'
  } else if (readinessScore < 70) {
    nextAction = 'Improve weak areas with consistent structured practice and daily problem-solving.'
  } else {
    nextAction = 'Attempt advanced mock interviews and system design practice to refine performance.'
  }
  
  // Additional action based on trend if improving or declining
  if (trend === 'Declining' && sessionCount >= 3) {
    nextAction = 'Address declining performance. Review fundamentals and schedule more frequent practice.'
  } else if (trend === 'Improving' && readinessScore >= 50) {
    nextAction = 'Maintain momentum. Build on improvements with targeted advanced practice.'
  }
  
  // FEATURE 2: SKILL GAP ROADMAP ENGINE
  const mustImprove: string[] = []
  const goodToHave: string[] = []
  
  weaknessMap.forEach(entry => {
    if (entry.level === 'Weak') {
      mustImprove.push(entry.category)
    } else if (entry.level === 'Moderate') {
      goodToHave.push(entry.category)
    }
  })
  
  // FEATURE 3: JOB READINESS ENGINE
  let jobStatus: 'Not Ready' | 'Almost Ready' | 'Ready'
  let confidence: number
  
  if (readinessScore < 40) {
    jobStatus = 'Not Ready'
    confidence = Math.max(0, readinessScore)
  } else if (readinessScore < 70) {
    jobStatus = 'Almost Ready'
    confidence = Math.min(70, readinessScore + 15)
  } else {
    jobStatus = 'Ready'
    confidence = Math.min(95, readinessScore + (trend === 'Improving' ? 5 : 0))
  }
  
  // Adjust confidence based on trend
  if (trend === 'Improving') {
    confidence = Math.min(100, confidence + 10)
  } else if (trend === 'Declining') {
    confidence = Math.max(0, confidence - 10)
  }
  
  // Require minimum sessions for higher readiness
  if (sessionCount < 5 && jobStatus === 'Ready') {
    jobStatus = 'Almost Ready'
    confidence = Math.min(65, confidence)
  }
  
  // FEATURE 4: CAREER COPILOT SUMMARY
  let summary: string
  const weakCount = weaknessMap.filter(w => w.level === 'Weak').length
  
  if (jobStatus === 'Not Ready' || (trend === 'Declining' && weakCount >= 2)) {
    summary = 'You are not yet job-ready. Focus on structured practice in weak areas and maintain consistency.'
  } else if (jobStatus === 'Almost Ready') {
    if (trend === 'Improving') {
      summary = 'You are improving steadily. Keep building consistency to reach full job-readiness.'
    } else {
      summary = 'You are close to job-readiness. Focus on consistency and fill remaining skill gaps.'
    }
  } else {
    summary = 'Strong performance detected. You are job-ready. Continue practicing to maintain readiness level.'
  }
  
  return {
    nextAction,
    roadmap: { mustImprove, goodToHave },
    jobReadiness: { status: jobStatus, confidence: Math.min(100, Math.max(0, confidence)) },
    summary
  }
}