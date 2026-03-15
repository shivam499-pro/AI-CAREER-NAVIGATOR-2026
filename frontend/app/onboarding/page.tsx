'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import { Brain, Github, Code, Linkedin, FileText, ChevronRight, ChevronLeft, Loader2, Upload } from 'lucide-react'

interface ProfileData {
  github_username: string
  leetcode_username: string
  linkedin_url: string
  resume_file: File | null
}

export default function OnboardingPage() {
  const [currentStep, setCurrentStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [user, setUser] = useState<{ id: string } | null>(null)
  const [profileData, setProfileData] = useState<ProfileData>({
    github_username: '',
    leetcode_username: '',
    linkedin_url: '',
    resume_file: null,
  })
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Check authentication on mount
  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        window.location.href = '/auth/login'
        return
      }
      setUser(user)
    }
    checkAuth()
  }, [])

  const handleNext = () => {
    if (currentStep < 4) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
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

      // Save profile to database
      const { error: dbError } = await supabase
        .from('profiles')
        .insert({
          user_id: user.id,
          github_username: profileData.github_username || null,
          leetcode_username: profileData.leetcode_username || null,
          linkedin_url: profileData.linkedin_url || null,
          resume_url: resumeUrl,
        })

      if (dbError) {
        console.error('Database error:', dbError)
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
        return profileData.github_username.trim().length > 0
      case 2:
        return profileData.leetcode_username.trim().length > 0
      case 3:
        return true // LinkedIn is optional
      case 4:
        return true // Resume is optional
      default:
        return false
    }
  }

  const steps = [
    { number: 1, title: 'GitHub', icon: Github },
    { number: 2, title: 'LeetCode', icon: Code },
    { number: 3, title: 'LinkedIn', icon: Linkedin },
    { number: 4, title: 'Resume', icon: FileText },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center space-x-2">
            <div className="w-10 h-10 rounded-lg gradient-primary flex items-center justify-center">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-primary">AI Career Navigator</span>
          </Link>
          <div className="text-sm text-muted-foreground">
            Step {currentStep} of 4
          </div>
        </div>
      </header>

      {/* Progress Bar */}
      <div className="bg-white border-b">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between max-w-md mx-auto">
            {steps.map((step, index) => (
              <div key={step.number} className="flex items-center">
                <div
                  className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium transition-all ${
                    currentStep > step.number
                      ? 'bg-success text-white'
                      : currentStep === step.number
                      ? 'bg-primary text-white'
                      : 'bg-gray-200 text-gray-500'
                  }`}
                >
                  {currentStep > step.number ? (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    step.number
                  )}
                </div>
                {index < steps.length - 1 && (
                  <div
                    className={`w-12 h-0.5 mx-2 ${
                      currentStep > step.number ? 'bg-success' : 'bg-gray-200'
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
        <div className="max-w-md mx-auto">
          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-error/10 border border-error/20 rounded-lg text-error text-sm">
              {error}
            </div>
          )}

          {/* Step Content */}
          <div className="bg-card rounded-2xl shadow-card p-8 border">
            {/* Step 1: GitHub */}
            {currentStep === 1 && (
              <div className="animate-fade-in">
                <div className="flex items-center justify-center mb-6">
                  <div className="w-16 h-16 rounded-2xl bg-gray-900 flex items-center justify-center">
                    <Github className="w-8 h-8 text-white" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold text-center text-foreground mb-2">
                  Connect GitHub
                </h2>
                <p className="text-muted-foreground text-center mb-6">
                  Enter your GitHub username so we can analyze your repositories and coding activity.
                </p>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    GitHub Username
                  </label>
                  <input
                    type="text"
                    value={profileData.github_username}
                    onChange={(e) => setProfileData({ ...profileData, github_username: e.target.value })}
                    placeholder="e.g. torvalds"
                    className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                  />
                  <p className="text-sm text-muted-foreground mt-2">
                    Enter just your username, not the full URL
                  </p>
                </div>
              </div>
            )}

            {/* Step 2: LeetCode */}
            {currentStep === 2 && (
              <div className="animate-fade-in">
                <div className="flex items-center justify-center mb-6">
                  <div className="w-16 h-16 rounded-2xl bg-warning/20 flex items-center justify-center">
                    <Code className="w-8 h-8 text-warning" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold text-center text-foreground mb-2">
                  Connect LeetCode
                </h2>
                <p className="text-muted-foreground text-center mb-6">
                  Enter your LeetCode username to analyze your problem-solving skills.
                </p>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    LeetCode Username
                  </label>
                  <input
                    type="text"
                    value={profileData.leetcode_username}
                    onChange={(e) => setProfileData({ ...profileData, leetcode_username: e.target.value })}
                    placeholder="e.g. johndoe"
                    className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                  />
                </div>
              </div>
            )}

            {/* Step 3: LinkedIn */}
            {currentStep === 3 && (
              <div className="animate-fade-in">
                <div className="flex items-center justify-center mb-6">
                  <div className="w-16 h-16 rounded-2xl bg-blue-100 flex items-center justify-center">
                    <Linkedin className="w-8 h-8 text-blue-600" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold text-center text-foreground mb-2">
                  Connect LinkedIn
                </h2>
                <p className="text-muted-foreground text-center mb-6">
                  Add your LinkedIn profile (optional) to get more accurate career recommendations.
                </p>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    LinkedIn Profile URL <span className="text-muted-foreground">(optional)</span>
                  </label>
                  <input
                    type="url"
                    value={profileData.linkedin_url}
                    onChange={(e) => setProfileData({ ...profileData, linkedin_url: e.target.value })}
                    placeholder="https://linkedin.com/in/yourname"
                    className="w-full px-4 py-3 rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                  />
                </div>
              </div>
            )}

            {/* Step 4: Resume */}
            {currentStep === 4 && (
              <div className="animate-fade-in">
                <div className="flex items-center justify-center mb-6">
                  <div className="w-16 h-16 rounded-2xl bg-accent-violet/20 flex items-center justify-center">
                    <FileText className="w-8 h-8 text-accent-violet" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold text-center text-foreground mb-2">
                  Upload Resume
                </h2>
                <p className="text-muted-foreground text-center mb-6">
                  Upload your resume (optional) for deeper skills analysis.
                </p>
                
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-input rounded-xl p-8 text-center cursor-pointer hover:border-primary hover:bg-primary/5 transition-all"
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
                      <FileText className="w-12 h-12 text-success mb-2" />
                      <p className="font-medium text-foreground">{profileData.resume_file.name}</p>
                      <p className="text-sm text-muted-foreground">Click to change file</p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center">
                      <Upload className="w-12 h-12 text-muted-foreground mb-2" />
                      <p className="font-medium text-foreground">Click to upload PDF</p>
                      <p className="text-sm text-muted-foreground">Maximum file size: 5MB</p>
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
              >
                <ChevronLeft className="w-4 h-4 mr-2" />
                Back
              </Button>

              {currentStep < 4 ? (
                <Button
                  onClick={handleNext}
                  disabled={!canProceed()}
                  className="bg-primary hover:bg-primary/90"
                >
                  Next
                  <ChevronRight className="w-4 h-4 ml-2" />
                </Button>
              ) : (
                <Button
                  onClick={handleSubmit}
                  disabled={saving}
                  className="bg-primary hover:bg-primary/90"
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

          {/* Step Indicators */}
          <div className="flex justify-center gap-2 mt-6">
            {steps.map((step) => (
              <div
                key={step.number}
                className={`w-2 h-2 rounded-full transition-all ${
                  currentStep === step.number
                    ? 'bg-primary w-6'
                    : currentStep > step.number
                    ? 'bg-success'
                    : 'bg-gray-300'
                }`}
              />
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
