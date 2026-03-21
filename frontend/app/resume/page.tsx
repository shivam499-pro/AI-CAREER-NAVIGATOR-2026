'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import { 
  Brain, Upload, FileText, Loader2, CheckCircle, 
  AlertCircle, ArrowRight, X
} from 'lucide-react'

export default function ResumePage() {
  const router = useRouter()
  const [user, setUser] = useState<{ id: string } | null>(null)
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
    // Validate file type
    if (file.type !== 'application/pdf') {
      setError('Please upload a PDF file')
      return
    }
    
    // Validate file size (5MB)
    if (file.size > 5 * 1024 * 1024) {
      setError('File size must be less than 5MB')
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
        throw new Error(errorData.detail || 'Upload failed')
      }
      
      const data = await response.json()
      
      if (data.success) {
        setUploadSuccess(true)
      } else {
        throw new Error('Upload failed')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to upload resume')
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
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  if (uploadSuccess) {
    return (
      <div className="min-h-screen bg-background">
        <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
          <div className="container mx-auto px-4 py-4 flex items-center justify-between">
            <Link href="/dashboard" className="flex items-center space-x-2">
              <div className="w-10 h-10 rounded-lg bg-[#1E3A5F] flex items-center justify-center">
                <Brain className="w-6 h-6 text-white" />
              </div>
              <span className="text-xl font-bold text-[#1E3A5F]">AI Career Navigator</span>
            </Link>
          </div>
        </header>

        <main className="container mx-auto px-4 py-16">
          <div className="max-w-md mx-auto text-center">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="w-10 h-10 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-foreground mb-2">Resume Uploaded!</h2>
            <p className="text-muted-foreground mb-6">
              Your analysis will now include data from your resume.
            </p>
            <div className="flex flex-col gap-3">
              <Link href="/analysis">
                <Button className="w-full bg-[#1E3A5F] hover:bg-[#1E3A5F]/90">
                  View Analysis
                  <ArrowRight className="ml-2 w-4 h-4" />
                </Button>
              </Link>
              <Link href="/dashboard">
                <Button variant="outline">
                  Go to Dashboard
                </Button>
              </Link>
            </div>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center space-x-2">
            <div className="w-10 h-10 rounded-lg bg-[#1E3A5F] flex items-center justify-center">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-[#1E3A5F]">AI Career Navigator</span>
          </Link>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-[#1E3A5F] mb-2">Upload Your Resume</h1>
            <p className="text-muted-foreground">
              Upload your resume in PDF format to enhance your career analysis
            </p>
          </div>

          <div 
            className={`border-2 border-dashed rounded-2xl p-12 text-center transition-colors ${
              dragActive 
                ? 'border-[#6C3FC8] bg-[#6C3FC8]/5' 
                : 'border-gray-300 hover:border-[#6C3FC8]'
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
            
            {selectedFile ? (
              <div className="flex flex-col items-center">
                <div className="w-16 h-16 bg-[#6C3FC8]/10 rounded-full flex items-center justify-center mb-4">
                  <FileText className="w-8 h-8 text-[#6C3FC8]" />
                </div>
                <p className="font-medium text-foreground mb-1">{selectedFile.name}</p>
                <p className="text-sm text-muted-foreground mb-4">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </p>
                <button
                  onClick={handleRemoveFile}
                  className="text-red-500 hover:text-red-700 flex items-center gap-1"
                >
                  <X className="w-4 h-4" />
                  Remove
                </button>
              </div>
            ) : (
              <>
                <div className="w-16 h-16 bg-[#1E3A5F]/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Upload className="w-8 h-8 text-[#1E3A5F]" />
                </div>
                <p className="font-medium text-foreground mb-2">
                  Drag and drop your PDF here
                </p>
                <p className="text-sm text-muted-foreground mb-4">
                  or click to browse
                </p>
                <label htmlFor="resume-upload">
                  <Button 
                    className="bg-[#1E3A5F] hover:bg-[#1E3A5F]/90 cursor-pointer">
                    Select PDF
                  </Button>
                </label>
                <p className="text-xs text-muted-foreground mt-4">
                  Maximum file size: 5MB
                </p>
              </>
            )}
          </div>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-500" />
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {selectedFile && (
            <div className="mt-6 flex justify-center">
              <Button 
                onClick={handleUpload}
                disabled={uploading}
                className="bg-[#6C3FC8] hover:bg-[#6C3FC8]/90 px-8"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    Upload Resume
                    <ArrowRight className="ml-2 w-4 h-4" />
                  </>
                )}
              </Button>
            </div>
          )}

          <div className="mt-8 text-center">
            <Link href="/analysis">
              <Button variant="ghost">
                Skip for now
              </Button>
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
