'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import Navbar from '@/components/Navbar'
import {
  Upload, FileText, Loader2, CheckCircle,
  AlertCircle, ArrowRight, X, Sparkles,
  Trash2, Award, Star, TrendingUp,
  RefreshCw, Eye, Plus
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Certificate {
  name: string
  issuer: string
  date: string
  score?: string
  skills: string[]
  weight: number        // 0-10 credibility score
  credibility: 'high' | 'medium' | 'low'
  type: 'cloud' | 'academic' | 'hackathon' | 'course' | 'competition' | 'other'
}

interface DocumentResult {
  certificates: Certificate[]
  skills_extracted: string[]
  achievements: string[]
  summary: string
  impact_score: number  // how much this improves profile
}

interface ResumeStatus {
  has_resume: boolean
  filename?: string
  resume_url?: string
}

interface UploadedDoc {
  id: string
  document_name: string
  document_type: string
  extracted_data: any
  created_at: string
}

// ─── Certificate type config ──────────────────────────────────────────────────

const CERT_TYPE_CONFIG = {
  cloud: { emoji: '☁️', color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/20' },
  academic: { emoji: '🎓', color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' },
  hackathon: { emoji: '🏆', color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/20' },
  course: { emoji: '📚', color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/20' },
  competition: { emoji: '🥇', color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/20' },
  other: { emoji: '📄', color: 'text-slate-400', bg: 'bg-slate-500/10 border-slate-500/20' },
}

const CREDIBILITY_CONFIG = {
  high: { label: 'Industry Recognised', color: 'text-green-400', dot: 'bg-green-400' },
  medium: { label: 'Verified Course', color: 'text-yellow-400', dot: 'bg-yellow-400' },
  low: { label: 'Participation', color: 'text-slate-400', dot: 'bg-slate-400' },
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function ResumePage() {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'resume' | 'certificates'>('resume')

  // Resume state
  const [resumeStatus, setResumeStatus] = useState<ResumeStatus | null>(null)
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [resumeUploading, setResumeUploading] = useState(false)
  const [resumeSuccess, setResumeSuccess] = useState(false)
  const [resumeError, setResumeError] = useState('')
  const [resumeDrag, setResumeDrag] = useState(false)
  const resumeInputRef = useRef<HTMLInputElement>(null)

  // Certificate state
  const [certFiles, setCertFiles] = useState<File[]>([])
  const [certUploading, setCertUploading] = useState(false)
  const [certError, setCertError] = useState('')
  const [certResult, setCertResult] = useState<DocumentResult | null>(null)
  const [certDrag, setCertDrag] = useState(false)
  const [uploadedDocs, setUploadedDocs] = useState<UploadedDoc[]>([])
  const [loadingDocs, setLoadingDocs] = useState(false)
  const certInputRef = useRef<HTMLInputElement>(null)

  const ALLOWED_CERT_TYPES = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']

  // ── Auth + init ─────────────────────────────────────────────────────────────

  useEffect(() => {
    const init = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) { router.push('/auth/login'); return }
      setUser(user)
      await Promise.all([fetchResumeStatus(user.id), fetchUploadedDocs(user.id)])
      setLoading(false)
    }
    init()
  }, [router])

  const getHeaders = async () => {
    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token
      ? { Authorization: `Bearer ${session.access_token}` }
      : {}
  }

  const fetchResumeStatus = async (userId: string) => {
    try {
      const headers = await getHeaders()
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${apiUrl}/api/v1/resume/status/${userId}`, { headers })
      if (res.ok) setResumeStatus(await res.json())
    } catch { /* keep null */ }
  }

  const fetchUploadedDocs = async (userId: string) => {
    setLoadingDocs(true)
    try {
      const headers = await getHeaders()
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${apiUrl}/api/v1/documents/list`, { headers })
      if (res.ok) {
        const data = await res.json()
        // Filter out resumes — show only certificates/documents
        const docs = (data.documents || []).filter((d: UploadedDoc) => d.document_type !== 'resume')
        setUploadedDocs(docs)
      }
    } catch { /* keep empty */ }
    setLoadingDocs(false)
  }

  // ── Resume handlers ──────────────────────────────────────────────────────────

  const handleResumeFile = (file: File) => {
    if (file.type !== 'application/pdf') { setResumeError('Only PDF files are supported.'); return }
    if (file.size > 10 * 1024 * 1024) { setResumeError('File must be under 10MB.'); return }
    setResumeFile(file)
    setResumeError('')
  }

  const handleResumeUpload = async () => {
    if (!resumeFile || !user) return
    setResumeUploading(true)
    setResumeError('')
    try {
      const formData = new FormData()
      formData.append('user_id', user.id)
      formData.append('file', resumeFile)

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${apiUrl}/api/v1/resume/upload`, { method: 'POST', body: formData })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Upload failed.')
      }

      const data = await res.json()
      if (data.success) {
        setResumeSuccess(true)
        setResumeStatus({ has_resume: true, filename: resumeFile.name })
        setResumeFile(null)
      }
    } catch (err: any) {
      setResumeError(err.message || 'Upload failed. Please try again.')
    }
    setResumeUploading(false)
  }

  // ── Certificate handlers ─────────────────────────────────────────────────────

  const addCertFiles = (incoming: File[]) => {
    setCertError('')
    const valid: File[] = []
    for (const f of incoming) {
      if (!ALLOWED_CERT_TYPES.includes(f.type)) { setCertError(`${f.name} — unsupported format.`); continue }
      if (f.size > 5 * 1024 * 1024) { setCertError(`${f.name} exceeds 5MB.`); continue }
      valid.push(f)
    }
    setCertFiles(prev => [...prev, ...valid].slice(0, 10))
  }

  const handleCertUpload = async () => {
    if (!certFiles.length || !user) return
    setCertUploading(true)
    setCertError('')
    setCertResult(null)

    try {
      const headers = await getHeaders()
      const formData = new FormData()
      formData.append('user_id', user.id)
      certFiles.forEach(f => formData.append('files', f))

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${apiUrl}/api/v1/documents/upload-files`, {
        method: 'POST',
        headers,   // auth header only — no Content-Type (browser sets multipart boundary)
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Analysis failed.')
      }

      const data = await res.json()
      if (data.success) {
        setCertResult(data.extracted)
        setCertFiles([])
        await fetchUploadedDocs(user.id)
      }
    } catch (err: any) {
      setCertError(err.message || 'Failed to process documents.')
    }
    setCertUploading(false)
  }

  const deleteDoc = async (docId: string) => {
    try {
      const headers = await getHeaders()
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      await fetch(`${apiUrl}/api/v1/documents/${docId}`, { method: 'DELETE', headers })
      setUploadedDocs(prev => prev.filter(d => d.id !== docId))
    } catch { /* silent */ }
  }

  // ── Helpers ──────────────────────────────────────────────────────────────────

  const formatSize = (bytes: number) =>
    bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(0)} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`

  const fadeUp = { hidden: { opacity: 0, y: 16 }, visible: { opacity: 1, y: 0 } }

  // ── Loading ──────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex items-center justify-center">
        <Loader2 className="w-10 h-10 animate-spin text-purple-500" />
      </div>
    )
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-[#0F172A] text-white">
      <Navbar />

      <main className="max-w-3xl mx-auto px-4 py-10 space-y-8">

        {/* ── Page header ───────────────────────────────────────────────────── */}
        <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-black text-white tracking-tight mb-1">
            Documents & Certificates
          </h1>
          <p className="text-slate-400 text-sm font-medium">
            Upload your resume and certificates — our AI reads them and adds verified skills to your profile.
          </p>
        </motion.div>

        {/* ── Tabs ──────────────────────────────────────────────────────────── */}
        <div className="flex gap-1 p-1 bg-[#1E293B] rounded-2xl border border-white/5 w-fit">
          {(['resume', 'certificates'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-6 py-2.5 rounded-xl text-sm font-black uppercase tracking-widest transition-all ${activeTab === tab
                ? 'bg-purple-600 text-white shadow-lg'
                : 'text-slate-500 hover:text-slate-300'
                }`}
            >
              {tab === 'resume' ? '📄 Resume' : '🏆 Certificates'}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">

          {/* ══════════════════════════════════════════
              RESUME TAB
              ══════════════════════════════════════════ */}
          {activeTab === 'resume' && (
            <motion.div
              key="resume"
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 12 }}
              className="space-y-6"
            >

              {/* Current resume status */}
              {resumeStatus?.has_resume && (
                <motion.div variants={fadeUp} initial="hidden" animate="visible"
                  className="flex items-center gap-4 p-5 bg-green-500/10 border border-green-500/20 rounded-2xl"
                >
                  <div className="w-10 h-10 rounded-xl bg-green-500/20 flex items-center justify-center flex-shrink-0">
                    <CheckCircle className="w-5 h-5 text-green-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-black text-white">Resume uploaded</p>
                    <p className="text-xs text-green-400/70 font-medium truncate mt-0.5">
                      {resumeStatus.filename || 'resume.pdf'}
                    </p>
                  </div>
                  <Link href="/analysis">
                    <button className="text-xs font-black text-green-400 hover:text-green-300 transition-colors flex items-center gap-1 flex-shrink-0">
                      View analysis <ArrowRight className="w-3 h-3" />
                    </button>
                  </Link>
                </motion.div>
              )}

              {/* Upload success */}
              <AnimatePresence>
                {resumeSuccess && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="p-6 bg-[#1E293B] border border-green-500/30 rounded-2xl text-center"
                  >
                    <div className="w-14 h-14 bg-green-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                      <CheckCircle className="w-7 h-7 text-green-400" />
                    </div>
                    <h3 className="text-lg font-black text-white mb-2">Resume uploaded successfully</h3>
                    <p className="text-sm text-slate-400 mb-5">
                      Your resume has been parsed. Run a new analysis to see updated scores.
                    </p>
                    <div className="flex gap-3 justify-center">
                      <Link href="/analysis">
                        <Button className="bg-purple-600 hover:bg-purple-700 text-white font-black text-sm px-6 py-2.5 rounded-xl">
                          Run Analysis <ArrowRight className="w-4 h-4 ml-2" />
                        </Button>
                      </Link>
                      <button
                        onClick={() => setResumeSuccess(false)}
                        className="text-sm font-bold text-slate-400 hover:text-white px-4 py-2.5 rounded-xl border border-white/10 hover:border-white/20 transition-all"
                      >
                        Upload another
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Upload area */}
              {!resumeSuccess && (
                <div className="bg-[#1E293B] rounded-3xl border border-white/5 overflow-hidden">
                  <div className="p-6 border-b border-white/5">
                    <h2 className="text-base font-black text-white">
                      {resumeStatus?.has_resume ? 'Replace Resume' : 'Upload Resume'}
                    </h2>
                    <p className="text-xs text-slate-400 font-medium mt-1">
                      PDF only · Max 10MB · Your resume text is used to improve skill matching
                    </p>
                  </div>

                  <div className="p-6">
                    <div
                      onDragEnter={e => { e.preventDefault(); setResumeDrag(true) }}
                      onDragLeave={e => { e.preventDefault(); setResumeDrag(false) }}
                      onDragOver={e => e.preventDefault()}
                      onDrop={e => { e.preventDefault(); setResumeDrag(false); if (e.dataTransfer.files[0]) handleResumeFile(e.dataTransfer.files[0]) }}
                      onClick={() => !resumeFile && resumeInputRef.current?.click()}
                      className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all cursor-pointer ${resumeDrag
                        ? 'border-purple-400 bg-purple-500/10'
                        : resumeFile
                          ? 'border-green-500/40 bg-green-500/5 cursor-default'
                          : 'border-white/10 hover:border-purple-500/40 hover:bg-purple-500/5'
                        }`}
                    >
                      <input
                        ref={resumeInputRef}
                        type="file"
                        accept=".pdf"
                        onChange={e => e.target.files?.[0] && handleResumeFile(e.target.files[0])}
                        className="hidden"
                      />

                      {resumeFile ? (
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 rounded-xl bg-green-500/20 border border-green-500/30 flex items-center justify-center flex-shrink-0">
                            <FileText className="w-6 h-6 text-green-400" />
                          </div>
                          <div className="flex-1 text-left min-w-0">
                            <p className="text-sm font-black text-white truncate">{resumeFile.name}</p>
                            <p className="text-xs text-slate-400 mt-0.5">{formatSize(resumeFile.size)}</p>
                          </div>
                          <button
                            onClick={e => { e.stopPropagation(); setResumeFile(null) }}
                            className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <>
                          <div className="w-12 h-12 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center mx-auto mb-4">
                            <Upload className="w-6 h-6 text-purple-400" />
                          </div>
                          <p className="text-sm font-bold text-white mb-1">
                            Drop your resume here or click to browse
                          </p>
                          <p className="text-xs text-slate-500">PDF files only, up to 10MB</p>
                        </>
                      )}
                    </div>

                    {/* Error */}
                    <AnimatePresence>
                      {resumeError && (
                        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                          className="mt-4 flex items-center gap-3 p-3 bg-red-500/10 border border-red-500/20 rounded-xl"
                        >
                          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                          <p className="text-xs font-bold text-red-400">{resumeError}</p>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {/* Upload button */}
                    {resumeFile && (
                      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-5">
                        <Button
                          onClick={handleResumeUpload}
                          disabled={resumeUploading}
                          className="w-full bg-purple-600 hover:bg-purple-700 text-white font-black h-12 rounded-2xl transition-all disabled:opacity-50"
                        >
                          {resumeUploading
                            ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Uploading...</>
                            : <><Upload className="w-4 h-4 mr-2" /> Upload Resume</>
                          }
                        </Button>
                      </motion.div>
                    )}
                  </div>
                </div>
              )}

              {/* Why upload */}
              <div className="grid grid-cols-3 gap-3">
                {[
                  { icon: '📊', title: 'Resume Score', desc: 'Raises resume quality from 0 to a real score' },
                  { icon: '🎯', title: 'Better Matches', desc: 'More accurate job recommendations' },
                  { icon: '🔍', title: 'Skill Detection', desc: 'Automatically extracts your skills' },
                ].map((item, i) => (
                  <div key={i} className="bg-[#1E293B] rounded-2xl p-4 border border-white/5 text-center">
                    <div className="text-2xl mb-2">{item.icon}</div>
                    <p className="text-xs font-black text-white mb-1">{item.title}</p>
                    <p className="text-[10px] text-slate-500 font-medium leading-snug">{item.desc}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* ══════════════════════════════════════════
              CERTIFICATES TAB
              ══════════════════════════════════════════ */}
          {activeTab === 'certificates' && (
            <motion.div
              key="certificates"
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -12 }}
              className="space-y-6"
            >

              {/* What to upload */}
              <div className="p-5 bg-[#1E293B] rounded-2xl border border-white/5">
                <p className="text-sm font-black text-white mb-3">What you can upload</p>
                <div className="flex flex-wrap gap-2">
                  {[
                    { emoji: '☁️', label: 'AWS / Azure / GCP' },
                    { emoji: '🎓', label: 'NPTEL certificates' },
                    { emoji: '🏆', label: 'Hackathon wins' },
                    { emoji: '📚', label: 'Coursera / Udemy' },
                    { emoji: '🥇', label: 'Competition awards' },
                    { emoji: '📄', label: 'Any PDF or image' },
                  ].map((item, i) => (
                    <span key={i} className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0F172A] rounded-full text-xs font-bold text-slate-300 border border-white/5">
                      {item.emoji} {item.label}
                    </span>
                  ))}
                </div>
              </div>

              {/* Upload area */}
              <div className="bg-[#1E293B] rounded-3xl border border-white/5 overflow-hidden">
                <div className="p-6 border-b border-white/5">
                  <h2 className="text-base font-black text-white">Upload certificates</h2>
                  <p className="text-xs text-slate-400 font-medium mt-1">
                    PDF, JPG or PNG · Max 5MB each · Up to 10 files
                  </p>
                </div>

                <div className="p-6 space-y-4">
                  {/* Drop zone */}
                  <div
                    onDragEnter={e => { e.preventDefault(); setCertDrag(true) }}
                    onDragLeave={e => { e.preventDefault(); setCertDrag(false) }}
                    onDragOver={e => e.preventDefault()}
                    onDrop={e => { e.preventDefault(); setCertDrag(false); addCertFiles(Array.from(e.dataTransfer.files)) }}
                    onClick={() => certInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${certDrag
                      ? 'border-yellow-400 bg-yellow-500/10'
                      : 'border-white/10 hover:border-yellow-500/40 hover:bg-yellow-500/5'
                      }`}
                  >
                    <input
                      ref={certInputRef}
                      type="file"
                      accept=".pdf,.jpg,.jpeg,.png"
                      multiple
                      onChange={e => e.target.files && addCertFiles(Array.from(e.target.files))}
                      className="hidden"
                    />
                    <div className="w-10 h-10 rounded-xl bg-yellow-500/10 border border-yellow-500/20 flex items-center justify-center mx-auto mb-3">
                      <Plus className="w-5 h-5 text-yellow-400" />
                    </div>
                    <p className="text-sm font-bold text-white mb-1">Add certificates</p>
                    <p className="text-xs text-slate-500">Drop files or click to browse</p>
                  </div>

                  {/* File list */}
                  <AnimatePresence>
                    {certFiles.map((file, idx) => (
                      <motion.div
                        key={`${file.name}-${idx}`}
                        initial={{ opacity: 0, x: -12 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 12 }}
                        className="flex items-center gap-3 p-3 bg-[#0F172A] rounded-xl border border-white/5 group"
                      >
                        <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center flex-shrink-0">
                          <span className="text-sm">{file.type === 'application/pdf' ? '📄' : '🖼️'}</span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-bold text-white truncate">{file.name}</p>
                          <p className="text-[10px] text-slate-500">{formatSize(file.size)}</p>
                        </div>
                        <button
                          onClick={() => setCertFiles(prev => prev.filter((_, i) => i !== idx))}
                          className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition-all opacity-0 group-hover:opacity-100"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </motion.div>
                    ))}
                  </AnimatePresence>

                  {/* Error */}
                  <AnimatePresence>
                    {certError && (
                      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="flex items-center gap-3 p-3 bg-red-500/10 border border-red-500/20 rounded-xl"
                      >
                        <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                        <p className="text-xs font-bold text-red-400">{certError}</p>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Upload button */}
                  {certFiles.length > 0 && (
                    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                      <Button
                        onClick={handleCertUpload}
                        disabled={certUploading}
                        className="w-full bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600 text-white font-black h-12 rounded-2xl transition-all disabled:opacity-50"
                      >
                        {certUploading ? (
                          <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> AI is reading your certificates...</>
                        ) : (
                          <><Sparkles className="w-4 h-4 mr-2" /> Analyse {certFiles.length} certificate{certFiles.length > 1 ? 's' : ''}</>
                        )}
                      </Button>
                    </motion.div>
                  )}
                </div>
              </div>

              {/* Analysis result */}
              <AnimatePresence>
                {certResult && (
                  <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">

                    {/* Impact banner */}
                    {certResult.impact_score > 0 && (
                      <div className="flex items-center gap-4 p-5 bg-green-500/10 border border-green-500/20 rounded-2xl">
                        <div className="w-10 h-10 rounded-xl bg-green-500/20 flex items-center justify-center flex-shrink-0">
                          <TrendingUp className="w-5 h-5 text-green-400" />
                        </div>
                        <div>
                          <p className="text-sm font-black text-white">Profile score improved</p>
                          <p className="text-xs text-green-400/80 font-medium mt-0.5">
                            These certificates added +{certResult.impact_score} points to your profile
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Certificate cards */}
                    {certResult.certificates?.length > 0 && (
                      <div className="space-y-3">
                        <p className="text-xs font-black text-slate-400 uppercase tracking-widest">
                          Certificates found — {certResult.certificates.length}
                        </p>
                        {certResult.certificates.map((cert, i) => {
                          const typeConfig = CERT_TYPE_CONFIG[cert.type] || CERT_TYPE_CONFIG.other
                          const credConfig = CREDIBILITY_CONFIG[cert.credibility] || CREDIBILITY_CONFIG.low
                          return (
                            <motion.div
                              key={i}
                              initial={{ opacity: 0, y: 8 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ delay: i * 0.08 }}
                              className="bg-[#1E293B] rounded-2xl p-5 border border-white/5"
                            >
                              <div className="flex items-start gap-4">
                                <div className={`w-12 h-12 rounded-xl border flex items-center justify-center text-2xl flex-shrink-0 ${typeConfig.bg}`}>
                                  {typeConfig.emoji}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-start justify-between gap-2 mb-1">
                                    <p className="text-sm font-black text-white leading-snug">{cert.name}</p>
                                    <div className="flex items-center gap-1.5 flex-shrink-0">
                                      <div className={`w-1.5 h-1.5 rounded-full ${credConfig.dot}`} />
                                      <span className={`text-[10px] font-black ${credConfig.color}`}>
                                        {credConfig.label}
                                      </span>
                                    </div>
                                  </div>
                                  <p className="text-xs text-slate-400 font-medium mb-3">
                                    {cert.issuer} {cert.date && `· ${cert.date}`} {cert.score && `· ${cert.score}`}
                                  </p>
                                  {cert.skills?.length > 0 && (
                                    <div className="flex flex-wrap gap-1.5">
                                      <span className="text-[10px] text-slate-500 font-bold mr-1">Skills unlocked:</span>
                                      {cert.skills.map((skill, si) => (
                                        <span key={si} className="text-[10px] font-bold px-2 py-0.5 bg-purple-500/10 text-purple-300 rounded-full border border-purple-500/20">
                                          {skill}
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                                {/* Weight bar */}
                                <div className="flex flex-col items-center gap-1 flex-shrink-0">
                                  <span className={`text-base font-black ${cert.weight >= 7 ? 'text-green-400' : cert.weight >= 5 ? 'text-yellow-400' : 'text-slate-400'}`}>
                                    {cert.weight}/10
                                  </span>
                                  <span className="text-[9px] text-slate-600 font-bold">value</span>
                                </div>
                              </div>
                            </motion.div>
                          )
                        })}
                      </div>
                    )}

                    {/* Skills summary */}
                    {certResult.skills_extracted?.length > 0 && (
                      <div className="p-5 bg-[#1E293B] rounded-2xl border border-white/5">
                        <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-3">
                          Skills added to your profile
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {certResult.skills_extracted.map((skill, i) => (
                            <span key={i} className="text-xs font-bold px-3 py-1 bg-purple-500/10 text-purple-300 rounded-full border border-purple-500/20">
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="flex gap-3">
                      <button
                        onClick={() => setCertResult(null)}
                        className="flex-1 text-sm font-bold text-slate-400 hover:text-white py-3 rounded-xl border border-white/10 hover:border-white/20 transition-all"
                      >
                        Upload more
                      </button>
                      <Link href="/analysis" className="flex-1">
                        <Button className="w-full bg-purple-600 hover:bg-purple-700 text-white font-black text-sm h-12 rounded-xl">
                          Re-run Analysis <ArrowRight className="w-4 h-4 ml-2" />
                        </Button>
                      </Link>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Previously uploaded documents */}
              {uploadedDocs.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-black text-slate-400 uppercase tracking-widest">
                      Previously uploaded — {uploadedDocs.length}
                    </p>
                    <button
                      onClick={() => fetchUploadedDocs(user.id)}
                      className="text-[10px] text-slate-500 hover:text-white transition-colors flex items-center gap-1"
                    >
                      <RefreshCw className="w-3 h-3" /> Refresh
                    </button>
                  </div>
                  {uploadedDocs.map((doc) => {
                    const certs = doc.extracted_data?.certificates || []
                    const skills = doc.extracted_data?.skills_extracted || []
                    return (
                      <div key={doc.id} className="flex items-center gap-3 p-4 bg-[#1E293B] rounded-2xl border border-white/5 group">
                        <div className="w-9 h-9 rounded-xl bg-white/5 flex items-center justify-center flex-shrink-0 text-base">
                          {doc.document_name?.match(/\.(jpg|jpeg|png)$/i) ? '🖼️' : '📄'}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-bold text-white truncate">{doc.document_name}</p>
                          <p className="text-[10px] text-slate-500 mt-0.5">
                            {certs.length > 0 ? `${certs.length} cert${certs.length > 1 ? 's' : ''}` : ''}
                            {certs.length > 0 && skills.length > 0 ? ' · ' : ''}
                            {skills.length > 0 ? `${skills.length} skills` : ''}
                            {certs.length === 0 && skills.length === 0 ? 'Processed' : ''}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => deleteDoc(doc.id)}
                            className="w-7 h-7 rounded-lg flex items-center justify-center text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition-all"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Empty state */}
              {!loadingDocs && uploadedDocs.length === 0 && !certResult && certFiles.length === 0 && (
                <div className="text-center py-12 bg-[#1E293B] rounded-2xl border border-white/5">
                  <div className="text-4xl mb-4">🏆</div>
                  <p className="text-sm font-black text-white mb-1">No certificates yet</p>
                  <p className="text-xs text-slate-400 max-w-xs mx-auto">
                    Upload your certificates above and our AI will verify the skills they prove.
                  </p>
                </div>
              )}

            </motion.div>
          )}

        </AnimatePresence>
      </main>
    </div>
  )
}