/**
 * API Client
 * Centralized API helper for communicating with the FastAPI backend.
 */
import { createBrowserClient } from '@supabase/ssr'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Types
export interface ProfileData {
  user_type?: string
  college_name?: string
  degree?: string
  branch?: string
  current_year?: string
  graduation_year?: number
  cgpa?: number
  current_job_title?: string
  current_company?: string
  years_of_experience?: number
  current_tech_stack?: string[]
  extra_skills?: string[]
  certificates?: string[]
  target_companies?: string[]
  preferred_location?: string
  career_goal?: string
  open_to?: string
  github_username?: string
  leetcode_username?: string
  linkedin_url?: string
  resume_url?: string
}

export interface EnrichedProfile {
  exists: boolean
  user_id: string
  completeness: number
  skills: any[]
  data: ProfileData
  documents_count: number
}

export interface UserProgress {
  total: number
  steps: any[]
  status: string
}

export interface AnalysisResult {
  id: string
  user_id: string
  strengths: string[]
  weaknesses: string[]
  experience_level: string
  career_paths: any[]
  skill_gap: any[]
  created_at: string
}

export interface Job {
  id: string
  title: string
  company: string
  location: string
  type: string
  url: string
  match_score: number
  matched_skills: string[]
  missing_skills: string[]
}

export interface Document {
  id: number
  document_name: string
  document_type: string
  extracted_data: Record<string, unknown>
  storage_url?: string
  created_at: string
}

export interface MatchFit {
  score: number
  label: string
  role: string
  reason: string
}

// API Client Class
class ApiClient {
  private supabase = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
  
  private async getAuthHeaders(): Promise<Record<string, string>> {
    const { data: { session } } = await this.supabase.auth.getSession()
    return session?.access_token 
      ? { Authorization: `Bearer ${session.access_token}` }
      : {}
  }
  
  private async request(endpoint: string, options: RequestInit = {}): Promise<any> {
    const headers = await this.getAuthHeaders()
    
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...headers,
        ...options.headers,
      },
    })
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || `API Error: ${response.statusText}`)
    }
    
    return response.json()
  }
  
  private async requestWithRetry(
    endpoint: string, 
    options: RequestInit = {}, 
    retries = 3,
    backoffMs = 1000
  ): Promise<any> {
    let lastError: Error | null = null
    
    for (let i = 0; i < retries; i++) {
      try {
        return await this.request(endpoint, options)
      } catch (error) {
        lastError = error as Error
        
        // Don't retry on client errors (4xx)
        if (error instanceof Error && error.message.includes('400')) {
          throw error
        }
        if (error instanceof Error && error.message.includes('401')) {
          throw error
        }
        if (error instanceof Error && error.message.includes('403')) {
          throw error
        }
        if (error instanceof Error && error.message.includes('404')) {
          throw error
        }
        
        // Exponential backoff
        if (i < retries - 1) {
          const delay = backoffMs * Math.pow(2, i)
          console.log(`Retry ${i + 1}/${retries} for ${endpoint} after ${delay}ms`)
          await new Promise(resolve => setTimeout(resolve, delay))
        }
      }
    }
    
    throw lastError || new Error('Max retries reached')
  }

  // Profile API
  async getProfile(): Promise<EnrichedProfile> {
    const res = await this.requestWithRetry('/api/profile/me')
    return res.profile
  }
  
  async saveProfile(data: ProfileData): Promise<any> {
    return this.request('/api/profile/save', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }
  
  async getProgress(): Promise<UserProgress> {
    const res = await this.requestWithRetry('/api/profile/progress')
    return res.progress
  }
  
  async getMatchFit(): Promise<MatchFit> {
    const res = await this.request('/api/profile/match-fit')
    return {
      score: res.score,
      label: res.label,
      role: res.role,
      reason: res.reason
    }
  }

  // Analysis API (async)
  async getAnalysis(): Promise<AnalysisResult | null> {
    const res = await this.request('/api/analysis/')
    return res.analysis
  }
  
  async runAnalysis(): Promise<any> {
    return this.request('/api/analysis/run', { method: 'POST' })
  }
  
  async getJobStatus(jobId: string): Promise<any> {
    return this.request(`/api/analysis/job/${jobId}`)
  }
  
  async getAnalysisJobs(): Promise<any[]> {
    const res = await this.request('/api/analysis/jobs')
    return res.jobs || []
  }
  
  // Helper to poll for job completion
  async pollJobUntilComplete(
    jobId: string,
    onProgress?: (status: string) => void,
    maxAttempts = 60,
    intervalMs = 2000
  ): Promise<any> {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const job = await this.getJobStatus(jobId)
      
      if (job.data?.status === 'completed') {
        return job.data.result
      }
      
      if (job.data?.status === 'failed') {
        throw new Error(job.data.error_message || 'Analysis failed')
      }
      
      if (onProgress) {
        onProgress(job.data?.status || 'processing')
      }
      
      await new Promise(resolve => setTimeout(resolve, intervalMs))
    }
    
    throw new Error('Analysis timed out')
  }
  
  async getCareerPaths(): Promise<any[]> {
    const res = await this.request('/api/analysis/career-paths')
    return res.career_paths
  }
  
  async getSkillGaps(): Promise<any[]> {
    const res = await this.request('/api/analysis/skill-gap')
    return res.skill_gaps
  }

  // Jobs API
  async getJobRecommendations(params?: {
    query?: string
    location?: string
    job_type?: string
    page?: number
    limit?: number
  }): Promise<any> {
    const searchParams = new URLSearchParams()
    if (params?.query) searchParams.set('query', params.query)
    if (params?.location) searchParams.set('location', params.location)
    if (params?.job_type) searchParams.set('job_type', params.job_type)
    if (params?.page) searchParams.set('page', String(params.page))
    if (params?.limit) searchParams.set('limit', String(params.limit))
    
    const query = searchParams.toString()
    return this.requestWithRetry(`/api/jobs/recommendations${query ? '?' + query : ''}`)
  }

  // Documents API
  async uploadDocument(data: {
    document_name: string
    document_type: string
    storage_url?: string
    content?: string
  }): Promise<any> {
    return this.request('/api/documents/upload', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }
  
  async getDocuments(documentType?: string): Promise<Document[]> {
    const query = documentType ? '?document_type=' + documentType : ''
    const res = await this.request('/api/documents/list' + query)
    return res.documents
  }
  
  async deleteDocument(documentId: number): Promise<any> {
    return this.request('/api/documents/' + documentId, { method: 'DELETE' })
  }
}

// Export singleton instance
export const api = new ApiClient()
