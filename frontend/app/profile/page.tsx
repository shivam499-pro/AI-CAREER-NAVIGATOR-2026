'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import Navbar from '@/components/Navbar'
import { 
  Brain, Loader2, Save, Plus, X, CheckCircle,
  GraduationCap, Code, Briefcase, Award, Target,
  ArrowRight
} from 'lucide-react'

interface ProfileData {
  college_name: string
  degree: string
  branch: string
  current_year: string
  graduation_year: number
  cgpa: number
  extra_skills: string[]
  experience: { company: string; role: string; duration: string; description: string }[]
  certificates: { name: string; issuer: string }[]
  target_companies: string[]
  preferred_location: string
  career_goal: string
  open_to: string
  codechef_rating: number
  codeforces_rating: number
  hackathon_wins: number
}

const initialProfile: ProfileData = {
  college_name: '',
  degree: '',
  branch: '',
  current_year: '',
  graduation_year: 0,
  cgpa: 0,
  extra_skills: [],
  experience: [],
  certificates: [],
  target_companies: [],
  preferred_location: '',
  career_goal: '',
  open_to: 'Both',
  codechef_rating: 0,
  codeforces_rating: 0,
  hackathon_wins: 0
}

export default function ProfilePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [user, setUser] = useState<{ id: string } | null>(null)
  const [profile, setProfile] = useState<ProfileData>(initialProfile)
  const [githubConnected, setGithubConnected] = useState(false)
  const [leetcodeConnected, setLeetcodeConnected] = useState(false)
  const [resumeUploaded, setResumeUploaded] = useState(false)

  // Tag input states
  const [skillInput, setSkillInput] = useState('')
  const [companyInput, setCompanyInput] = useState('')

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        router.push('/auth/login')
        return
      }
      setUser(user)
      await loadProfile(user.id)
    }
    checkAuth()
  }, [router])

  const loadProfile = async (userId: string) => {
    try {
      // Load basic profile
      const { data: profileData } = await supabase
        .from('profiles')
        .select('*')
        .eq('user_id', userId)
        .single()

      if (profileData) {
        setGithubConnected(!!profileData.github_username)
        setLeetcodeConnected(!!profileData.leetcode_username)
        setResumeUploaded(!!profileData.resume_text)

        setProfile({
          college_name: profileData.college_name || '',
          degree: profileData.degree || '',
          branch: profileData.branch || '',
          current_year: profileData.current_year || '',
          graduation_year: profileData.graduation_year || 0,
          cgpa: profileData.cgpa || 0,
          extra_skills: profileData.extra_skills || [],
          experience: profileData.experience || [],
          certificates: profileData.certificates || [],
          target_companies: profileData.target_companies || [],
          preferred_location: profileData.preferred_location || '',
          career_goal: profileData.career_goal || '',
          open_to: profileData.open_to || 'Both',
          codechef_rating: profileData.codechef_rating || 0,
          codeforces_rating: profileData.codeforces_rating || 0,
          hackathon_wins: profileData.hackathon_wins || 0
        })
      }
    } catch (err) {
      console.error('Error loading profile:', err)
    } finally {
      setLoading(false)
    }
  }

  const calculateCompleteness = () => {
    let score = 0
    if (githubConnected) score += 20
    if (leetcodeConnected) score += 20
    if (resumeUploaded) score += 20
    if (profile.college_name && profile.degree) score += 15
    if (profile.extra_skills.length >= 3) score += 10
    if (profile.experience.length > 0) score += 10
    if (profile.career_goal) score += 5
    return score
  }

  const handleSave = async () => {
    if (!user) return
    
    setSaving(true)
    try {
      const { error } = await supabase
        .from('profiles')
        .update({
          college_name: profile.college_name,
          degree: profile.degree,
          branch: profile.branch,
          current_year: profile.current_year,
          graduation_year: profile.graduation_year,
          cgpa: profile.cgpa,
          extra_skills: profile.extra_skills,
          experience: profile.experience,
          certificates: profile.certificates,
          target_companies: profile.target_companies,
          preferred_location: profile.preferred_location,
          career_goal: profile.career_goal,
          open_to: profile.open_to,
          codechef_rating: profile.codechef_rating,
          codeforces_rating: profile.codeforces_rating,
          hackathon_wins: profile.hackathon_wins
        })
        .eq('user_id', user.id)

      if (error) throw error
      
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      console.error('Error saving profile:', err)
    } finally {
      setSaving(false)
    }
  }

  const addSkill = () => {
    if (skillInput.trim() && !profile.extra_skills.includes(skillInput.trim())) {
      setProfile({ ...profile, extra_skills: [...profile.extra_skills, skillInput.trim()] })
      setSkillInput('')
    }
  }

  const removeSkill = (index: number) => {
    setProfile({ ...profile, extra_skills: profile.extra_skills.filter((_, i) => i !== index) })
  }

  const addCompany = () => {
    if (companyInput.trim() && !profile.target_companies.includes(companyInput.trim())) {
      setProfile({ ...profile, target_companies: [...profile.target_companies, companyInput.trim()] })
      setCompanyInput('')
    }
  }

  const removeCompany = (index: number) => {
    setProfile({ ...profile, target_companies: profile.target_companies.filter((_, i) => i !== index) })
  }

  const addExperience = () => {
    setProfile({
      ...profile,
      experience: [...profile.experience, { company: '', role: '', duration: '', description: '' }]
    })
  }

  const updateExperience = (index: number, field: string, value: string) => {
    const updated = [...profile.experience]
    updated[index] = { ...updated[index], [field]: value }
    setProfile({ ...profile, experience: updated })
  }

  const removeExperience = (index: number) => {
    setProfile({ ...profile, experience: profile.experience.filter((_, i) => i !== index) })
  }

  const addCertificate = () => {
    setProfile({
      ...profile,
      certificates: [...profile.certificates, { name: '', issuer: '' }]
    })
  }

  const updateCertificate = (index: number, field: string, value: string) => {
    const updated = [...profile.certificates]
    updated[index] = { ...updated[index], [field]: value }
    setProfile({ ...profile, certificates: updated })
  }

  const removeCertificate = (index: number) => {
    setProfile({ ...profile, certificates: profile.certificates.filter((_, i) => i !== index) })
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  const completeness = calculateCompleteness()

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-lg font-semibold text-foreground">Profile Completeness</h2>
            <span className="text-lg font-bold text-[#6C3FC8]">{completeness}%</span>
          </div>
          <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-[#1E3A5F] to-[#6C3FC8] transition-all duration-500"
              style={{ width: `${completeness}%` }}
            />
          </div>
          <div className="flex flex-wrap gap-2 mt-2 text-xs text-muted-foreground">
            <span className={githubConnected ? 'text-green-600' : ''}>GitHub {githubConnected ? '✓' : '○'}</span>
            <span className={leetcodeConnected ? 'text-green-600' : ''}>LeetCode {leetcodeConnected ? '✓' : '○'}</span>
            <span className={resumeUploaded ? 'text-green-600' : ''}>Resume {resumeUploaded ? '✓' : '○'}</span>
            <span className={profile.college_name && profile.degree ? 'text-green-600' : ''}>Academic {profile.college_name && profile.degree ? '✓' : '○'}</span>
            <span className={profile.extra_skills.length >= 3 ? 'text-green-600' : ''}>Skills {profile.extra_skills.length >= 3 ? '✓' : '○'}</span>
            <span className={profile.experience.length > 0 ? 'text-green-600' : ''}>Experience {profile.experience.length > 0 ? '✓' : '○'}</span>
            <span className={profile.career_goal ? 'text-green-600' : ''}>Goals {profile.career_goal ? '✓' : '○'}</span>
          </div>
        </div>

        {/* Success Message */}
        {saved && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-600" />
            <p className="text-green-600 font-medium">Profile saved successfully!</p>
          </div>
        )}

        {/* Section 1: Academic Info */}
        <section className="bg-card rounded-xl border p-6 mb-6">
          <h3 className="text-xl font-bold text-[#1E3A5F] mb-4 flex items-center gap-2">
            <GraduationCap className="w-5 h-5" />
            Academic Information
          </h3>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">College Name</label>
              <input
                type="text"
                value={profile.college_name}
                onChange={(e) => setProfile({ ...profile, college_name: e.target.value })}
                className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
                placeholder="Enter college name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Degree</label>
              <select
                value={profile.degree}
                onChange={(e) => setProfile({ ...profile, degree: e.target.value })}
                className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
              >
                <option value="">Select Degree</option>
                <option value="B.Tech">B.Tech</option>
                <option value="BCA">BCA</option>
                <option value="MCA">MCA</option>
                <option value="B.Sc">B.Sc</option>
                <option value="MBA">MBA</option>
                <option value="Other">Other</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Branch</label>
              <select
                value={profile.branch}
                onChange={(e) => setProfile({ ...profile, branch: e.target.value })}
                className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
              >
                <option value="">Select Branch</option>
                <option value="CSE">CSE</option>
                <option value="IT">IT</option>
                <option value="ECE">ECE</option>
                <option value="Mechanical">Mechanical</option>
                <option value="Civil">Civil</option>
                <option value="Other">Other</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Current Year</label>
              <select
                value={profile.current_year}
                onChange={(e) => setProfile({ ...profile, current_year: e.target.value })}
                className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
              >
                <option value="">Select Year</option>
                <option value="1st Year">1st Year</option>
                <option value="2nd Year">2nd Year</option>
                <option value="3rd Year">3rd Year</option>
                <option value="Final Year">Final Year</option>
                <option value="Graduated">Graduated</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Graduation Year</label>
              <input
                type="number"
                value={profile.graduation_year || ''}
                onChange={(e) => setProfile({ ...profile, graduation_year: parseInt(e.target.value) || 0 })}
                className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
                placeholder="2026"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">CGPA (0-10)</label>
              <input
                type="number"
                step="0.1"
                max="10"
                value={profile.cgpa || ''}
                onChange={(e) => setProfile({ ...profile, cgpa: parseFloat(e.target.value) || 0 })}
                className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
                placeholder="8.5"
              />
            </div>
          </div>
        </section>

        {/* Section 2: Technical Skills */}
        <section className="bg-card rounded-xl border p-6 mb-6">
          <h3 className="text-xl font-bold text-[#1E3A5F] mb-4 flex items-center gap-2">
            <Code className="w-5 h-5" />
            Technical Skills
          </h3>
          <div className="flex flex-wrap gap-2 mb-3">
            {profile.extra_skills.map((skill, i) => (
              <span key={i} className="px-3 py-1 bg-[#6C3FC8]/10 text-[#6C3FC8] rounded-full flex items-center gap-1">
                {skill}
                <button onClick={() => removeSkill(i)} className="hover:text-red-500">
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={skillInput}
              onChange={(e) => setSkillInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && addSkill()}
              className="flex-1 p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
              placeholder="Type a skill and press Enter (e.g. React, Node.js, Docker)"
            />
            <Button onClick={addSkill} className="bg-[#6C3FC8] hover:bg-[#6C3FC8]/90">
              <Plus className="w-4 h-4 mr-1" /> Add
            </Button>
          </div>
        </section>

        {/* Section 3: Experience */}
        <section className="bg-card rounded-xl border p-6 mb-6">
          <h3 className="text-xl font-bold text-[#1E3A5F] mb-4 flex items-center gap-2">
            <Briefcase className="w-5 h-5" />
            Experience
          </h3>
          {profile.experience.map((exp, i) => (
            <div key={i} className="border rounded-lg p-4 mb-3">
              <div className="grid md:grid-cols-3 gap-3 mb-2">
                <input
                  type="text"
                  value={exp.company}
                  onChange={(e) => updateExperience(i, 'company', e.target.value)}
                  className="p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
                  placeholder="Company/Organization"
                />
                <select
                  value={exp.role}
                  onChange={(e) => updateExperience(i, 'role', e.target.value)}
                  className="p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
                >
                  <option value="">Select Role</option>
                  <option value="Intern">Intern</option>
                  <option value="Part-time">Part-time</option>
                  <option value="Freelance">Freelance</option>
                  <option value="Full-time">Full-time</option>
                </select>
                <input
                  type="text"
                  value={exp.duration}
                  onChange={(e) => updateExperience(i, 'duration', e.target.value)}
                  className="p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
                  placeholder="Duration (e.g. 3 months)"
                />
              </div>
              <textarea
                value={exp.description}
                onChange={(e) => updateExperience(i, 'description', e.target.value)}
                className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none mb-2"
                placeholder="What did you build/do?"
                rows={2}
              />
              <button onClick={() => removeExperience(i)} className="text-red-500 text-sm flex items-center gap-1">
                <X className="w-3 h-3" /> Remove
              </button>
            </div>
          ))}
          <Button onClick={addExperience} variant="outline" className="border-[#6C3FC8] text-[#6C3FC8]">
            <Plus className="w-4 h-4 mr-1" /> Add Experience
          </Button>
        </section>

        {/* Section 4: Achievements */}
        <section className="bg-card rounded-xl border p-6 mb-6">
          <h3 className="text-xl font-bold text-[#1E3A5F] mb-4 flex items-center gap-2">
            <Award className="w-5 h-5" />
            Achievements
          </h3>
          
          <h4 className="font-medium mb-2">Certificates</h4>
          {profile.certificates.map((cert, i) => (
            <div key={i} className="flex gap-2 mb-2">
              <input
                type="text"
                value={cert.name}
                onChange={(e) => updateCertificate(i, 'name', e.target.value)}
                className="flex-1 p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
                placeholder="Certificate name"
              />
              <input
                type="text"
                value={cert.issuer}
                onChange={(e) => updateCertificate(i, 'issuer', e.target.value)}
                className="flex-1 p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
                placeholder="Issuer (e.g. AWS - Amazon)"
              />
              <button onClick={() => removeCertificate(i)} className="text-red-500">
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
          <Button onClick={addCertificate} variant="outline" className="border-[#6C3FC8] text-[#6C3FC8] mb-4">
            <Plus className="w-4 h-4 mr-1" /> Add Certificate
          </Button>

          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Hackathon Wins</label>
              <input
                type="number"
                value={profile.hackathon_wins || ''}
                onChange={(e) => setProfile({ ...profile, hackathon_wins: parseInt(e.target.value) || 0 })}
                className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
                placeholder="0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">CodeChef Rating</label>
              <input
                type="number"
                value={profile.codechef_rating || ''}
                onChange={(e) => setProfile({ ...profile, codechef_rating: parseInt(e.target.value) || 0 })}
                className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
                placeholder="1500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Codeforces Rating</label>
              <input
                type="number"
                value={profile.codeforces_rating || ''}
                onChange={(e) => setProfile({ ...profile, codeforces_rating: parseInt(e.target.value) || 0 })}
                className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
                placeholder="1200"
              />
            </div>
          </div>
        </section>

        {/* Section 5: Career Goals */}
        <section className="bg-card rounded-xl border p-6 mb-6">
          <h3 className="text-xl font-bold text-[#1E3A5F] mb-4 flex items-center gap-2">
            <Target className="w-5 h-5" />
            Career Goals
          </h3>
          <div className="grid md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">Target Role</label>
              <input
                type="text"
                value={profile.career_goal}
                onChange={(e) => setProfile({ ...profile, career_goal: e.target.value })}
                className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
                placeholder="e.g. Full Stack Developer"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Preferred Location</label>
              <input
                type="text"
                value={profile.preferred_location}
                onChange={(e) => setProfile({ ...profile, preferred_location: e.target.value })}
                className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
                placeholder="e.g. Bangalore, Remote"
              />
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Open To</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="open_to"
                  checked={profile.open_to === 'Internship'}
                  onChange={() => setProfile({ ...profile, open_to: 'Internship' })}
                />
                Internship
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="open_to"
                  checked={profile.open_to === 'Full-time'}
                  onChange={() => setProfile({ ...profile, open_to: 'Full-time' })}
                />
                Full-time
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="open_to"
                  checked={profile.open_to === 'Both'}
                  onChange={() => setProfile({ ...profile, open_to: 'Both' })}
                />
                Both
              </label>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Target Companies</label>
            <div className="flex flex-wrap gap-2 mb-2">
              {profile.target_companies.map((company, i) => (
                <span key={i} className="px-3 py-1 bg-[#1E3A5F]/10 text-[#1E3A5F] rounded-full flex items-center gap-1">
                  {company}
                  <button onClick={() => removeCompany(i)} className="hover:text-red-500">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={companyInput}
                onChange={(e) => setCompanyInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addCompany()}
                className="flex-1 p-2 border rounded-lg focus:ring-2 focus:ring-[#6C3FC8] outline-none"
                placeholder="Type company name and press Enter"
              />
              <Button onClick={addCompany} className="bg-[#6C3FC8] hover:bg-[#6C3FC8]/90">
                <Plus className="w-4 h-4 mr-1" /> Add
              </Button>
            </div>
          </div>
        </section>

        {/* Save Button */}
        <div className="flex justify-center gap-4 mb-8">
          <Button 
            onClick={handleSave} 
            disabled={saving}
            className="bg-[#1E3A5F] hover:bg-[#1E3A5F]/90 px-8"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Save Profile
              </>
            )}
          </Button>
        </div>

        {/* Navigation Buttons */}
        <div className="flex justify-center gap-4">
          <Link href="/analysis">
            <Button variant="outline" className="border-[#1E3A5F] text-[#1E3A5F]">
              Go to Analysis
              <ArrowRight className="ml-2 w-4 h-4" />
            </Button>
          </Link>
          <Link href="/interview">
            <Button className="bg-[#6C3FC8] hover:bg-[#6C3FC8]/90">
              Practice Interview
            </Button>
          </Link>
        </div>
      </main>
    </div>
  )
}
