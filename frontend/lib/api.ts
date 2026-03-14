const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Types for API responses
export interface ProfileData {
  github_url?: string
  leetcode_username?: string
  linkedin_url?: string
}

export interface AnalysisResult {
  id: string
  user_id: string
  strengths: string[]
  weaknesses: string[]
  experience_level: 'Beginner' | 'Intermediate' | 'Advanced'
  career_paths: CareerPath[]
  skill_gap: SkillGap[]
  created_at: string
}

export interface CareerPath {
  name: string
  match_percentage: number
  reason: string
}

export interface SkillGap {
  skill: string
  have: boolean
  priority: number
  resources: string[]
}

export interface Roadmap {
  id: string
  target_career: string
  duration_months: number
  milestones: Milestone[]
}

export interface Milestone {
  week: number
  title: string
  description: string
  skills: string[]
  completed: boolean
}

export interface Job {
  id: string
  title: string
  company: string
  location: string
  type: string
  url: string
  match_score: number
}

// API functions
async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`)
  }
  
  return response.json()
}

export const api = {
  // Profile endpoints
  async submitProfile(data: ProfileData) {
    return fetchWithAuth('/api/profile', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
  
  async getProfile() {
    return fetchWithAuth('/api/profile')
  },
  
  // Analysis endpoints
  async startAnalysis() {
    return fetchWithAuth('/api/analysis/start', {
      method: 'POST',
    })
  },
  
  async getAnalysis(analysisId: string) {
    return fetchWithAuth(`/api/analysis/${analysisId}`)
  },
  
  // Career paths
  async getCareerPaths() {
    return fetchWithAuth('/api/career-paths')
  },
  
  // Skill gap
  async getSkillGap() {
    return fetchWithAuth('/api/skill-gap')
  },
  
  // Roadmap
  async getRoadmap(careerPath: string) {
    return fetchWithAuth(`/api/roadmap?career=${encodeURIComponent(careerPath)}`)
  },
  
  // Jobs
  async getJobs(filters?: { location?: string; type?: string }) {
    const params = new URLSearchParams()
    if (filters?.location) params.set('location', filters.location)
    if (filters?.type) params.set('type', filters.type)
    
    return fetchWithAuth(`/api/jobs?${params.toString()}`)
  },
}
