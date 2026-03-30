'use client'
import CareerRoadmap from '@/components/CareerRoadmap'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import Navbar from '@/components/Navbar'
import {
  Brain, Briefcase, Loader2, ArrowRight, Building2,
  Globe, Search, GraduationCap, TrendingUp, ExternalLink, RefreshCw
} from 'lucide-react'

interface CareerPath {
  name?: string
  career_name?: string
  match_percentage?: number
}

export default function JobsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState<{ id: string } | null>(null)
  const [profile, setProfile] = useState<any>(null)
  const [analysis, setAnalysis] = useState<any>(null)
  const [targetCareer, setTargetCareer] = useState('Full Stack Developer')
  const [jobs, setJobs] = useState<any[]>([])
  const [jobsLoading, setJobsLoading] = useState(false)

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        router.push('/auth/login')
        return
      }
      setUser(user)
      await loadUserData(user.id)
    }
    checkAuth()
  }, [router])

  const loadUserData = async (userId: string) => {
    try {
      // Get user's profile
      const { data: profileData } = await supabase
        .from('profiles')
        .select('*')
        .eq('user_id', userId)
        .single()

      if (profileData) {
        setProfile(profileData)
      }

      // Get user's analysis
      const { data: analysisData } = await supabase
        .from('analyses')
        .select('*')
        .eq('user_id', userId)
        .single()

      if (analysisData) {
        setAnalysis(analysisData)
        const careerPaths = analysisData.career_paths || []
        if (Array.isArray(careerPaths) && careerPaths.length > 0) {
          const topPath = careerPaths[0]
          const careerName = topPath?.name || topPath?.career_name || 'Full Stack Developer'
          setTargetCareer(careerName)
          fetchRealJobs(careerName)
        }
      }
    } catch (err) {
      console.error('Error loading user data:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchRealJobs = async (query: string) => {
    setJobsLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/jobs?query=${encodeURIComponent(query)}`)
      const data = await response.json()
      setJobs(data.jobs || [])
    } catch (err) {
      console.error("Failed to fetch jobs:", err)
    } finally {
      setJobsLoading(false)
    }
  }

  // Tech company careers pages
  const techCompanies = [
    {
      name: 'Google',
      careersUrl: 'https://careers.google.com/jobs',
      description: 'Software Engineer, Frontend Developer, Backend Developer',
      color: 'bg-blue-500'
    },
    {
      name: 'Microsoft',
      careersUrl: 'https://careers.microsoft.com',
      description: 'Full Stack Developer, Cloud Engineer, Data Scientist',
      color: 'bg-green-500'
    },
    {
      name: 'Amazon',
      careersUrl: 'https://www.amazon.jobs',
      description: 'Software Development Engineer, DevOps, ML Engineer',
      color: 'bg-orange-500'
    },
    {
      name: 'Meta',
      careersUrl: 'https://metacareers.com',
      description: 'React Developer, iOS/Android Engineer, Backend',
      color: 'bg-blue-600'
    },
    {
      name: 'Apple',
      careersUrl: 'https://jobs.apple.com',
      description: 'Swift Developer, ML Engineer, Systems Engineer',
      color: 'bg-gray-600'
    }
  ]

  // Internship platforms (India focused)
  const internshipPlatforms = [
    {
      name: 'Internshala',
      url: 'https://internshala.com/internships',
      description: 'Free internships for students & freshers in India',
      icon: GraduationCap
    },
    {
      name: 'LinkedIn Jobs',
      url: 'https://www.linkedin.com/jobs/',
      description: 'Internships and entry-level jobs worldwide',
      icon: Briefcase
    },
    {
      name: 'Naukri',
      url: 'https://www.naukri.com/nlogin/login',
      description: 'Freshers & entry-level jobs in India',
      icon: Search
    }
  ]

  // Job search by role links
  const jobSearchByRole = [
    {
      platform: 'LinkedIn',
      url: `https://www.linkedin.com/jobs/search/?keywords=${encodeURIComponent(targetCareer)}`,
      icon: Briefcase
    },
    {
      platform: 'Naukri',
      url: `https://www.naukri.com/${encodeURIComponent(targetCareer.toLowerCase().replace(/\s+/g, '-'))}-jobs`,
      icon: Search
    },
    {
      platform: 'Indeed',
      url: `https://www.indeed.com/jobs?q=${encodeURIComponent(targetCareer)}`,
      icon: Globe
    },
    {
      platform: 'Glassdoor',
      url: `https://www.glassdoor.com/Job/jobs.htm?sc.keyword=${encodeURIComponent(targetCareer)}`,
      icon: Building2
    },
    {
      platform: 'AngelList',
      url: `https://angel.co/jobs/search?q=${encodeURIComponent(targetCareer)}`,
      icon: TrendingUp
    },
    {
      platform: 'GitHub Jobs',
      url: 'https://jobs.github.com',
      icon: Globe
    }
  ]

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

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        {/* Hero Banner */}
        <div className="mb-10">
          <div className="bg-gradient-to-r from-[#1E3A5F] to-[#6C3FC8] rounded-2xl p-8 text-white">
            <div className="flex items-center gap-4 mb-4">
              <Briefcase className="w-8 h-8" />
              <h2 className="text-2xl font-bold">Jobs Matched to Your Profile</h2>
            </div>
            <div className="text-4xl font-bold mb-2">
              {targetCareer}
            </div>
            <p className="text-white/80">
              Based on your analysis, you are best matched for: {targetCareer}
            </p>
          </div>
        </div>

        {/* Career Paths from Analysis */}
        {analysis?.career_paths && analysis.career_paths.length > 0 && (
          <div className="mb-10">
            <h3 className="text-xl font-bold text-foreground mb-4">Your Recommended Career Paths</h3>
            <div className="grid md:grid-cols-4 gap-4">
              {analysis.career_paths.slice(0, 4).map((path: any, i: number) => (
                <div
                  key={i}
                  className={`bg-card rounded-xl p-4 border-2 ${i === 0 ? 'border-[#6C3FC8]' : 'border-gray-200'
                    }`}
                >
                  {i === 0 && (
                    <span className="text-xs font-bold text-[#6C3FC8] mb-1 block">BEST MATCH</span>
                  )}
                  <h4 className="font-bold text-foreground">{path.name || path.career_name}</h4>
                  <p className="text-sm text-primary font-semibold">{path.match_percentage}% match</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Career Roadmap Timeline
        {analysis?.roadmap && (
          <div className="mb-10 bg-card rounded-2xl border p-6">
            <h3 className="text-xl font-bold text-foreground mb-6 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-[#6C3FC8]" />
              Your Career Roadmap
            </h3>
            <CareerRoadmap roadmap={analysis.roadmap} />
          </div>
        )} */}

        {/* Section: Live Job Matches */}
        <section className="mb-10">
          <h3 className="text-xl font-bold text-foreground mb-4 flex items-center gap-2">
            <Search className="w-5 h-5 text-[#6C3FC8]" />
            Live Job Matches
          </h3>

          {jobsLoading ? (
            <div className="flex items-center justify-center p-12 bg-card rounded-xl border">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
              <span className="ml-2 text-muted-foreground">Searching for live opportunities...</span>
            </div>
          ) : jobs.length > 0 ? (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {jobs.map((job, i) => (
                <div
                  key={i}
                  className="bg-card rounded-xl border p-6 hover:shadow-lg transition-shadow border-l-4 border-l-[#6C3FC8]"
                >
                  <div className="flex justify-between items-start mb-4">
                    <h4 className="font-bold text-foreground text-lg leading-tight">
                      {job.title}
                    </h4>
                    <span className="px-2 py-1 bg-green-50 text-green-700 text-[10px] font-bold rounded uppercase">
                      New
                    </span>
                  </div>

                  <div className="space-y-2 mb-6">
                    <div className="flex items-center text-sm text-muted-foreground">
                      <Building2 className="w-4 h-4 mr-2 text-[#1E3A5F]" />
                      {job.company}
                    </div>
                    <div className="flex items-center text-sm text-muted-foreground">
                      <Globe className="w-4 h-4 mr-2 text-[#1E3A5F]" />
                      {job.location}
                    </div>
                  </div>

                  <a
                    href={job.url || job.apply_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block"
                  >
                    <Button className="w-full bg-[#6C3FC8] hover:bg-[#6C3FC8]/90">
                      Apply Now
                      <ExternalLink className="ml-2 w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => fetchRealJobs(targetCareer)}
                      className="ml-2"
                    >
                      Refresh Jobs
                    </Button>
                  </a>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-card rounded-xl border p-8 text-center text-muted-foreground">
              No live matches found for your current profile. Try adjusting your target career path.
            </div>
          )}
        </section>

        {/* Section 1: Top Tech Companies */}
        <section className="mb-10">
          <h3 className="text-xl font-bold text-foreground mb-4 flex items-center gap-2">
            <Building2 className="w-5 h-5 text-[#6C3FC8]" />
            Top Tech Companies
          </h3>
          <div className="grid md:grid-cols-5 gap-4">
            {techCompanies.map((company, i) => (
              <a
                key={i}
                href={company.careersUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-card rounded-xl border p-6 hover:shadow-lg transition-shadow group"
              >
                <div className={`w-12 h-12 rounded-lg ${company.color} flex items-center justify-center text-white font-bold text-xl mb-4`}>
                  {company.name.charAt(0)}
                </div>
                <h4 className="font-bold text-foreground mb-2 group-hover:text-[#6C3FC8] transition-colors">
                  {company.name}
                </h4>
                <p className="text-sm text-muted-foreground mb-4">
                  {company.description}
                </p>
                <Button className="w-full bg-[#1E3A5F] hover:bg-[#1E3A5F]/90">
                  Apply Now
                  <ExternalLink className="ml-2 w-4 h-4" />
                </Button>
              </a>
            ))}
          </div>
        </section>

        {/* Section 2: Internships (India Focused) */}
        <section className="mb-10">
          <h3 className="text-xl font-bold text-foreground mb-4 flex items-center gap-2">
            <GraduationCap className="w-5 h-5 text-[#6C3FC8]" />
            Internships & Fresher Jobs (India)
          </h3>
          <div className="grid md:grid-cols-3 gap-4">
            {internshipPlatforms.map((platform, i) => (
              <a
                key={i}
                href={platform.url}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-card rounded-xl border p-6 hover:shadow-lg transition-shadow group"
              >
                <div className="w-12 h-12 rounded-lg bg-[#6C3FC8]/10 flex items-center justify-center mb-4">
                  <platform.icon className="w-6 h-6 text-[#6C3FC8]" />
                </div>
                <h4 className="font-bold text-foreground mb-2 group-hover:text-[#6C3FC8] transition-colors">
                  {platform.name}
                </h4>
                <p className="text-sm text-muted-foreground mb-4">
                  {platform.description}
                </p>
                <Button className="w-full bg-[#6C3FC8] hover:bg-[#6C3FC8]/90">
                  Search Jobs
                  <ArrowRight className="ml-2 w-4 h-4" />
                </Button>
              </a>
            ))}
          </div>
        </section>

        {/* Section 3: Job Search By Role */}
        <section className="mb-10">
          <h3 className="text-xl font-bold text-foreground mb-4 flex items-center gap-2">
            <Search className="w-5 h-5 text-[#6C3FC8]" />
            Search for {targetCareer} Jobs
          </h3>
          <div className="grid md:grid-cols-3 lg:grid-cols-6 gap-4">
            {jobSearchByRole.map((platform, i) => (
              <a
                key={i}
                href={platform.url}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-card rounded-xl border p-4 hover:shadow-lg transition-shadow group text-center"
              >
                <div className="w-10 h-10 rounded-lg bg-[#1E3A5F]/10 flex items-center justify-center mx-auto mb-3">
                  <platform.icon className="w-5 h-5 text-[#1E3A5F]" />
                </div>
                <h4 className="font-semibold text-foreground group-hover:text-[#6C3FC8] transition-colors">
                  {platform.platform}
                </h4>
                <p className="text-xs text-muted-foreground mt-1">
                  Search on {platform.platform}
                </p>
              </a>
            ))}
          </div>
        </section>


        {/* Career Roadmap Timeline */}
        {analysis?.roadmap && (
          <div className="mb-10 bg-card rounded-2xl border p-6">
            <h3 className="text-xl font-bold text-foreground mb-6 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-[#6C3FC8]" />
              Your Career Roadmap
            </h3>
            <CareerRoadmap roadmap={analysis.roadmap} />
          </div>
        )}


        {/* Profile Summary */}
        {profile && (
          <section className="mb-10">
            <h3 className="text-xl font-bold text-foreground mb-4">
              Your Profile Summary
            </h3>
            <div className="bg-card rounded-xl border p-6">
              <div className="grid md:grid-cols-3 gap-6">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">GitHub</p>
                  <p className="font-medium text-foreground">
                    {profile.github_username || 'Not connected'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">LeetCode</p>
                  <p className="font-medium text-foreground">
                    {profile.leetcode_username || 'Not connected'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Experience Level</p>
                  <p className="font-medium text-foreground">
                    {analysis?.analysis?.experience_level || analysis?.experience_level || 'Not analyzed yet'}
                  </p>
                </div>
              </div>
              <div className="mt-4 pt-4 border-t">
                <Link href="/analysis">
                  <Button variant="outline">
                    View Full Analysis
                    <ArrowRight className="ml-2 w-4 h-4" />
                  </Button>
                </Link>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}
