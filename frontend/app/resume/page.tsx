'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import Navbar from '@/components/Navbar'
import { 
  Brain, Upload, FileText, Loader2, CheckCircle, 
  AlertCircle, ArrowRight, X, Sparkles, Image, 
  FilePlus2, Trash2, Award, BookOpen
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

// ─────────────────────────────────────────────
// Types for multi-document upload
// ─────────────────────────────────────────────
interface ExtractedData {
  certificates: { name: string; issuer: string; date: string; skills: string[] }[]
  skills_extracted: string[]
  grades: { subject: string; score: string }[]
  achievements: string[]
  summary: string
}

interface SkillProfile {
  name: string
  count: number
  sources: string[]
  confidence: number
}

interface UserProfile {
  skills: SkillProfile[]
}

export default function ResumePage() {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [dragActive, setDragActive] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  // ─── Multi-doc state ───
  const [docFiles, setDocFiles] = useState<File[]>([])
  const [docUploading, setDocUploading] = useState(false)
  const [docError, setDocError] = useState('')
  const [docResult, setDocResult] = useState<ExtractedData | null>(null)
  const [docFilesProcessed, setDocFilesProcessed] = useState(0)
  const [docDragActive, setDocDragActive] = useState(false)
  const docInputRef = useRef<HTMLInputElement>(null)
  
  // ─── Unified Profile state ───
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loadingProfile, setLoadingProfile] = useState(false)

  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        router.push('/auth/login')
        return
      }
      setUser(user)
      setLoading(false)
    }
    checkAuth()
  }, [router])

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const handleFile = (file: File) => {
    if (file.type !== 'application/pdf') {
      setError('Invalid format: Only PDF documents are authorized.')
      return
    }
    
    if (file.size > 5 * 1024 * 1024) {
      setError('Payload exceeded: Maximum file size is 5MB.')
      return
    }
    
    setSelectedFile(file)
    setError('')
  }

  const handleUpload = async () => {
    if (!selectedFile || !user) return
    
    setUploading(true)
    setError('')
    
    try {
      const formData = new FormData()
      formData.append('user_id', user.id)
      formData.append('file', selectedFile)
      
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/resume/upload`, {
        method: 'POST',
        body: formData,
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Upload protocol failed.')
      }
      
      const data = await response.json()
      
      if (data.success) {
        setUploadSuccess(true)
      } else {
        throw new Error('Upload verification failed.')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to establish connection for upload.')
    } finally {
      setUploading(false)
    }
  }

  const handleRemoveFile = () => {
    setSelectedFile(null)
    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }

  // ─────────────────────────────────────────────
  // Multi-document handlers
  // ─────────────────────────────────────────────
  const ALLOWED_DOC_TYPES = [
    'application/pdf',
    'image/jpeg',
    'image/jpg',
    'image/png',
  ]

  const handleDocDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDocDragActive(true)
    } else if (e.type === 'dragleave') {
      setDocDragActive(false)
    }
  }

  const handleDocDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDocDragActive(false)
    if (e.dataTransfer.files) {
      addDocFiles(Array.from(e.dataTransfer.files))
    }
  }

  const handleDocFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addDocFiles(Array.from(e.target.files))
    }
  }

  const addDocFiles = (incoming: File[]) => {
    setDocError('')
    const valid: File[] = []
    for (const f of incoming) {
      if (!ALLOWED_DOC_TYPES.includes(f.type)) {
        setDocError(`Unsupported file: ${f.name}. Only PDF, JPG, JPEG, PNG allowed.`)
        continue
      }
      if (f.size > 5 * 1024 * 1024) {
        setDocError(`File "${f.name}" exceeds 5MB limit.`)
        continue
      }
      valid.push(f)
    }
    setDocFiles(prev => {
      const combined = [...prev, ...valid]
      if (combined.length > 10) {
        setDocError('Maximum 10 files allowed.')
        return combined.slice(0, 10)
      }
      return combined
    })
  }

  const removeDocFile = (index: number) => {
    setDocFiles(prev => prev.filter((_, i) => i !== index))
  }

  const fetchProfile = async () => {
    if (!user) return
    setLoadingProfile(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${apiUrl}/api/profile/${user.id}`)
      const data = await res.json()
      if (data.success) {
        setProfile(data.profile)
      }
    } catch (err) {
      console.error('Failed to fetch profile', err)
    }
    setLoadingProfile(false)
  }

  const handleDocUpload = async () => {
    if (!docFiles.length || !user) return
    setDocUploading(true)
    setDocError('')
    setDocResult(null)
    setProfile(null)

    try {
      const formData = new FormData()
      formData.append('user_id', user.id)
      for (const f of docFiles) {
        formData.append('files', f)
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/documents/upload`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.detail || 'Document upload failed.')
      }

      const data = await response.json()
      if (data.success) {
        setDocResult(data.extracted)
        setDocFilesProcessed(data.files_processed)
        // Fetch unified profile after successful upload
        await fetchProfile()
      } else {
        throw new Error('Document analysis failed.')
      }
    } catch (err: any) {
      setDocError(err.message || 'Failed to process documents.')
    } finally {
      setDocUploading(false)
    }
  }

  const getFileIcon = (file: File) => {
    if (file.type === 'application/pdf') {
      return <FileText className="w-5 h-5 text-red-400" />
    }
    return <Image className="w-5 h-5 text-blue-400" />
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // ─────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-purple-500 mx-auto mb-4" />
          <p className="text-slate-400 font-black uppercase tracking-widest text-[10px]">Initializing Upload Protocol...</p>
        </div>
      </div>
    )
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  }

  if (uploadSuccess) {
    return (
      <div className="min-h-screen bg-[#0F172A] text-white selection:bg-purple-500/30">
        <Navbar />
        <main className="container mx-auto px-4 py-20 flex justify-center items-center">
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }} 
            animate={{ opacity: 1, scale: 1 }}
            className="w-full max-w-lg bg-[#1E293B] rounded-[2.5rem] border-2 border-green-500/50 p-12 text-center relative overflow-hidden shadow-[0_0_50px_rgba(34,197,94,0.15)] group"
          >
            <div className="absolute inset-0 bg-green-500/5 pointer-events-none group-hover:bg-green-500/10 transition-colors" />
            
            <motion.div 
               initial={{ scale: 0 }}
               animate={{ scale: 1 }}
               transition={{ type: 'spring', damping: 15 }}
               className="w-24 h-24 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-8 relative"
            >
              <div className="absolute inset-0 bg-green-500/20 blur-xl rounded-full animate-pulse" />
              <CheckCircle className="w-12 h-12 text-green-400 relative z-10" />
            </motion.div>
            
            <h2 className="text-3xl font-black text-yellow-400 uppercase tracking-tighter mb-4">Resume Uploaded!</h2>
            <p className="text-slate-400 font-bold mb-10 text-sm leading-relaxed px-4">
              Your professional history has been successfully parsed. Analysis modules will now incorporate this data.
            </p>
            
            <div className="flex flex-col gap-4">
              <Link href="/analysis">
                <Button className="w-full bg-gradient-to-r from-[#6C3FC8] to-purple-600 hover:scale-105 active:scale-95 text-white font-black uppercase tracking-widest h-14 rounded-2xl shadow-[0_10px_30px_-10px_rgba(108,63,200,0.5)] transition-all">
                  Initialize Analysis
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </Link>
              <Link href="/dashboard">
                <Button variant="outline" className="w-full border-white/5 bg-[#0F172A]/50 text-slate-400 hover:text-white hover:border-white/20 h-14 rounded-2xl font-black uppercase tracking-widest transition-all">
                  Return to Dashboard
                </Button>
              </Link>
            </div>
          </motion.div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0F172A] text-white selection:bg-purple-500/30">
      <Navbar />
      <main className="container mx-auto px-4 py-12">
        <motion.div initial="hidden" animate="visible" variants={containerVariants} className="max-w-2xl mx-auto space-y-8">
          
          {/* ═══════════════════════════════════════════
              SECTION 1: Existing Resume Upload (unchanged)
              ═══════════════════════════════════════════ */}
          <motion.div variants={itemVariants} className="bg-[#1E293B] rounded-[2.5rem] p-8 md:p-12 border border-white/5 relative overflow-hidden shadow-2xl">
            <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-purple-500/10 to-transparent pointer-events-none" />
            
            <div className="text-center mb-10 relative z-10">
              <div className="w-16 h-16 bg-purple-500/20 rounded-2xl border border-purple-500/30 flex items-center justify-center mx-auto mb-6 shadow-[0_0_20px_rgba(108,63,200,0.3)]">
                 <FileText className="w-8 h-8 text-[#6C3FC8]" />
              </div>
              <h1 className="text-3xl font-black text-yellow-400 uppercase tracking-tighter mb-2 drop-shadow-[0_0_10px_rgba(250,204,21,0.2)]">Document Induction</h1>
              <p className="text-xs font-black text-slate-500 uppercase tracking-[0.2em]">
                Provide your Resume (PDF) for deep neural analysis
              </p>
            </div>

            <div 
              className={`relative border-2 border-dashed rounded-[2rem] p-12 text-center transition-all duration-300 ${
                dragActive 
                  ? 'border-purple-400 bg-purple-500/10 scale-105' 
                  : 'border-purple-500/30 bg-[#0F172A]/50 hover:border-purple-400 hover:bg-[#0F172A]/80'
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="hidden"
                id="resume-upload"
              />
              
              <AnimatePresence mode="wait">
                {selectedFile ? (
                  <motion.div 
                    key="selected"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    className="flex flex-col items-center z-10 relative"
                  >
                    <div className="relative mb-6">
                       <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center border-2 border-green-500/50 shadow-[0_0_30px_rgba(34,197,94,0.3)]">
                         <CheckCircle className="w-10 h-10 text-green-400" />
                       </div>
                    </div>
                    <p className="font-black text-white px-4 py-2 bg-white/5 rounded-xl border border-white/10 mb-2 truncate max-w-full text-sm uppercase tracking-widest">
                      {selectedFile.name}
                    </p>
                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-6">
                      {(selectedFile.size / 1024).toFixed(1)} KB
                    </p>
                    <button
                      onClick={handleRemoveFile}
                      className="group flex items-center gap-2 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-xl transition-colors font-black text-[10px] uppercase tracking-widest"
                    >
                      <X className="w-3 h-3 group-hover:scale-110 transition-transform" />
                      Eject Payload
                    </button>
                  </motion.div>
                ) : (
                  <motion.div 
                    key="unselected"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="z-10 relative"
                  >
                    <div className="w-20 h-20 bg-purple-500/20 rounded-full flex items-center justify-center mx-auto mb-6 relative">
                      <div className="absolute inset-0 bg-purple-500/20 blur-xl rounded-full" />
                      <Upload className="w-10 h-10 text-purple-400 relative z-10" />
                    </div>
                    <p className="font-black text-slate-300 text-sm uppercase tracking-widest mb-2">
                      Drag & Drop Protocol
                    </p>
                    <p className="text-[10px] font-bold text-slate-500 mb-8 uppercase tracking-[0.2em]">
                      Hover file or click to locate
                    </p>
                    <label htmlFor="resume-upload">
                      <div 
                        className="inline-flex items-center justify-center px-8 py-4 bg-[#1E293B] border border-white/10 hover:border-purple-500/50 text-white rounded-2xl cursor-pointer font-black uppercase tracking-widest text-xs transition-all shadow-lg hover:shadow-purple-500/20 active:scale-95">
                        <Sparkles className="w-4 h-4 mr-2 text-purple-400" />
                        Select Payload
                      </div>
                    </label>
                    <div className="mt-8 px-4 py-2 bg-white/5 rounded-full inline-block border border-white/5">
                      <p className="text-[9px] font-black text-slate-500 uppercase tracking-widest">
                        Limit: 5MB | Format: PDF Only
                      </p>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <AnimatePresence>
              {error && (
                <motion.div 
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="mt-6 p-4 bg-red-500/10 border border-red-500/30 rounded-2xl flex items-center gap-3"
                >
                  <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                  <p className="text-[10px] font-black text-red-400 uppercase tracking-widest">{error}</p>
                </motion.div>
              )}
            </AnimatePresence>

            {selectedFile && (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-10 flex justify-center"
              >
                <Button 
                  onClick={handleUpload}
                  disabled={uploading}
                  className="w-full md:w-auto bg-gradient-to-r from-[#6C3FC8] to-purple-600 hover:scale-105 active:scale-95 text-white font-black uppercase tracking-widest h-14 px-10 rounded-2xl shadow-[0_10px_30px_-10px_rgba(108,63,200,0.5)] transition-all group"
                >
                  {uploading ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-3 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      Initialize Upload
                      <ArrowRight className="ml-3 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                    </>
                  )}
                </Button>
              </motion.div>
            )}

            <div className="mt-8 text-center border-t border-white/5 pt-8">
              <Link href="/analysis">
                <span className="text-[10px] font-black text-slate-500 hover:text-white uppercase tracking-[0.2em] cursor-pointer transition-colors px-4 py-2 rounded-lg hover:bg-white/5">
                  Bypass this step
                </span>
              </Link>
            </div>
          </motion.div>

          {/* ═══════════════════════════════════════════
              SECTION 2: Multi-Document Upload (NEW)
              ═══════════════════════════════════════════ */}
          <motion.div
            variants={itemVariants}
            className="bg-[#1E293B] rounded-[2.5rem] p-8 md:p-12 border border-white/5 relative overflow-hidden shadow-2xl"
          >
            {/* Decorative gradient */}
            <div className="absolute top-0 left-0 w-1/2 h-full bg-gradient-to-r from-cyan-500/5 to-transparent pointer-events-none" />
            <div className="absolute bottom-0 right-0 w-1/3 h-1/2 bg-gradient-to-tl from-purple-500/5 to-transparent pointer-events-none" />

            {/* Header */}
            <div className="text-center mb-10 relative z-10">
              <div className="w-16 h-16 bg-cyan-500/20 rounded-2xl border border-cyan-500/30 flex items-center justify-center mx-auto mb-6 shadow-[0_0_20px_rgba(6,182,212,0.3)]">
                <FilePlus2 className="w-8 h-8 text-cyan-400" />
              </div>
              <h2 className="text-2xl font-black text-yellow-400 uppercase tracking-tighter mb-2 drop-shadow-[0_0_10px_rgba(250,204,21,0.2)]">
                Upload Career Documents
              </h2>
              <p className="text-xs font-black text-slate-500 uppercase tracking-[0.15em]">
                Optional — Certificates, Marksheets, Transcripts & More
              </p>
              <p className="text-[10px] text-slate-600 mt-2 max-w-md mx-auto leading-relaxed">
                Upload multiple documents and our AI will extract certificates, skills, grades, and achievements to strengthen your career analysis.
              </p>
            </div>

            {/* Drop zone */}
            <div
              className={`relative border-2 border-dashed rounded-[2rem] p-8 text-center transition-all duration-300 ${
                docDragActive
                  ? 'border-cyan-400 bg-cyan-500/10 scale-[1.02]'
                  : 'border-cyan-500/20 bg-[#0F172A]/50 hover:border-cyan-400/50 hover:bg-[#0F172A]/80'
              }`}
              onDragEnter={handleDocDrag}
              onDragLeave={handleDocDrag}
              onDragOver={handleDocDrag}
              onDrop={handleDocDrop}
            >
              <input
                ref={docInputRef}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                multiple
                onChange={handleDocFileChange}
                className="hidden"
                id="doc-upload"
              />

              {docFiles.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="relative z-10"
                >
                  <div className="w-16 h-16 bg-cyan-500/15 rounded-full flex items-center justify-center mx-auto mb-5 relative">
                    <div className="absolute inset-0 bg-cyan-500/10 blur-xl rounded-full" />
                    <Upload className="w-8 h-8 text-cyan-400 relative z-10" />
                  </div>
                  <p className="font-black text-slate-300 text-sm uppercase tracking-widest mb-1">
                    Drop Documents Here
                  </p>
                  <p className="text-[10px] font-bold text-slate-500 mb-6 uppercase tracking-[0.2em]">
                    Or click to browse files
                  </p>
                  <label htmlFor="doc-upload">
                    <div className="inline-flex items-center justify-center px-8 py-4 bg-[#1E293B] border border-white/10 hover:border-cyan-500/50 text-white rounded-2xl cursor-pointer font-black uppercase tracking-widest text-xs transition-all shadow-lg hover:shadow-cyan-500/20 active:scale-95">
                      <FilePlus2 className="w-4 h-4 mr-2 text-cyan-400" />
                      Select Documents
                    </div>
                  </label>
                  <div className="mt-6 px-4 py-2 bg-white/5 rounded-full inline-block border border-white/5">
                    <p className="text-[9px] font-black text-slate-500 uppercase tracking-widest">
                      Max: 5MB each | 10 files | PDF, JPG, PNG
                    </p>
                  </div>
                </motion.div>
              ) : (
                /* File list */
                <div className="relative z-10 space-y-3">
                  <AnimatePresence>
                    {docFiles.map((file, idx) => (
                      <motion.div
                        key={`${file.name}-${idx}`}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 20 }}
                        transition={{ delay: idx * 0.05 }}
                        className="flex items-center gap-3 px-4 py-3 bg-[#1E293B]/80 rounded-xl border border-white/5 hover:border-white/10 transition-colors group"
                      >
                        <div className="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center bg-white/5">
                          {getFileIcon(file)}
                        </div>
                        <div className="flex-1 min-w-0 text-left">
                          <p className="text-xs font-bold text-white truncate">
                            {file.name}
                          </p>
                          <p className="text-[10px] text-slate-500 font-semibold">
                            {formatFileSize(file.size)}
                          </p>
                        </div>
                        <button
                          onClick={() => removeDocFile(idx)}
                          className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all opacity-0 group-hover:opacity-100"
                          title="Remove file"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </motion.div>
                    ))}
                  </AnimatePresence>

                  {/* Add more files */}
                  {docFiles.length < 10 && (
                    <label htmlFor="doc-upload">
                      <div className="flex items-center justify-center gap-2 px-4 py-3 border border-dashed border-white/10 hover:border-cyan-500/40 rounded-xl cursor-pointer transition-all hover:bg-white/[0.02]">
                        <FilePlus2 className="w-4 h-4 text-cyan-500/60" />
                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
                          Add More Files ({docFiles.length}/10)
                        </span>
                      </div>
                    </label>
                  )}
                </div>
              )}
            </div>

            {/* Error display */}
            <AnimatePresence>
              {docError && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="mt-6 p-4 bg-red-500/10 border border-red-500/30 rounded-2xl flex items-center gap-3"
                >
                  <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                  <p className="text-[10px] font-black text-red-400 uppercase tracking-widest">{docError}</p>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Upload button */}
            {docFiles.length > 0 && !docResult && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-8 flex justify-center"
              >
                <Button
                  onClick={handleDocUpload}
                  disabled={docUploading}
                  className="w-full md:w-auto bg-gradient-to-r from-cyan-600 via-purple-600 to-purple-700 hover:scale-105 active:scale-95 text-white font-black uppercase tracking-widest h-14 px-10 rounded-2xl shadow-[0_10px_30px_-10px_rgba(6,182,212,0.4)] transition-all group"
                >
                  {docUploading ? (
                    <span className="flex items-center gap-3">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span className="flex flex-col items-start">
                        <span className="text-xs">AI is reading your documents...</span>
                      </span>
                    </span>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5 mr-3" />
                      Upload & Analyze Documents
                      <ArrowRight className="ml-3 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                    </>
                  )}
                </Button>
              </motion.div>
            )}

            {/* Loading state overlay */}
            <AnimatePresence>
              {docUploading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="mt-6 p-6 bg-[#0F172A]/60 backdrop-blur border border-purple-500/20 rounded-2xl"
                >
                  <div className="flex flex-col items-center gap-4">
                    <div className="relative">
                      <div className="w-16 h-16 border-4 border-purple-500/20 border-t-purple-500 rounded-full animate-spin" />
                      <Brain className="w-7 h-7 text-purple-400 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-black text-white uppercase tracking-widest mb-1">
                        AI is reading your documents...
                      </p>
                      <p className="text-[10px] text-slate-500 font-bold">
                        Extracting certificates, skills, grades & achievements
                      </p>
                    </div>
                    {/* Animated dots */}
                    <div className="flex gap-1.5">
                      {[0, 1, 2, 3, 4].map(i => (
                        <motion.div
                          key={i}
                          className="w-2 h-2 rounded-full bg-purple-500"
                          animate={{ opacity: [0.2, 1, 0.2], scale: [0.8, 1.2, 0.8] }}
                          transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
                        />
                      ))}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* ── Success results ── */}
            <AnimatePresence>
              {docResult && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-8 space-y-5"
                >
                  {/* Success banner */}
                  <div className="p-5 bg-green-500/10 border border-green-500/30 rounded-2xl">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-10 h-10 bg-green-500/20 rounded-full flex items-center justify-center">
                        <CheckCircle className="w-5 h-5 text-green-400" />
                      </div>
                      <div>
                        <p className="text-sm font-black text-green-400 uppercase tracking-widest">
                          Analysis Complete
                        </p>
                        <p className="text-[10px] text-slate-500 font-bold">
                          {docFilesProcessed} document{docFilesProcessed !== 1 ? 's' : ''} processed successfully
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Stats grid */}
                  <div className="grid grid-cols-2 gap-3">
                    {/* Certificates */}
                    <div className="p-4 bg-[#0F172A]/60 rounded-2xl border border-white/5">
                      <div className="flex items-center gap-2 mb-2">
                        <Award className="w-4 h-4 text-yellow-400" />
                        <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Certificates</span>
                      </div>
                      <p className="text-2xl font-black text-white">{docResult.certificates?.length || 0}</p>
                      {docResult.certificates?.length > 0 && (
                        <div className="mt-2 space-y-1">
                          {docResult.certificates.slice(0, 3).map((cert, i) => (
                            <p key={i} className="text-[10px] text-slate-400 truncate">
                              • {cert.name}
                            </p>
                          ))}
                          {docResult.certificates.length > 3 && (
                            <p className="text-[10px] text-slate-600">+{docResult.certificates.length - 3} more</p>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Skills - Unified Profile */}
                    <div className="p-4 bg-[#0F172A]/60 rounded-2xl border border-white/5">
                      <div className="flex items-center gap-2 mb-2">
                        <Sparkles className="w-4 h-4 text-purple-400" />
                        <span className="text-[10px] font-black text-purple-400 uppercase tracking-widest">🧠 AI Skill Intelligence</span>
                      </div>
                      <p className="text-[9px] text-slate-500 mb-3">
                        AI analyzed your documents and identified your strongest skills with confidence scores.
                      </p>
                      {loadingProfile ? (
                        <p className="text-2xl font-black text-white">Analyzing...</p>
                      ) : profile && profile.skills.length > 0 ? (
                        <>
                          <p className="text-2xl font-black text-white">{profile.skills.length}</p>
                          <div className="mt-2 flex flex-wrap gap-1">
                            {profile.skills.slice(0, 5).map((skill, i) => (
                              <span key={i} className="text-[9px] font-bold px-2 py-0.5 bg-purple-500/15 text-purple-300 rounded-full border border-purple-500/20 flex items-center gap-1">
                                {skill.name} ({Math.round(skill.confidence * 100)}%)
                                <span className="text-purple-400/50 ml-1 text-[8px]">from {skill.sources.join(", ")}</span>
                              </span>
                            ))}
                            {profile.skills.length > 5 && (
                              <span className="text-[9px] font-bold px-2 py-0.5 text-slate-500">
                                +{profile.skills.length - 5}
                              </span>
                            )}
                          </div>
                        </>
                      ) : docResult.skills_extracted?.length > 0 ? (
                        <>
                          <p className="text-2xl font-black text-white">{docResult.skills_extracted?.length || 0}</p>
                          <div className="mt-2 flex flex-wrap gap-1">
                            {docResult.skills_extracted.slice(0, 4).map((skill, i) => (
                              <span key={i} className="text-[9px] font-bold px-2 py-0.5 bg-purple-500/15 text-purple-300 rounded-full border border-purple-500/20">
                                {skill}
                              </span>
                            ))}
                            {docResult.skills_extracted.length > 4 && (
                              <span className="text-[9px] font-bold px-2 py-0.5 text-slate-500">
                                +{docResult.skills_extracted.length - 4}
                              </span>
                            )}
                          </div>
                        </>
                      ) : (
                        <p className="text-2xl font-black text-white">0</p>
                      )}
                    </div>

                    {/* Grades */}
                    <div className="p-4 bg-[#0F172A]/60 rounded-2xl border border-white/5">
                      <div className="flex items-center gap-2 mb-2">
                        <BookOpen className="w-4 h-4 text-cyan-400" />
                        <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Grades</span>
                      </div>
                      <p className="text-2xl font-black text-white">{docResult.grades?.length || 0}</p>
                    </div>

                    {/* Achievements */}
                    <div className="p-4 bg-[#0F172A]/60 rounded-2xl border border-white/5">
                      <div className="flex items-center gap-2 mb-2">
                        <CheckCircle className="w-4 h-4 text-green-400" />
                        <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Achievements</span>
                      </div>
                      <p className="text-2xl font-black text-white">{docResult.achievements?.length || 0}</p>
                    </div>
                  </div>

                  {/* Summary */}
                  {docResult.summary && (
                    <div className="p-4 bg-[#0F172A]/60 rounded-2xl border border-white/5">
                      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">AI Summary</p>
                      <p className="text-sm text-slate-300 leading-relaxed">{docResult.summary}</p>
                    </div>
                  )}

                  {/* Upload more button */}
                  <div className="flex justify-center pt-2">
                    <button
                      onClick={() => { setDocResult(null); setDocFiles([]); setDocFilesProcessed(0); }}
                      className="text-[10px] font-black text-slate-500 hover:text-cyan-400 uppercase tracking-[0.2em] cursor-pointer transition-colors px-4 py-2 rounded-lg hover:bg-white/5"
                    >
                      Upload More Documents
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

        </motion.div>
      </main>

      {/* Decorative Orbs */}
      <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden opacity-30">
        <div className="absolute top-[20%] left-[-10%] w-[500px] h-[500px] bg-purple-900/20 rounded-full blur-[120px]" />
        <div className="absolute bottom-[20%] right-[-10%] w-[400px] h-[400px] bg-blue-900/20 rounded-full blur-[100px]" />
      </div>
    </div>
  )
}
