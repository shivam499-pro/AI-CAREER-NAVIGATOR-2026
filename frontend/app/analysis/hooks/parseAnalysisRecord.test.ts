/**
 * parseAnalysisRecord Tests
 * Pure function — zero mocks, zero timers, zero async.
 * Closes Phase 0 frontend testing gap.
 */
import { parseAnalysisRecord } from './parseAnalysisRecord'

const FULL_RECORD = {
  analysis: {
    analysis: { strengths: ['Python', 'React'], experience_level: 'Intermediate' },
    career_paths:    [{ name: 'Full Stack Developer' }],
    skill_gaps:      ['TypeScript', 'AWS'],
    roadmap:         { target_career: 'Full Stack', duration_months: 6, milestones: [] },
    resume_score:    { overall: 85 },
    salary_insights: { entry_level: 60000 },
    top_companies:   [{ name: 'Google' }],
    certifications:  [{ name: 'AWS Certified' }],
  },
  career_paths:    [{ name: 'Full Stack Developer' }],
  skill_gaps:      ['TypeScript'],
  roadmap:         { target_career: 'Full Stack', duration_months: 6, milestones: [] },
  path_details:    { 'Full Stack Developer': { description: 'Build web apps' } },
  resume_score:    { overall: 85 },
  salary_insights: { entry_level: 60000 },
  top_companies:   [{ name: 'Google' }],
  certifications:  [{ name: 'AWS Certified' }],
}

describe('parseAnalysisRecord', () => {

  describe('happy path', () => {
    it('returns correct experience_level', () => {
      expect(parseAnalysisRecord(FULL_RECORD).analysis.experience_level).toBe('Intermediate')
    })
    it('returns correct strengths', () => {
      expect(parseAnalysisRecord(FULL_RECORD).analysis.strengths).toEqual(['Python', 'React'])
    })
    it('returns correct career_paths', () => {
      expect(parseAnalysisRecord(FULL_RECORD).analysis.career_paths).toEqual([{ name: 'Full Stack Developer' }])
    })
    it('returns correct skill_gaps', () => {
      expect(parseAnalysisRecord(FULL_RECORD).analysis.skill_gaps).toEqual(['TypeScript', 'AWS'])
    })
    it('returns correct roadmap', () => {
      const r = parseAnalysisRecord(FULL_RECORD).analysis.roadmap
      expect(r.target_career).toBe('Full Stack')
      expect(r.duration_months).toBe(6)
    })
    it('returns firstPathName from career_paths[0].name', () => {
      expect(parseAnalysisRecord(FULL_RECORD).firstPathName).toBe('Full Stack Developer')
    })
    it('returns pathDetails', () => {
      expect(parseAnalysisRecord(FULL_RECORD).pathDetails).toEqual({ 'Full Stack Developer': { description: 'Build web apps' } })
    })
    it('returns resume_score when overall present', () => {
      expect(parseAnalysisRecord(FULL_RECORD).analysis.resume_score).toEqual({ overall: 85 })
    })
    it('returns salary_insights when entry_level present', () => {
      expect(parseAnalysisRecord(FULL_RECORD).analysis.salary_insights).toEqual({ entry_level: 60000 })
    })
    it('returns top_companies array', () => {
      expect(parseAnalysisRecord(FULL_RECORD).analysis.top_companies).toEqual([{ name: 'Google' }])
    })
    it('returns certifications array', () => {
      expect(parseAnalysisRecord(FULL_RECORD).analysis.certifications).toEqual([{ name: 'AWS Certified' }])
    })
  })

  describe('error string filtering', () => {
    it('filters strengths containing the word error', () => {
      const record = { analysis: { analysis: { strengths: ['Python', 'error: AI failed', 'React', 'ERROR: timeout'], experience_level: 'Senior' } } }
      expect(parseAnalysisRecord(record).analysis.strengths).toEqual(['Python', 'React'])
    })
    it('keeps strengths without the word error', () => {
      const record = { analysis: { analysis: { strengths: ['Go', 'Rust', 'TypeScript'], experience_level: 'Senior' } } }
      expect(parseAnalysisRecord(record).analysis.strengths).toHaveLength(3)
    })
  })

  describe('missing fields', () => {
    it('defaults experience_level to Beginner', () => {
      expect(parseAnalysisRecord({}).analysis.experience_level).toBe('Beginner')
    })
    it('defaults strengths to empty array', () => {
      expect(parseAnalysisRecord({}).analysis.strengths).toEqual([])
    })
    it('defaults career_paths to empty array', () => {
      expect(parseAnalysisRecord({}).analysis.career_paths).toEqual([])
    })
    it('defaults skill_gaps to empty array', () => {
      expect(parseAnalysisRecord({}).analysis.skill_gaps).toEqual([])
    })
    it('defaults roadmap with empty target_career', () => {
      const r = parseAnalysisRecord({}).analysis.roadmap
      expect(r.target_career).toBe('')
      expect(r.duration_months).toBe(6)
    })
    it('defaults firstPathName to empty string', () => {
      expect(parseAnalysisRecord({ career_paths: [] }).firstPathName).toBe('')
    })
    it('defaults pathDetails to empty object', () => {
      expect(parseAnalysisRecord({}).pathDetails).toEqual({})
    })
    it('returns null for resume_score when overall missing', () => {
      expect(parseAnalysisRecord({ resume_score: { score: 80 } }).analysis.resume_score).toBeNull()
    })
    it('returns null for salary_insights when entry_level missing', () => {
      expect(parseAnalysisRecord({ salary_insights: { mid_level: 90000 } }).analysis.salary_insights).toBeNull()
    })
    it('returns empty array for top_companies when missing', () => {
      expect(parseAnalysisRecord({}).analysis.top_companies).toEqual([])
    })
    it('returns empty array for certifications when missing', () => {
      expect(parseAnalysisRecord({}).analysis.certifications).toEqual([])
    })
  })

  describe('firstPathName fallbacks', () => {
    it('uses career_name when name missing', () => {
      expect(parseAnalysisRecord({ career_paths: [{ career_name: 'Backend Engineer' }] }).firstPathName).toBe('Backend Engineer')
    })
    it('uses title when name and career_name missing', () => {
      expect(parseAnalysisRecord({ career_paths: [{ title: 'DevOps Engineer' }] }).firstPathName).toBe('DevOps Engineer')
    })
    it('returns empty string when all name fields missing', () => {
      expect(parseAnalysisRecord({ career_paths: [{ id: 1 }] }).firstPathName).toBe('')
    })
  })

  describe('null and undefined safety', () => {
    it('handles null input without throwing', () => {
      expect(() => parseAnalysisRecord(null)).not.toThrow()
    })
    it('handles undefined input without throwing', () => {
      expect(() => parseAnalysisRecord(undefined)).not.toThrow()
    })
    it('handles non-array strengths gracefully', () => {
      const record = { analysis: { analysis: { strengths: 'Python', experience_level: 'Junior' } } }
      expect(parseAnalysisRecord(record).analysis.strengths).toEqual([])
    })
    it('handles non-array career_paths gracefully', () => {
      expect(parseAnalysisRecord({ career_paths: 'Full Stack' }).analysis.career_paths).toEqual([])
    })
  })
})
