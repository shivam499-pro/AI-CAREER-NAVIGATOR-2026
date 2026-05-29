/**
 * Resume API Client (DIP Fix)
 * All fetch calls for resume and certificate features live here.
 * useResume never calls fetch directly.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface ResumeStatus {
  has_resume: boolean
  filename?: string
  resume_url?: string
}

export interface UploadedDoc {
  id: string
  document_name: string
  document_type: string
  extracted_data: any
  created_at: string
}

export interface Certificate {
  name: string
  issuer: string
  date: string
  score?: string
  skills: string[]
  weight: number
  credibility: 'high' | 'medium' | 'low'
  type: 'cloud' | 'academic' | 'hackathon' | 'course' | 'competition' | 'other'
}

export interface DocumentResult {
  certificates: Certificate[]
  skills_extracted: string[]
  achievements: string[]
  summary: string
  impact_score: number
}

const authHeader = (token: string) => ({ Authorization: `Bearer ${token}` })

export const resumeClient = {
  async getStatus(token: string): Promise<ResumeStatus | null> {
    try {
      const res = await fetch(`${API_URL}/api/v1/resume/status/`, { headers: authHeader(token) })
      if (!res.ok) return null
      return res.json()
    } catch { return null }
  },

  // No token — backend authenticates via form data for file uploads
  async uploadResume(file: File): Promise<{ success: boolean }> {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${API_URL}/api/v1/resume/upload`, {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Upload failed.')
    }
    return res.json()
  },

  async getDocuments(token: string): Promise<UploadedDoc[]> {
    try {
      const res = await fetch(`${API_URL}/api/v1/documents/list`, { headers: authHeader(token) })
      if (!res.ok) return []
      const data = await res.json()
      return (data.documents || []).filter((d: UploadedDoc) => d.document_type !== 'resume')
    } catch { return [] }
  },

  async uploadCertificates(token: string, userId: string, files: File[]): Promise<DocumentResult> {
    const formData = new FormData()
    formData.append('user_id', userId)
    files.forEach(f => formData.append('files', f))
    const res = await fetch(`${API_URL}/api/v1/documents/upload-files`, {
      method: 'POST',
      headers: authHeader(token),
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Analysis failed.')
    }
    const data = await res.json()
    if (!data.success) throw new Error('Upload was not successful')
    return data.extracted
  },

  async deleteDocument(token: string, docId: string): Promise<void> {
    await fetch(`${API_URL}/api/v1/documents/${docId}`, {
      method: 'DELETE',
      headers: authHeader(token),
    })
  },
}