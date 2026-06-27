import { parseAnalysisRecord } from './parseAnalysisRecord';

describe('parseAnalysisRecord', () => {
  it('correctly parses a well-formed record', () => {
    const baseRecord = {
      analysis: {
        strengths: ['Leadership', 'Problem Solving'],
        experience_level: 'Mid-level',
      },
      career_paths: [{ name: 'Software Engineer' }],
      resume_score: { overall: 85 },
      salary_insights: { entry_level: 75000 },
    };

    const result = parseAnalysisRecord(baseRecord);

    expect(result.analysis.experience_level).toBe('Mid-level');
    expect(result.analysis.strengths).toEqual(['Leadership', 'Problem Solving']);
    expect(result.analysis.career_paths).toEqual([{ name: 'Software Engineer' }]);
    expect(result.firstPathName).toBe('Software Engineer');
    expect(result.analysis.resume_score).toEqual({ overall: 85 });
  });

  it('handles null/undefined input gracefully', () => {
    const result = parseAnalysisRecord(null);
    expect(result.analysis.strengths).toEqual([]);
    expect(result.analysis.career_paths).toEqual([]);
    expect(result.firstPathName).toBe('');
  });

  it('prioritizes nested analysis fields correctly', () => {
    const messyRecord = {
      analysis: {
        analysis: { strengths: ['Communication'] },
        strengths: ['Old Strength'],
      },
    };

    const result = parseAnalysisRecord(messyRecord);
    expect(result.analysis.strengths).toEqual(['Communication']);
  });

  it('filters error messages from strengths', () => {
    const recordWithError = {
      analysis: { strengths: ['Leadership', 'Error in processing', 'Teamwork'] },
    };

    const result = parseAnalysisRecord(recordWithError);
    expect(result.analysis.strengths).toEqual(['Leadership', 'Teamwork']);
  });

  it('handles missing fields with sensible defaults', () => {
    const result = parseAnalysisRecord({});

    expect(result.analysis.experience_level).toBe('Beginner');
    expect(result.analysis.roadmap.duration_months).toBe(6);
    expect(result.firstPathName).toBe('');
  });
});