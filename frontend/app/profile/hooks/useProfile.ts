'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'

// ── Types ──────────────────────────────────────────────────────────────────────

export interface ProfileFormData {
  user_type: string
  // Academic
  college_name: string
  degree: string
  branch: string
  year_of_study: string
  graduation_year: number
  cgpa: string
  // Professional
  current_job_title: string
  current_company: string
  years_of_experience: number
  current_tech_stack: string[]
  reason_for_switching: string
  // Career
  career_goal: string
  target_companies: string[]
  preferred_work_type: string
  job_search_timeline: string
  preferred_location: string
  // Skills
  extra_skills: string[]
  // External
  github_username: string
  leetcode_username: string
  linkedin_url: string
}

const INITIAL_PROFILE: ProfileFormData = {
  user_type: '',
  college_name: '',
  degree: '',
  branch: '',
  year_of_study: '',
  graduation_year: 0,
  cgpa: '',
  current_job_title: '',
  current_company: '',
  years_of_experience: 0,
  current_tech_stack: [],
  reason_for_switching: '',
  career_goal: '',
  target_companies: [],
  preferred_work_type: '',
  job_search_timeline: '',
  preferred_location: '',
  extra_skills: [],
  github_username: '',
  leetcode_username: '',
  linkedin_url: '',
}

// ── Hook ───────────────────────────────────────────────────────────────────────

export function useProfile() {
  const router = useRouter()
  const isMountedRef = useRef(true)
  useEffect(() => { return () => { isMountedRef.current = false } }, [])

  const [user, setUser] = useState<any>(null)
  const [profile, setProfile] = useState<ProfileFormData>(INITIAL_PROFILE)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [resumeUploaded, setResumeUploaded] = useState(false)

  // ── Auth headers ─────────────────────────────────────────────────────────────

  const getHeaders = useCallback(async (): Promise<Record<string, string>> => {
    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token
      ? {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        }
      : { 'Content-Type': 'application/json' }
  }, [])

  // ── Load ──────────────────────────────────────────────────────────────────────

  const loadProfile = useCallback(async () => {
    try {
      const headers = await getHeaders()
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${apiUrl}/api/v1/profile/me`, { headers })

      if (!res.ok) { setError('Failed to load profile'); return }

      const json = await res.json()
      // Response is nested: json.data.profile.data
      const data = json?.data?.profile?.data || {}

      setResumeUploaded(!!data.resume_text)

      setProfile({
        user_type:            data.user_type            || '',
        college_name:         data.college_name         || '',
        degree:               data.degree               || '',
        branch:               data.branch               || '',
        year_of_study:        data.year_of_study        || '',
        graduation_year:      data.graduation_year      || 0,
        cgpa:                 data.cgpa                 || '',
        current_job_title:    data.current_job_title    || '',
        current_company:      data.current_company      || '',
        years_of_experience:  data.years_of_experience  || 0,
        current_tech_stack:   data.current_tech_stack   || [],
        reason_for_switching: data.reason_for_switching || '',
        career_goal:          data.career_goal          || '',
        target_companies:     data.target_companies     || [],
        preferred_work_type:  data.preferred_work_type  || '',
        job_search_timeline:  data.job_search_timeline  || '',
        preferred_location:   data.preferred_location   || '',
        extra_skills:         data.extra_skills         || [],
        github_username:      data.github_username      || '',
        leetcode_username:    data.leetcode_username    || '',
        linkedin_url:         data.linkedin_url         || '',
      })
    } catch {
      setError('Failed to load profile')
    } finally {
      if (isMountedRef.current) setLoading(false)
    }
  }, [getHeaders])

  // ── Init ──────────────────────────────────────────────────────────────────────

  useEffect(() => {
    const init = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) { router.push('/auth/login'); return }
      setUser(user)
      await loadProfile()
    }
    init()
  }, [router, loadProfile])

  
  // ── Save ──────────────────────────────────────────────────────────────────────

  const saveProfile = useCallback(async () => {
    if (!user) return
    setSaving(true)
    setError(null)
    try {
      const headers = await getHeaders()
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${apiUrl}/api/v1/profile/save`, {
        method: 'POST',
        headers,
        body: JSON.stringify(profile),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err?.error || 'Failed to save profile')
      }
      if (isMountedRef.current) {
        setSaved(true)
        setTimeout(() => setSaved(false), 3000)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to save profile')
    } finally {
      if (isMountedRef.current) setSaving(false)
    }
  }, [user, profile, getHeaders])

  // ── Field update ──────────────────────────────────────────────────────────────

  const updateField = useCallback(<K extends keyof ProfileFormData>(
    field: K,
    value: ProfileFormData[K]
  ) => {
    setProfile(prev => ({ ...prev, [field]: value }))
  }, [])

  // ── Tag management ────────────────────────────────────────────────────────────

  const addTag = useCallback((
    field: 'extra_skills' | 'target_companies' | 'current_tech_stack',
    value: string
  ) => {
    const trimmed = value.trim()
    if (!trimmed) return
    setProfile(prev => {
      if (prev[field].includes(trimmed)) return prev
      return { ...prev, [field]: [...prev[field], trimmed] }
    })
  }, [])

  const removeTag = useCallback((
    field: 'extra_skills' | 'target_companies' | 'current_tech_stack',
    index: number
  ) => {
    setProfile(prev => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== index)
    }))
  }, [])

  // ── Completeness ──────────────────────────────────────────────────────────────

  const completeness = (() => {
    let score = 0
    if (profile.github_username)              score += 15
    if (profile.leetcode_username)            score += 15
    if (resumeUploaded)                       score += 20
    if (profile.college_name && profile.degree) score += 10
    if (profile.extra_skills.length >= 3)    score += 10
    if (profile.career_goal)                 score += 15
    if (profile.linkedin_url)                score += 5
    if (profile.year_of_study || profile.current_job_title) score += 5
    if (profile.target_companies.length > 0) score += 5
    return Math.min(score, 100)
  })()

  // ── Derived flags ─────────────────────────────────────────────────────────────

  const isStudent     = ['student', 'fresher', ''].includes(profile.user_type)
  const isProfessional = ['professional', 'career_switch'].includes(profile.user_type)

  return {
    user,
    profile,
    loading,
    saving,
    saved,
    error,
    completeness,
    resumeUploaded,
    isStudent,
    isProfessional,
    updateField,
    addTag,
    removeTag,
    saveProfile,
  }
}
