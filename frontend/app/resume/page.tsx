'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import Navbar from '@/components/Navbar'
import { 
  Brain, Upload, FileText, Loader2, CheckCircle, 
  AlertCircle, ArrowRight, X, Sparkles
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

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
        <motion.div initial="hidden" animate="visible" variants={containerVariants} className="max-w-2xl mx-auto">
          
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
