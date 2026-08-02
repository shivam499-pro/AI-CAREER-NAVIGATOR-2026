export interface WeaknessEntry {
  category: string
  avgScore: number
  level: 'Weak' | 'Moderate' | 'Strong'
}

export interface InsightResult {
  weaknessMap: WeaknessEntry[]
  trend: 'Improving' | 'Stable' | 'Declining'
  readinessScore: number
  aiSummary: string
}

export interface CopilotResult {
  nextAction: string
  roadmap: {
    mustImprove: string[]
    goodToHave: string[]
  }
  jobReadiness: {
    status: 'Not Ready' | 'Almost Ready' | 'Ready'
    confidence: number
  }
  summary: string
}