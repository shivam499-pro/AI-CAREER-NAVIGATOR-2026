import { generateCopilotInsights } from '../copilot.engine'
import type { InsightResult, WeaknessEntry } from '../types'

// This file does NOT modify generateCopilotInsights's logic. Per the source
// file's own comment ("copy the exact logic from page.tsx into this function
// without modifying it"), this is a verbatim-extracted decision engine likely
// still mirrored in page.tsx. These tests document CURRENT behavior precisely,
// including a confirmed cross-field contradiction (see the dedicated section
// near the bottom) that the team needs to discuss before deciding whether to
// fix it here, in page.tsx, or both.

const weakness = (category: string, level: WeaknessEntry['level'], avgScore = 50): WeaknessEntry => ({
  category,
  avgScore,
  level,
})

const analysis = (overrides: Partial<InsightResult> = {}): InsightResult => ({
  weaknessMap: [],
  trend: 'Stable',
  readinessScore: 50,
  aiSummary: '',
  ...overrides,
})

// ─── FEATURE 1: next action engine ────────────────────────────────────────────

describe('generateCopilotInsights: nextAction (base tier by readinessScore)', () => {
  test('readinessScore < 40 -> fundamentals action', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 39, trend: 'Stable' }), 10)
    expect(result.nextAction).toContain('fundamentals and basics')
  })

  test('readinessScore 40-69 -> improve weak areas action', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 40, trend: 'Stable' }), 10)
    expect(result.nextAction).toContain('Improve weak areas')
  })

  test('readinessScore >= 70 -> advanced practice action', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 70, trend: 'Stable' }), 10)
    expect(result.nextAction).toContain('advanced mock interviews')
  })

  test('boundary: readinessScore exactly 69 is still the mid tier', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 69, trend: 'Stable' }), 10)
    expect(result.nextAction).toContain('Improve weak areas')
  })
})

describe('generateCopilotInsights: nextAction (trend overrides)', () => {
  test('Declining trend with sessionCount >= 3 overrides the base action, regardless of readinessScore', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 90, trend: 'Declining' }), 3)
    expect(result.nextAction).toContain('Address declining performance')
  })

  test('Declining trend with sessionCount < 3 does NOT override (insufficient data to call it a trend)', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 90, trend: 'Declining' }), 2)
    expect(result.nextAction).not.toContain('Address declining performance')
    expect(result.nextAction).toContain('advanced mock interviews')
  })

  test('Improving trend with readinessScore >= 50 overrides the base action with a momentum message', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 50, trend: 'Improving' }), 10)
    expect(result.nextAction).toContain('Maintain momentum')
  })

  test('Improving trend with readinessScore < 50 does NOT override (too early for "momentum" framing)', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 49, trend: 'Improving' }), 10)
    expect(result.nextAction).not.toContain('Maintain momentum')
    expect(result.nextAction).toContain('Improve weak areas')
  })

  test('Declining override takes priority over Improving override if both conditions were somehow true (mutually exclusive trend values make this unreachable, documenting for completeness)', () => {
    // trend can only be one value, so this just confirms the else-if ordering:
    // Declining is checked first, Improving second.
    const result = generateCopilotInsights(analysis({ readinessScore: 90, trend: 'Declining' }), 5)
    expect(result.nextAction).toContain('Address declining performance')
  })
})

// ─── FEATURE 2: skill gap roadmap engine ──────────────────────────────────────

describe('generateCopilotInsights: roadmap (mustImprove / goodToHave)', () => {
  test('"Weak" entries go into mustImprove', () => {
    const result = generateCopilotInsights(analysis({ weaknessMap: [weakness('SQL', 'Weak')] }), 10)
    expect(result.roadmap.mustImprove).toEqual(['SQL'])
    expect(result.roadmap.goodToHave).toEqual([])
  })

  test('"Moderate" entries go into goodToHave', () => {
    const result = generateCopilotInsights(analysis({ weaknessMap: [weakness('System Design', 'Moderate')] }), 10)
    expect(result.roadmap.goodToHave).toEqual(['System Design'])
    expect(result.roadmap.mustImprove).toEqual([])
  })

  test('"Strong" entries are excluded from both lists', () => {
    const result = generateCopilotInsights(analysis({ weaknessMap: [weakness('React', 'Strong')] }), 10)
    expect(result.roadmap.mustImprove).toEqual([])
    expect(result.roadmap.goodToHave).toEqual([])
  })

  test('a mix of all three levels sorts correctly into the two buckets', () => {
    const result = generateCopilotInsights(
      analysis({
        weaknessMap: [weakness('A', 'Strong'), weakness('B', 'Moderate'), weakness('C', 'Weak'), weakness('D', 'Weak')],
      }),
      10
    )
    expect(result.roadmap.mustImprove).toEqual(['C', 'D'])
    expect(result.roadmap.goodToHave).toEqual(['B'])
  })

  test('an empty weaknessMap produces empty roadmap arrays, not an error', () => {
    const result = generateCopilotInsights(analysis({ weaknessMap: [] }), 10)
    expect(result.roadmap.mustImprove).toEqual([])
    expect(result.roadmap.goodToHave).toEqual([])
  })
})

// ─── FEATURE 3: job readiness engine ──────────────────────────────────────────

describe('generateCopilotInsights: jobReadiness status and confidence', () => {
  test('readinessScore < 40 -> Not Ready, confidence equals readinessScore (clamped at 0)', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 20, trend: 'Stable' }), 10)
    expect(result.jobReadiness.status).toBe('Not Ready')
    expect(result.jobReadiness.confidence).toBe(20)
  })

  test('readinessScore 40-69 -> Almost Ready, confidence = readinessScore + 15 (capped at 70)', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 50, trend: 'Stable' }), 10)
    expect(result.jobReadiness.status).toBe('Almost Ready')
    expect(result.jobReadiness.confidence).toBe(65)
  })

  test('readinessScore >= 70, Stable trend -> Ready, confidence = readinessScore (capped at 95)', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 80, trend: 'Stable' }), 10)
    expect(result.jobReadiness.status).toBe('Ready')
    expect(result.jobReadiness.confidence).toBe(80)
  })

  test('readinessScore >= 70, Improving trend gets a +5 bonus before the trend-confidence adjustment', () => {
    // base: min(95, 80+5)=85, then +10 for Improving trend = 95
    const result = generateCopilotInsights(analysis({ readinessScore: 80, trend: 'Improving' }), 10)
    expect(result.jobReadiness.confidence).toBe(95)
  })

  test('Improving trend adds +10 to confidence (capped at 100)', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 20, trend: 'Improving' }), 10)
    // base Not Ready confidence = 20, +10 Improving = 30
    expect(result.jobReadiness.confidence).toBe(30)
  })

  test('Declining trend subtracts 10 from confidence (floored at 0)', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 50, trend: 'Declining' }), 10)
    // base Almost Ready confidence = 65, -10 Declining = 55
    expect(result.jobReadiness.confidence).toBe(55)
  })

  test('confidence never goes below 0 even with a very low score and Declining trend', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 5, trend: 'Declining' }), 10)
    expect(result.jobReadiness.confidence).toBe(0)
  })

  test('confidence never exceeds 100 even with a high score and Improving trend', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 95, trend: 'Improving' }), 10)
    expect(result.jobReadiness.confidence).toBe(100)
  })

  test('sessionCount < 5 downgrades a "Ready" status to "Almost Ready" and caps confidence at 65', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 90, trend: 'Stable' }), 3)
    expect(result.jobReadiness.status).toBe('Almost Ready')
    expect(result.jobReadiness.confidence).toBe(65)
  })

  test('sessionCount >= 5 does NOT downgrade an otherwise-"Ready" status', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 90, trend: 'Stable' }), 5)
    expect(result.jobReadiness.status).toBe('Ready')
  })

  test('the sessionCount floor only applies to "Ready", not to "Almost Ready" or "Not Ready"', () => {
    const almostReady = generateCopilotInsights(analysis({ readinessScore: 50, trend: 'Stable' }), 1)
    expect(almostReady.jobReadiness.status).toBe('Almost Ready')
    expect(almostReady.jobReadiness.confidence).toBe(65) // unaffected by the sessionCount<5 cap, since status wasn't Ready

    const notReady = generateCopilotInsights(analysis({ readinessScore: 10, trend: 'Stable' }), 1)
    expect(notReady.jobReadiness.status).toBe('Not Ready')
  })
})

// ─── FEATURE 4: copilot summary ───────────────────────────────────────────────

describe('generateCopilotInsights: summary text', () => {
  test('Not Ready status always produces the not-ready summary', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 20, trend: 'Stable' }), 10)
    expect(result.summary).toContain('not yet job-ready')
  })

  test('Declining trend with 2+ weak areas forces the not-ready summary even if status is Ready', () => {
    const result = generateCopilotInsights(
      analysis({
        readinessScore: 90,
        trend: 'Declining',
        weaknessMap: [weakness('A', 'Weak'), weakness('B', 'Weak')],
      }),
      10
    )
    expect(result.jobReadiness.status).toBe('Ready') // status itself is unaffected (see contradiction section below)
    expect(result.summary).toContain('not yet job-ready') // but summary IS overridden in this specific case
  })

  test('Declining trend with only 1 weak area does NOT force the not-ready summary', () => {
    const result = generateCopilotInsights(
      analysis({ readinessScore: 90, trend: 'Declining', weaknessMap: [weakness('A', 'Weak')] }),
      10
    )
    expect(result.summary).not.toContain('not yet job-ready')
  })

  test('Almost Ready + Improving trend -> "improving steadily" summary', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 50, trend: 'Improving' }), 10)
    expect(result.summary).toContain('improving steadily')
  })

  test('Almost Ready + non-Improving trend -> "close to job-readiness" summary', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 50, trend: 'Stable' }), 10)
    expect(result.summary).toContain('close to job-readiness')
  })

  test('Ready status (and not the Declining+weakCount>=2 exception) -> "Strong performance" summary', () => {
    const result = generateCopilotInsights(analysis({ readinessScore: 90, trend: 'Stable' }), 10)
    expect(result.summary).toContain('Strong performance detected')
  })
})
describe('generateCopilotInsights: KNOWN GAP - cross-field contradiction on Declining trend', () => {
  test('KNOWN GAP: nextAction says "address declining performance" while jobReadiness.status simultaneously says "Ready"', () => {
    const result = generateCopilotInsights(
      analysis({ readinessScore: 75, trend: 'Declining', weaknessMap: [] }),
      10
    )
    expect(result.nextAction).toContain('Address declining performance')
    expect(result.jobReadiness.status).toBe('Ready')
  })

  test('KNOWN GAP: same contradiction extends to summary when weakCount < 2 - all three fields disagree at once', () => {
    const result = generateCopilotInsights(
      analysis({
        readinessScore: 90,
        trend: 'Declining',
        weaknessMap: [weakness('SQL', 'Weak')], // only 1 weak area - below the weakCount>=2 threshold
      }),
      10
    )
    expect(result.nextAction).toContain('Address declining performance')
    expect(result.jobReadiness.status).toBe('Ready')
    expect(result.summary).toContain('Strong performance detected')
  })

  test('the contradiction resolves correctly ONLY when weakCount >= 2 (summary aligns, but jobReadiness.status still does not)', () => {
    const result = generateCopilotInsights(
      analysis({
        readinessScore: 90,
        trend: 'Declining',
        weaknessMap: [weakness('SQL', 'Weak'), weakness('System Design', 'Weak')],
      }),
      10
    )
    expect(result.nextAction).toContain('Address declining performance')
    expect(result.summary).toContain('not yet job-ready') // summary now agrees with nextAction
    expect(result.jobReadiness.status).toBe('Ready') // ...but status still does not agree with either
  })
})