/**
 * parseAnalysisRecord — Pure Data Transformer
 * SRP: only responsibility is normalising raw API records into AnalysisData.
 * Extracted from useAnalysis so it can be unit-tested without mocks or timers.
 */
export function parseAnalysisRecord(record: any) {
  if (record == null) return parseAnalysisRecord({})
  const analysisObj       = record?.analysis || {}
  const strengths         = analysisObj.analysis?.strengths   || analysisObj.strengths   || record.strengths   || []
  const careerPaths       = record.career_paths               || analysisObj.career_paths || []
  const skillGaps         = analysisObj.skill_gaps            || analysisObj.skill_gap   || record.skill_gaps   || []
  const roadmap           = analysisObj.roadmap               || record.roadmap           || { target_career: '', duration_months: 6, milestones: [] }
  const experienceLevel   = analysisObj.analysis?.experience_level || analysisObj.experience_level || record.experience_level || 'Beginner'
  const pathDetails       = record?.path_details || {}
  const firstPathName     = Array.isArray(careerPaths) && careerPaths.length > 0
    ? (careerPaths[0]?.name || careerPaths[0]?.career_name || careerPaths[0]?.title || '')
    : ''

  return {
    analysis: {
      experience_level: experienceLevel,
      strengths:        Array.isArray(strengths)   ? strengths.filter((s: string) => !String(s).toLowerCase().includes('error')) : [],
      career_paths:     Array.isArray(careerPaths) ? careerPaths : [],
      skill_gaps:       Array.isArray(skillGaps)   ? skillGaps   : [],
      roadmap,
      resume_score:     (record.resume_score?.overall != null ? record.resume_score : null) || analysisObj.resume_score     || null,
      salary_insights:  (record.salary_insights?.entry_level   ? record.salary_insights  : null) || analysisObj.salary_insights || null,
      top_companies:    (Array.isArray(record.top_companies)    && record.top_companies.length > 0    ? record.top_companies    : null) || analysisObj.top_companies    || [],
      certifications:   (Array.isArray(record.certifications)   && record.certifications.length > 0   ? record.certifications   : null) || analysisObj.certifications   || [],
    },
    pathDetails,
    firstPathName,
  }
}

