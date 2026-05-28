/**
 * Analysis API Client - Phase 3 (DIP Fix)
 * All fetch calls for the analysis feature live here.
 * page.tsx and useAnalysis never call fetch directly.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface AnalysisJobResponse {
  job_id: string
  status: string
  message: string
}

export interface JobStatusResponse {
  id: string
  status: 'pending' | 'completed' | 'failed'
}

export interface AnalysisRecord {
  analysis: Record<string, any>
  career_paths: any[]
  skill_gaps: any[]
  roadmap: Record<string, any>
  path_details: Record<string, any>
  resume_score?: any
  salary_insights?: any
  top_companies?: any[]
  certifications?: any[]
  experience_level?: string
}

export const analysisClient = {
  async checkExisting(token: string): Promise<{ exists: boolean; analysis?: AnalysisRecord }> {
    const res = await fetch(`${API_URL}/api/v1/analysis/`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    })
    const data = await res.json()
    return {
      exists: data?.data?.exists ?? false,
      analysis: data?.data?.analysis,
    }
  },

  async startAnalysis(token: string, userId: string): Promise<AnalysisJobResponse> {
    const res = await fetch(`${API_URL}/api/v1/analysis/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ user_id: userId }),
    })
    if (!res.ok) throw new Error('Analysis failed to start')
    const data = await res.json()
    if (!data?.data?.job_id) throw new Error('No job ID returned from analysis start')
    return data.data
  },

  async getJobStatus(token: string, jobId: string): Promise<JobStatusResponse> {
    const res = await fetch(`${API_URL}/api/v1/analysis/job/${jobId}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    })
    if (!res.ok) throw new Error('Failed to get job status')
    const data = await res.json()
    return data.data
  },

  async getFinalAnalysis(token: string): Promise<AnalysisRecord | null> {
    const res = await fetch(`${API_URL}/api/v1/analysis/`, {
      headers: { 'Authorization': `Bearer ${token}` },
    })
    if (!res.ok) return null
    const data = await res.json()
    return data?.data?.analysis ?? null
  },

  async getRoadmapProgress(token: string, careerPath: string): Promise<Record<number, string>> {
    const res = await fetch(`${API_URL}/api/v1/roadmap/progress/${careerPath}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    })
    if (!res.ok) return {}
    const data = await res.json()
    return data.progress_map || {}
  },

  async updateMilestone(token: string, careerPath: string, week: number, status: string): Promise<any> {
    const res = await fetch(`${API_URL}/api/v1/roadmap/milestone`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ career_path: careerPath, milestone_week: week, status }),
    })
    const data = await res.json()
    return { status: res.status, data }
  },
}