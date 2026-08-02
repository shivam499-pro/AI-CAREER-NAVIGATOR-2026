import { generateInsights, getSafeSessions, getSafeNum, getSafeStr, safeDate } from '../insights.engine'

const session = (career_path: string, total_score: number, created_at: string) => ({
  career_path,
  total_score,
  created_at,
})

// ─── exported safe accessors ──────────────────────────────────────────────────

describe('getSafeSessions', () => {
  test('returns the array unchanged when input is an array', () => {
    expect(getSafeSessions([1, 2, 3])).toEqual([1, 2, 3])
  })

  test('returns an empty array for null, undefined, or non-array input', () => {
    expect(getSafeSessions(null)).toEqual([])
    expect(getSafeSessions(undefined)).toEqual([])
    expect(getSafeSessions('not an array')).toEqual([])
  })
})

describe('getSafeNum', () => {
  test('returns the number when valid', () => {
    expect(getSafeNum(42)).toBe(42)
    expect(getSafeNum(0)).toBe(0)
  })

  test('returns the fallback for NaN, non-numbers, null, or undefined', () => {
    expect(getSafeNum(NaN)).toBe(0)
    expect(getSafeNum('42')).toBe(0)
    expect(getSafeNum(null)).toBe(0)
    expect(getSafeNum(undefined, 5)).toBe(5)
  })
})

describe('getSafeStr', () => {
  test('returns the string when non-empty', () => {
    expect(getSafeStr('hello')).toBe('hello')
  })

  test('returns the fallback for empty/whitespace strings or non-strings', () => {
    expect(getSafeStr('')).toBe('—')
    expect(getSafeStr('   ')).toBe('—')
    expect(getSafeStr(null)).toBe('—')
    expect(getSafeStr(42)).toBe('—')
  })
})

describe('safeDate', () => {
  test('returns a timestamp for a valid date string', () => {
    expect(safeDate('2026-06-20')).toBe(new Date('2026-06-20').getTime())
  })

  test('returns 0 for an invalid or missing date', () => {
    expect(safeDate(null)).toBe(0)
    expect(safeDate('not-a-date')).toBe(0)
  })
})

// ─── generateInsights: empty state ───────────────────────────────────────────

describe('generateInsights: empty state', () => {
  test('returns the empty-state default when given no sessions', () => {
    const result = generateInsights([])
    expect(result).toEqual({
      weaknessMap: [],
      trend: 'Stable',
      readinessScore: 0,
      aiSummary: 'Start your first interview to unlock career insights.',
    })
  })

  test('returns the empty-state default when given null/non-array input', () => {
    const result = generateInsights(null as any)
    expect(result.weaknessMap).toEqual([])
    expect(result.readinessScore).toBe(0)
  })
})

// ─── FEATURE 1: weakness detection engine ────────────────────────────────────

describe('generateInsights: weaknessMap', () => {
  test('groups sessions by career_path and averages their scores (scaled x2 to a 0-100 range)', () => {
    const result = generateInsights([
      session('Backend', 20, '2026-01-01'),
      session('Backend', 30, '2026-01-02'),
    ])
    // avg total_score = 25, *2 = 50
    expect(result.weaknessMap).toEqual([{ category: 'Backend', avgScore: 50, level: 'Moderate' }])
  })

  test('classifies avgScore < 40 as Weak', () => {
    const result = generateInsights([session('Backend', 15, '2026-01-01')]) // 15*2=30
    expect(result.weaknessMap[0].level).toBe('Weak')
  })

  test('classifies avgScore 40-70 (inclusive) as Moderate', () => {
    const result = generateInsights([session('Backend', 35, '2026-01-01')]) // 35*2=70
    expect(result.weaknessMap[0].level).toBe('Moderate')
  })

  test('classifies avgScore > 70 as Strong', () => {
    const result = generateInsights([session('Backend', 36, '2026-01-01')]) // 36*2=72
    expect(result.weaknessMap[0].level).toBe('Strong')
  })

  test('separates multiple career paths into separate entries, sorted ascending by avgScore', () => {
    const result = generateInsights([
      session('Backend', 40, '2026-01-01'), // 80
      session('Frontend', 10, '2026-01-02'), // 20
      session('DevOps', 25, '2026-01-03'), // 50
    ])
    expect(result.weaknessMap.map(w => w.category)).toEqual(['Frontend', 'DevOps', 'Backend'])
  })

  test('a session with an empty/missing career_path is grouped under the "—" fallback category, not silently dropped', () => {
    // getSafeStr('') returns the fallback '—' (a non-empty string), so the
    // `if (!careerPath) return` guard never actually fires for an empty
    // string input - '—' is truthy. This means sessions with no known
    // career path still show up in weaknessMap, just under a placeholder
    // category, rather than being excluded. Arguably more correct than
    // silent exclusion (the data isn't lost), but worth confirming this
    // matches the team's intent for how the progress page should render it.
    const result = generateInsights([
      session('', 50, '2026-01-01'),
      session('Backend', 40, '2026-01-02'),
    ])
    expect(result.weaknessMap).toHaveLength(2)
    expect(result.weaknessMap.map(w => w.category)).toEqual(expect.arrayContaining(['Backend', '—']))
  })

  // REGRESSION GUARD for the avgScore clamping fix.
  test('REGRESSION GUARD: an out-of-range total_score no longer produces an avgScore outside 0-100', () => {
    const result = generateInsights([session('Backend', 999, '2026-01-01')])
    expect(result.weaknessMap[0].avgScore).toBe(100) // clamped, not 1998
  })

  test('REGRESSION GUARD: a negative total_score clamps to 0, not a negative avgScore', () => {
    const result = generateInsights([session('Backend', -50, '2026-01-01')])
    expect(result.weaknessMap[0].avgScore).toBe(0)
  })

  test('a normal in-range total_score is unaffected by the clamp', () => {
    const result = generateInsights([session('Backend', 20, '2026-01-01')])
    expect(result.weaknessMap[0].avgScore).toBe(40) // 20*2, well within 0-100
  })
})

// ─── FEATURE 2: skill trend analysis ──────────────────────────────────────────

describe('generateInsights: trend', () => {
  test('a single session always yields Stable (no second half to compare against)', () => {
    const result = generateInsights([session('Backend', 30, '2026-01-01')])
    expect(result.trend).toBe('Stable')
  })

  test('2 sessions, second clearly higher (>2 point gap) -> Improving', () => {
    const result = generateInsights([
      session('Backend', 10, '2026-01-01'),
      session('Backend', 20, '2026-01-02'),
    ])
    expect(result.trend).toBe('Improving')
  })

  test('2 sessions, second clearly lower -> Declining', () => {
    const result = generateInsights([
      session('Backend', 20, '2026-01-01'),
      session('Backend', 10, '2026-01-02'),
    ])
    expect(result.trend).toBe('Declining')
  })

  test('2 sessions within the +/-2 threshold -> Stable', () => {
    const result = generateInsights([
      session('Backend', 20, '2026-01-01'),
      session('Backend', 21, '2026-01-02'),
    ])
    expect(result.trend).toBe('Stable')
  })

  test('sessions are sorted by created_at before splitting into halves, regardless of array order', () => {
    const result = generateInsights([
      session('Backend', 20, '2026-01-04'), // newest, highest score
      session('Backend', 5, '2026-01-01'), // oldest, lowest score
      session('Backend', 5, '2026-01-02'),
      session('Backend', 20, '2026-01-03'),
    ])
    // chronologically: 5, 5, 20, 20 -> second half clearly higher -> Improving
    expect(result.trend).toBe('Improving')
  })

  test('boundary: a gap of exactly 2 points does NOT count as Improving (threshold is > 2, not >=)', () => {
    const result = generateInsights([
      session('Backend', 10, '2026-01-01'),
      session('Backend', 12, '2026-01-02'),
    ])
    expect(result.trend).toBe('Stable')
  })

  test('boundary: a gap of just over 2 points (2.01+) does count as Improving', () => {
    const result = generateInsights([
      session('Backend', 10, '2026-01-01'),
      session('Backend', 12.1, '2026-01-02'),
    ])
    expect(result.trend).toBe('Improving')
  })
})

// ─── FEATURE 3: career readiness score ────────────────────────────────────────

describe('generateInsights: readinessScore', () => {
  test('a single low-scoring session produces a low readinessScore', () => {
    const result = generateInsights([session('Backend', 5, '2026-01-01')])
    // avgScoreNormalized = (5/50)*100=10, *0.5=5; consistencyFactor=1*5=5; bonus=1*2=2; total=12
    expect(result.readinessScore).toBe(12)
  })

  test('readinessScore is clamped at 100 even though the raw formula can exceed it', () => {
    // 10 sessions all scoring the max (50): avgScoreNormalized=100*0.5=50, consistencyFactor=10*5=50,
    // bonus=5*2=10 -> raw total=110, must clamp to 100.
    const result = generateInsights(
      Array.from({ length: 10 }, (_, i) => session('Backend', 50, `2026-01-${String(i + 1).padStart(2, '0')}`))
    )
    expect(result.readinessScore).toBe(100)
  })

  test('readinessScore never goes negative even with a 0-scoring session', () => {
    const result = generateInsights([session('Backend', 0, '2026-01-01')])
    expect(result.readinessScore).toBeGreaterThanOrEqual(0)
  })

  test('more sessions increase the consistency component, up to the 10-session cap', () => {
    const fiveSessions = generateInsights(
      Array.from({ length: 5 }, (_, i) => session('Backend', 25, `2026-01-0${i + 1}`))
    )
    const tenSessions = generateInsights(
      Array.from({ length: 10 }, (_, i) => session('Backend', 25, `2026-01-${String(i + 1).padStart(2, '0')}`))
    )
    expect(tenSessions.readinessScore).toBeGreaterThan(fiveSessions.readinessScore)
  })

  test('the consistency bonus does not keep increasing past 10 sessions (capped)', () => {
    const tenSessions = generateInsights(
      Array.from({ length: 10 }, (_, i) => session('Backend', 25, `2026-01-${String(i + 1).padStart(2, '0')}`))
    )
    const twentySessions = generateInsights(
      Array.from({ length: 20 }, (_, i) => session('Backend', 25, `2026-${String(Math.floor(i / 28) + 1).padStart(2, '0')}-${String((i % 28) + 1).padStart(2, '0')}`))
    )
    expect(twentySessions.readinessScore).toBe(tenSessions.readinessScore)
  })
})

// ─── FEATURE 4: AI insight summary ────────────────────────────────────────────

describe('generateInsights: aiSummary', () => {
  test('fewer than 3 sessions -> "keep practicing" message, regardless of scores', () => {
    const result = generateInsights([session('Backend', 50, '2026-01-01'), session('Backend', 50, '2026-01-02')])
    expect(result.aiSummary).toContain('Keep practicing')
  })

  test('2+ weak categories AND Declining trend -> declining-with-weak-areas message naming the first weak category', () => {
    const result = generateInsights([
      session('Backend', 30, '2026-01-01'),
      session('Frontend', 5, '2026-01-02'),
      session('Backend', 5, '2026-01-03'),
      session('Frontend', 2, '2026-01-04'),
    ])
    expect(result.trend).toBe('Declining')
    expect(result.aiSummary).toContain('declining results')
  })

  test('2+ weak categories without Declining trend -> lists the weak categories by name', () => {
    const result = generateInsights([
      session('Backend', 5, '2026-01-01'),
      session('Backend', 5, '2026-01-02'),
      session('Frontend', 5, '2026-01-03'),
      session('Frontend', 5, '2026-01-04'),
    ])
    expect(result.aiSummary).toContain('areas to strengthen')
    expect(result.aiSummary).toContain('Backend')
    expect(result.aiSummary).toContain('Frontend')
  })

  test('Improving trend with 2+ strong categories -> "strong growth" message', () => {
    const result = generateInsights([
      session('Backend', 35, '2026-01-01'),
      session('Frontend', 35, '2026-01-02'),
      session('Backend', 45, '2026-01-03'),
      session('Frontend', 45, '2026-01-04'),
    ])
    expect(result.weaknessMap.every(w => w.level === 'Strong')).toBe(true)
    expect(result.trend).toBe('Improving')
    expect(result.aiSummary).toContain('Strong growth detected')
  })

  test('Improving trend without 2+ strong categories -> generic improving message', () => {
    const result = generateInsights([
      session('Backend', 15, '2026-01-01'),
      session('Backend', 16, '2026-01-02'),
      session('Backend', 22, '2026-01-03'),
    ])
    expect(result.trend).toBe('Improving')
    expect(result.aiSummary).toContain('improving steadily')
  })

  test('Declining trend with fewer than 2 weak categories -> generic declining message', () => {
    const result = generateInsights([
      session('Backend', 25, '2026-01-01'),
      session('Backend', 24, '2026-01-02'),
      session('Backend', 10, '2026-01-03'),
    ])
    expect(result.trend).toBe('Declining')
    expect(result.aiSummary).toContain('slight decline')
  })

  test('Stable trend with fewer than 5 total sessions -> "foundation is developing" message', () => {
    const result = generateInsights([
      session('Backend', 20, '2026-01-01'),
      session('Backend', 20, '2026-01-02'),
      session('Backend', 20, '2026-01-03'),
    ])
    expect(result.trend).toBe('Stable')
    expect(result.aiSummary).toContain('foundation is developing')
  })

  test('Stable trend with 5+ total sessions -> generic "stable, focus on consistency" message', () => {
    const result = generateInsights(
      Array.from({ length: 5 }, (_, i) => session('Backend', 20, `2026-01-0${i + 1}`))
    )
    expect(result.trend).toBe('Stable')
    expect(result.aiSummary).toContain('performance is stable')
  })
})

// ─── documented findings: dead code / formula notes (informational, not bugs) ─

describe('generateInsights: documented findings (not bugs, pinned for visibility)', () => {
  test('DOCUMENTED: the readinessScore formula can only ever reach exactly 100 at its true maximum, never overshoot in the returned value (clamp confirmed correct at the boundary)', () => {
    const maxResult = generateInsights(
      Array.from({ length: 10 }, (_, i) => session('Backend', 50, `2026-01-${String(i + 1).padStart(2, '0')}`))
    )
    expect(maxResult.readinessScore).toBeLessThanOrEqual(100)
    expect(maxResult.readinessScore).toBe(100)
  })

  test('DOCUMENTED: the small-sample fallback trend branch (safe.length >= 4 with an empty half) is unreachable in practice; midpoint splitting always produces two non-empty halves once length >= 2', () => {
    // Demonstrates that even with exactly 4 sessions (the threshold named in
    // the dead branch's condition), the main branch's firstHalf/secondHalf
    // split already produces two non-empty halves, so the dead branch's
    // own condition for being entered is never satisfied.
    const result = generateInsights([
      session('Backend', 10, '2026-01-01'),
      session('Backend', 10, '2026-01-02'),
      session('Backend', 10, '2026-01-03'),
      session('Backend', 10, '2026-01-04'),
    ])
    expect(result.trend).toBe('Stable') // computed via the main branch, not the dead one
  })
})