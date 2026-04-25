'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import { Brain, Github, Code, Linkedin, FileText, ChevronRight, ChevronLeft, Loader2, Upload, X, GraduationCap, Briefcase, Sprout, ArrowRightLeft } from 'lucide-react'

type UserType = 'student' | 'professional' | 'fresher' | 'career_switch'

interface ProfileData {
  user_id: string
  user_type: UserType
  // Student fields
  college_name: string
  degree: string
  branch: string
  year_of_study: string
  graduation_year: string
  cgpa: string
  // Professional fields
  current_job_title: string
  current_company: string
  years_of_experience: string
  current_tech_stack: string[]
  reason_for_switching: string
  // Fresher fields
  // (uses college_name, degree, graduation_year, cgpa from student)
  // Career switch fields
  // (uses current_job_title, years_of_experience, reason_for_switching from professional)
  // Common fields
  career_goal: string
  target_companies: string[]
  preferred_work_type: string
  extra_skills: string[]
  certificates: string[]
  job_search_timeline: string
  // Existing fields
  github_username: string
  leetcode_username: string
  linkedin_url: string
  resume_url: string
  resume_file: File | null
}

const COMMON_SKILLS = [
  'Python', 'JavaScript', 'TypeScript', 'React', 'Node.js', 'FastAPI',
  'Django', 'Java', 'C++', 'SQL', 'MongoDB', 'Docker', 'AWS', 'Git',
  'Machine Learning', 'Data Analysis'
]

const DEGREE_OPTIONS = ['B.Tech', 'BCA', 'BCS', 'MCA', 'MBA', 'BSc', 'MSc', 'Other']
const YEAR_OF_STUDY_OPTIONS = ['1st Year', '2nd Year', '3rd Year', 'Final Year']
const EXPERIENCE_OPTIONS = ['1-2', '3-5', '5-10', '10+']
const CAREER_GOAL_OPTIONS = [
  'Full Stack Developer', 'Frontend Developer', 'Backend Developer',
  'AI/ML Engineer', 'Data Scientist', 'DevOps Engineer',
  'Mobile Developer', 'Cybersecurity', 'Cloud Architect', 'Other'
]
const TIMELINE_OPTIONS = ['Actively looking (ASAP)', '1-3 months', '3-6 months', 'Just exploring']

export default function OnboardingPage() {
  const [currentStep, setCurrentStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [user, setUser] = useState<{ id: string } | null>(null)
  const [profileData, setProfileData] = useState<ProfileData>({
    user_id: '',
    user_type: 'student',
    college_name: '',
    degree: '',
    branch: '',
    year_of_study: '',
    graduation_year: '',
    cgpa: '',
    current_job_title: '',
    current_company: '',
    years_of_experience: '',
    current_tech_stack: [],
    reason_for_switching: '',
    career_goal: '',
    target_companies: [],
    preferred_work_type: '',
    extra_skills: [],
    certificates: [],
    job_search_timeline: '',
    github_username: '',
    leetcode_username: '',
    linkedin_url: '',
    resume_url: '',
    resume_file: null,
  })
  const fileInputRef = useRef<HTMLInputElement>(null)
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // Tag input state
  const [techStackInput, setTechStackInput] = useState('')
  const [targetCompanyInput, setTargetCompanyInput] = useState('')
  const [skillInput, setSkillInput] = useState('')
  const [certificateInput, setCertificateInput] = useState('')

  // Check authentication on mount
  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        window.location.href = '/auth/login'
        return
      }
      setUser(user)
      setProfileData(prev => ({ ...prev, user_id: user.id }))
    }
    checkAuth()
  }, [])

  const handleNext = () => {
    if (currentStep < 7) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const addTag = (field: 'current_tech_stack' | 'target_companies' | 'extra_skills' | 'certificates', value: string, setInput: (v: string) => void) => {
    const trimmed = value.trim()
    if (!trimmed) return
    if (!profileData[field].includes(trimmed)) {
      setProfileData(prev => ({
        ...prev,
        [field]: [...prev[field], trimmed]
      }))
    }
    setInput('')
  }

  const removeTag = (field: 'current_tech_stack' | 'target_companies' | 'extra_skills' | 'certificates', index: number) => {
    setProfileData(prev => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== index)
    }))
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && file.type === 'application/pdf') {
      setProfileData({ ...profileData, resume_file: file })
    } else {
      setError('Please upload a PDF file')
    }
  }

  const handleSubmit = async () => {
    if (!user) return
    
    setSaving(true)
    setError('')

    try {
      // Upload resume to Supabase Storage if exists
      let resumeUrl = null
      
      if (profileData.resume_file) {
        const fileName = `${user.id}/resume_${Date.now()}.pdf`
        const { data: uploadData, error: uploadError } = await supabase.storage
          .from('resumes')
          .upload(fileName, profileData.resume_file)
        
        if (uploadError) {
          console.error('Upload error:', uploadError)
        } else {
          const { data: { publicUrl } } = supabase.storage
            .from('resumes')
            .getPublicUrl(fileName)
          resumeUrl = publicUrl
        }
      }

      // Prepare the request body
      const requestBody = {
        user_id: user.id,
        user_type: profileData.user_type,
        // Student fields
        college_name: profileData.college_name || null,
        degree: profileData.degree || null,
        branch: profileData.branch || null,
        year_of_study: profileData.year_of_study || null,
        graduation_year: profileData.graduation_year ? parseInt(profileData.graduation_year) : null,
        cgpa: profileData.cgpa || null,
        // Professional fields
        current_job_title: profileData.current_job_title || null,
        current_company: profileData.current_company || null,
        years_of_experience: profileData.years_of_experience ? parseInt(profileData.years_of_experience) : null,
        current_tech_stack: profileData.current_tech_stack,
        reason_for_switching: profileData.reason_for_switching || null,
        // Common fields
        career_goal: profileData.career_goal || null,
        target_companies: profileData.target_companies,
        preferred_work_type: profileData.preferred_work_type || null,
        extra_skills: profileData.extra_skills,
        certificates: profileData.certificates,
        job_search_timeline: profileData.job_search_timeline || null,
        // Existing fields
        github_username: profileData.github_username || null,
        leetcode_username: profileData.leetcode_username || null,
        linkedin_url: profileData.linkedin_url || null,
        resume_url: resumeUrl,
      }

      // Get session token for authorization
      const { data: { session } } = await supabase.auth.getSession()

      // Call POST /api/v1/profile/save
      const response = await fetch(`${apiUrl}/api/v1/profile/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.access_token}`
        },
        body: JSON.stringify(requestBody),
      })

      const result = await response.json()

      if (!response.ok) {
        console.error('API error:', result)
        setError('Failed to save profile. Please try again.')
        setSaving(false)
        return
      }

      // Redirect to analysis
      window.location.href = '/analysis'
    } catch (err) {
      console.error('Error:', err)
      setError('An error occurred. Please try again.')
      setSaving(false)
    }
  }

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return !!profileData.user_type
      case 2:
        if (profileData.user_type === 'student') {
          return !!profileData.college_name && !!profileData.degree && !!profileData.branch && !!profileData.year_of_study && !!profileData.graduation_year
        } else if (profileData.user_type === 'professional') {
          return !!profileData.current_job_title && !!profileData.current_company && !!profileData.years_of_experience
        } else if (profileData.user_type === 'fresher') {
          return !!profileData.college_name && !!profileData.degree && !!profileData.graduation_year
        } else if (profileData.user_type === 'career_switch') {
          return !!profileData.current_job_title && !!profileData.years_of_experience && !!profileData.reason_for_switching
        }
        return false
      case 3:
        return !!profileData.github_username.trim()
      case 4:
        return !!profileData.leetcode_username.trim()
      case 5:
        return !!profileData.career_goal
      case 6:
        return true // Skills and certificates are optional
      case 7:
        return true // Resume is optional
      default:
        return false
    }
  }

  const userTypeCards = [
    { type: 'student' as UserType, icon: GraduationCap, label: 'Student', desc: 'Currently studying' },
    { type: 'professional' as UserType, icon: Briefcase, label: 'Working Professional', desc: 'Employed and working' },
    { type: 'fresher' as UserType, icon: Sprout, label: 'Fresher', desc: 'Just graduated' },
    { type: 'career_switch' as UserType, icon: ArrowRightLeft, label: 'Career Switch', desc: 'Looking to change roles' },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0F1D2E] via-[#1E3A5F] to-[#0F1D2E]">
      {/* Header */}
      <header className="border-b border-white/10 bg-[#0F1D2E]/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center space-x-2">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-r from-[#6C3FC8] to-[#8B5CF6] flex items-center justify-center">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-white">AI Career Navigator</span>
          </Link>
          <div className="text-sm text-gray-400">
            Step {currentStep} of 7
          </div>
        </div>
      </header>

      {/* Progress Bar */}
      <div className="bg-[#0F1D2E]/50 border-b border-white/10">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between max-w-2xl mx-auto">
            {[1, 2, 3, 4, 5, 6, 7].map((step, index) => (
              <div key={step} className="flex items-center">
                <div
                  className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium transition-all ${
                    currentStep > step
                      ? 'bg-green-500 text-white'
                      : currentStep === step
                      ? 'bg-[#6C3FC8] text-white shadow-[0_0_20px_rgba(108,63,200,0.5)]'
                      : 'bg-white/10 text-gray-500'
                  }`}
                >
                  {currentStep > step ? (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    step
                  )}
                </div>
                {index < 6 && (
                  <div
                    className={`w-16 h-0.5 mx-2 ${
                      currentStep > step ? 'bg-green-500' : 'bg-white/10'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-12">
        <div className="max-w-lg mx-auto">
          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Step Content */}
          <div className="bg-[#1E3A5F]/50 rounded-2xl shadow-2xl p-8 border border-white/10">
            {/* Step 1: Who are you? */}
            {currentStep === 1 && (
              <div className="animate-fade-in">
                <h2 className="text-2xl font-bold text-center text-white mb-2">
                  Who are you?
                </h2>
                <p className="text-gray-400 text-center mb-8">
                  Select your current role
                </p>
                <div className="grid grid-cols-2 gap-4">
                  {userTypeCards.map((card) => (
                    <button
                      key={card.type}
                      onClick={() => setProfileData({ ...profileData, user_type: card.type })}
                      className={`p-6 rounded-xl border-2 transition-all text-left ${
                        profileData.user_type === card.type
                          ? 'border-[#6C3FC8] bg-[#6C3FC8]/20 shadow-[0_0_20px_rgba(108,63,200,0.3)]'
                          : 'border-white/10 bg-white/5 hover:border-white/30'
                      }`}
                    >
                      <card.icon className={`w-8 h-8 mb-3 ${profileData.user_type === card.type ? 'text-[#6C3FC8]' : 'text-gray-400'}`} />
                      <div className="font-semibold text-white">{card.label}</div>
                      <div className="text-sm text-gray-400">{card.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Step 2: Basic Info - Dynamic based on userType */}
            {currentStep === 2 && profileData.user_type === 'student' && (
              <div className="animate-fade-in">
                <h2 className="text-2xl font-bold text-center text-white mb-2">
                  Student Details
                </h2>
                <p className="text-gray-400 text-center mb-6">
                  Tell us about your education
                </p>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">College/University *</label>
                    <input
                      type="text"
                      value={profileData.college_name}
                      onChange={(e) => setProfileData({ ...profileData, college_name: e.target.value })}
                      placeholder="e.g. IIT Bombay"
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Degree *</label>
                    <select
                      value={profileData.degree}
                      onChange={(e) => setProfileData({ ...profileData, degree: e.target.value })}
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    >
                      <option value="" className="bg-[#1E3A5F]">Select degree</option>
                      {DEGREE_OPTIONS.map(d => <option key={d} value={d} className="bg-[#1E3A5F]">{d}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Branch/Major *</label>
                    <input
                      type="text"
                      value={profileData.branch}
                      onChange={(e) => setProfileData({ ...profileData, branch: e.target.value })}
                      placeholder="e.g. Computer Science"
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Year of Study *</label>
                    <select
                      value={profileData.year_of_study}
                      onChange={(e) => setProfileData({ ...profileData, year_of_study: e.target.value })}
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    >
                      <option value="" className="bg-[#1E3A5F]">Select year</option>
                      {YEAR_OF_STUDY_OPTIONS.map(y => <option key={y} value={y} className="bg-[#1E3A5F]">{y}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Expected Graduation Year *</label>
                    <input
                      type="number"
                      value={profileData.graduation_year}
                      onChange={(e) => setProfileData({ ...profileData, graduation_year: e.target.value })}
                      placeholder="e.g. 2026"
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">CGPA (optional)</label>
                    <input
                      type="text"
                      value={profileData.cgpa}
                      onChange={(e) => setProfileData({ ...profileData, cgpa: e.target.value })}
                      placeholder="e.g. 8.5"
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    />
                  </div>
                </div>
              </div>
            )}

            {currentStep === 2 && profileData.user_type === 'professional' && (
              <div className="animate-fade-in">
                <h2 className="text-2xl font-bold text-center text-white mb-2">
                  Professional Details
                </h2>
                <p className="text-gray-400 text-center mb-6">
                  Tell us about your work experience
                </p>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Current Job Title *</label>
                    <input
                      type="text"
                      value={profileData.current_job_title}
                      onChange={(e) => setProfileData({ ...profileData, current_job_title: e.target.value })}
                      placeholder="e.g. Software Engineer"
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Current Company *</label>
                    <input
                      type="text"
                      value={profileData.current_company}
                      onChange={(e) => setProfileData({ ...profileData, current_company: e.target.value })}
                      placeholder="e.g. Google"
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Years of Experience *</label>
                    <select
                      value={profileData.years_of_experience}
                      onChange={(e) => setProfileData({ ...profileData, years_of_experience: e.target.value })}
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    >
                      <option value="" className="bg-[#1E3A5F]">Select experience</option>
                      {EXPERIENCE_OPTIONS.map(e => <option key={e} value={e} className="bg-[#1E3A5F]">{e} years</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Current Tech Stack</label>
                    <div className="flex flex-wrap gap-2 mb-2">
                      {profileData.current_tech_stack.map((tech, index) => (
                        <span key={index} className="inline-flex items-center px-3 py-1 rounded-full bg-[#6C3FC8]/20 text-[#6C3FC8] text-sm">
                          {tech}
                          <button onClick={() => removeTag('current_tech_stack', index)} className="ml-2 hover:text-white">
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                    <input
                      type="text"
                      value={techStackInput}
                      onChange={(e) => setTechStackInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('current_tech_stack', techStackInput, setTechStackInput))}
                      placeholder="Type skill and press Enter"
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Reason for switching (optional)</label>
                    <textarea
                      value={profileData.reason_for_switching}
                      onChange={(e) => setProfileData({ ...profileData, reason_for_switching: e.target.value })}
                      placeholder="Why are you looking to switch?"
                      rows={3}
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent resize-none"
                    />
                  </div>
                </div>
              </div>
            )}

            {currentStep === 2 && profileData.user_type === 'fresher' && (
              <div className="animate-fade-in">
                <h2 className="text-2xl font-bold text-center text-white mb-2">
                  Fresher Details
                </h2>
                <p className="text-gray-400 text-center mb-6">
                  Tell us about your recent graduation
                </p>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">College/University</label>
                    <input
                      type="text"
                      value={profileData.college_name}
                      onChange={(e) => setProfileData({ ...profileData, college_name: e.target.value })}
                      placeholder="e.g. IIT Bombay"
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Degree</label>
                    <select
                      value={profileData.degree}
                      onChange={(e) => setProfileData({ ...profileData, degree: e.target.value })}
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    >
                      <option value="" className="bg-[#1E3A5F]">Select degree</option>
                      {DEGREE_OPTIONS.map(d => <option key={d} value={d} className="bg-[#1E3A5F]">{d}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Graduation Year</label>
                    <input
                      type="number"
                      value={profileData.graduation_year}
                      onChange={(e) => setProfileData({ ...profileData, graduation_year: e.target.value })}
                      placeholder="e.g. 2025"
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">CGPA (optional)</label>
                    <input
                      type="text"
                      value={profileData.cgpa}
                      onChange={(e) => setProfileData({ ...profileData, cgpa: e.target.value })}
                      placeholder="e.g. 8.5"
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    />
                  </div>
                </div>
              </div>
            )}

            {currentStep === 2 && profileData.user_type === 'career_switch' && (
              <div className="animate-fade-in">
                <h2 className="text-2xl font-bold text-center text-white mb-2">
                  Career Switch Details
                </h2>
                <p className="text-gray-400 text-center mb-6">
                  Tell us about your background
                </p>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Current/Previous Job Title *</label>
                    <input
                      type="text"
                      value={profileData.current_job_title}
                      onChange={(e) => setProfileData({ ...profileData, current_job_title: e.target.value })}
                      placeholder="e.g. QA Engineer"
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Years of Experience *</label>
                    <select
                      value={profileData.years_of_experience}
                      onChange={(e) => setProfileData({ ...profileData, years_of_experience: e.target.value })}
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    >
                      <option value="" className="bg-[#1E3A5F]">Select experience</option>
                      {EXPERIENCE_OPTIONS.map(e => <option key={e} value={e} className="bg-[#1E3A5F]">{e} years</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Reason for switching *</label>
                    <textarea
                      value={profileData.reason_for_switching}
                      onChange={(e) => setProfileData({ ...profileData, reason_for_switching: e.target.value })}
                      placeholder="Why do you want to switch careers?"
                      rows={4}
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent resize-none"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: GitHub */}
            {currentStep === 3 && (
              <div className="animate-fade-in">
                <div className="flex items-center justify-center mb-6">
                  <div className="w-16 h-16 rounded-2xl bg-gray-900 flex items-center justify-center">
                    <Github className="w-8 h-8 text-white" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold text-center text-white mb-2">
                  Connect GitHub
                </h2>
                <p className="text-gray-400 text-center mb-6">
                  We'll analyze your repositories and coding activity
                </p>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    GitHub Username <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={profileData.github_username}
                    onChange={(e) => setProfileData({ ...profileData, github_username: e.target.value })}
                    placeholder="e.g. torvalds"
                    className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                  />
                </div>
              </div>
            )}

            {/* Step 4: LeetCode */}
            {currentStep === 4 && (
              <div className="animate-fade-in">
                <div className="flex items-center justify-center mb-6">
                  <div className="w-16 h-16 rounded-2xl bg-yellow-500/20 flex items-center justify-center">
                    <Code className="w-8 h-8 text-yellow-400" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold text-center text-white mb-2">
                  Connect LeetCode
                </h2>
                <p className="text-gray-400 text-center mb-6">
                  We'll analyze your problem-solving skills
                </p>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    LeetCode Username <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={profileData.leetcode_username}
                    onChange={(e) => setProfileData({ ...profileData, leetcode_username: e.target.value })}
                    placeholder="e.g. johndoe"
                    className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                  />
                </div>
              </div>
            )}

            {/* Step 5: LinkedIn & Career Goal */}
            {currentStep === 5 && (
              <div className="animate-fade-in">
                <div className="flex items-center justify-center mb-6">
                  <div className="w-16 h-16 rounded-2xl bg-blue-500/20 flex items-center justify-center">
                    <Linkedin className="w-8 h-8 text-blue-400" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold text-center text-white mb-2">
                  Career Goals
                </h2>
                <p className="text-gray-400 text-center mb-6">
                  Define your target role
                </p>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">LinkedIn URL (optional)</label>
                    <input
                      type="url"
                      value={profileData.linkedin_url}
                      onChange={(e) => setProfileData({ ...profileData, linkedin_url: e.target.value })}
                      placeholder="https://linkedin.com/in/yourname"
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Career Goal <span className="text-red-400">*</span></label>
                    <select
                      value={profileData.career_goal}
                      onChange={(e) => setProfileData({ ...profileData, career_goal: e.target.value })}
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    >
                      <option value="" className="bg-[#1E3A5F]">Select career goal</option>
                      {CAREER_GOAL_OPTIONS.map(g => <option key={g} value={g} className="bg-[#1E3A5F]">{g}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Target Companies</label>
                    <div className="flex flex-wrap gap-2 mb-2">
                      {profileData.target_companies.map((company, index) => (
                        <span key={index} className="inline-flex items-center px-3 py-1 rounded-full bg-[#6C3FC8]/20 text-[#6C3FC8] text-sm">
                          {company}
                          <button onClick={() => removeTag('target_companies', index)} className="ml-2 hover:text-white">
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                    <input
                      type="text"
                      value={targetCompanyInput}
                      onChange={(e) => setTargetCompanyInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('target_companies', targetCompanyInput, setTargetCompanyInput))}
                      placeholder="Type company and press Enter"
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Job Search Timeline</label>
                    <select
                      value={profileData.job_search_timeline}
                      onChange={(e) => setProfileData({ ...profileData, job_search_timeline: e.target.value })}
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    >
                      <option value="" className="bg-[#1E3A5F]">Select timeline</option>
                      {TIMELINE_OPTIONS.map(t => <option key={t} value={t} className="bg-[#1E3A5F]">{t}</option>)}
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Step 6: Skills & Certificates */}
            {currentStep === 6 && (
              <div className="animate-fade-in">
                <h2 className="text-2xl font-bold text-center text-white mb-2">
                  Skills & Certificates
                </h2>
                <p className="text-gray-400 text-center mb-6">
                  Show us what you know
                </p>
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Current Skills</label>
                    <div className="flex flex-wrap gap-2 mb-3">
                      {COMMON_SKILLS.map(skill => (
                        <button
                          key={skill}
                          onClick={() => {
                            if (!profileData.extra_skills.includes(skill)) {
                              setProfileData(prev => ({
                                ...prev,
                                extra_skills: [...prev.extra_skills, skill]
                              }))
                            }
                          }}
                          className={`px-3 py-1 rounded-full text-sm transition-all ${
                            profileData.extra_skills.includes(skill)
                              ? 'bg-[#6C3FC8] text-white'
                              : 'bg-white/10 text-gray-300 hover:bg-white/20'
                          }`}
                        >
                          + {skill}
                        </button>
                      ))}
                    </div>
                    <div className="flex flex-wrap gap-2 mb-2">
                      {profileData.extra_skills.map((skill, index) => (
                        <span key={index} className="inline-flex items-center px-3 py-1 rounded-full bg-[#6C3FC8]/20 text-[#6C3FC8] text-sm">
                          {skill}
                          <button onClick={() => removeTag('extra_skills', index)} className="ml-2 hover:text-white">
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                    <input
                      type="text"
                      value={skillInput}
                      onChange={(e) => setSkillInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('extra_skills', skillInput, setSkillInput))}
                      placeholder="Add custom skill and press Enter"
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Certificates (optional)</label>
                    <div className="flex flex-wrap gap-2 mb-2">
                      {profileData.certificates.map((cert, index) => (
                        <span key={index} className="inline-flex items-center px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-sm">
                          {cert}
                          <button onClick={() => removeTag('certificates', index)} className="ml-2 hover:text-white">
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                    <input
                      type="text"
                      value={certificateInput}
                      onChange={(e) => setCertificateInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag('certificates', certificateInput, setCertificateInput))}
                      placeholder="Type certificate and press Enter"
                      className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#6C3FC8] focus:border-transparent"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Step 7: Resume Upload */}
            {currentStep === 7 && (
              <div className="animate-fade-in">
                <div className="flex items-center justify-center mb-6">
                  <div className="w-16 h-16 rounded-2xl bg-[#6C3FC8]/20 flex items-center justify-center">
                    <FileText className="w-8 h-8 text-[#6C3FC8]" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold text-center text-white mb-2">
                  Upload Resume
                </h2>
                <p className="text-gray-400 text-center mb-6">
                  Upload your resume for deeper analysis (optional)
                </p>
                
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-white/20 rounded-xl p-8 text-center cursor-pointer hover:border-[#6C3FC8] hover:bg-[#6C3FC8]/5 transition-all"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  {profileData.resume_file ? (
                    <div className="flex flex-col items-center">
                      <FileText className="w-12 h-12 text-green-400 mb-2" />
                      <p className="font-medium text-white">{profileData.resume_file.name}</p>
                      <p className="text-sm text-gray-400">Click to change file</p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center">
                      <Upload className="w-12 h-12 text-gray-400 mb-2" />
                      <p className="font-medium text-white">Click to upload PDF</p>
                      <p className="text-sm text-gray-400">Maximum file size: 5MB</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Navigation Buttons */}
            <div className="flex justify-between mt-8">
              <Button
                variant="outline"
                onClick={handleBack}
                disabled={currentStep === 1 || saving}
                className="border-white/20 text-white hover:bg-white/10"
              >
                <ChevronLeft className="w-4 h-4 mr-2" />
                Back
              </Button>

              {currentStep < 7 ? (
                <Button
                  onClick={handleNext}
                  disabled={!canProceed()}
                  className="bg-[#6C3FC8] hover:bg-[#6C3FC8]/90"
                >
                  Next
                  <ChevronRight className="w-4 h-4 ml-2" />
                </Button>
              ) : (
                <Button
                  onClick={handleSubmit}
                  disabled={saving}
                  className="bg-[#6C3FC8] hover:bg-[#6C3FC8]/90"
                >
                  {saving ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      Start Analysis
                      <ChevronRight className="w-4 h-4 ml-2" />
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
