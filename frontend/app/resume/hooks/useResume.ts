/**
 * useResume Hook (SRP Fix)
 * All state, auth, and data loading extracted from ResumePage.
 * ResumePage becomes a pure renderer.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { resumeClient, ResumeStatus, UploadedDoc, DocumentResult } from '@/lib/api/resumeClient'

const ALLOWED_CERT_TYPES = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']
const MAX_CERT_SIZE = 5 * 1024 * 1024
const MAX_RESUME_SIZE = 10 * 1024 * 1024

export interface UseResumeReturn {
  // Auth
  user: any
  loading: boolean
  // Resume tab
  resumeStatus: ResumeStatus | null
  resumeFile: File | null
  resumeUploading: boolean
  resumeSuccess: boolean
  resumeError: string
  resumeDrag: boolean
  setResumeFile: (f: File | null) => void
  setResumeDrag: (v: boolean) => void
  setResumeSuccess: (v: boolean) => void
  handleResumeFile: (file: File) => void
  handleResumeUpload: () => Promise<void>
  // Cert tab
  certFiles: File[]
  certUploading: boolean
  certError: string
  certResult: DocumentResult | null
  certDrag: boolean
  uploadedDocs: UploadedDoc[]
  loadingDocs: boolean
  setCertDrag: (v: boolean) => void
  setCertResult: (r: DocumentResult | null) => void
  addCertFiles: (files: File[]) => void
  removeCertFile: (index: number) => void
  handleCertUpload: () => Promise<void>
  refreshDocs: () => Promise<void>
  deleteDoc: (id: string) => Promise<void>
}

export function useResume(): UseResumeReturn {
  const isMountedRef = useRef(true)
  useEffect(() => { 
    isMountedRef.current = true
    return () => { isMountedRef.current = false } }, [])

  const router = useRouter()
  const [user, setUser]                     = useState<any>(null)
  const [loading, setLoading]               = useState(true)
  // Resume
  const [resumeStatus, setResumeStatus]     = useState<ResumeStatus | null>(null)
  const [resumeFile, setResumeFile]         = useState<File | null>(null)
  const [resumeUploading, setResumeUploading] = useState(false)
  const [resumeSuccess, setResumeSuccess]   = useState(false)
  const [resumeError, setResumeError]       = useState('')
  const [resumeDrag, setResumeDrag]         = useState(false)
  // Certs
  const [certFiles, setCertFiles]           = useState<File[]>([])
  const [certUploading, setCertUploading]   = useState(false)
  const [certError, setCertError]           = useState('')
  const [certResult, setCertResult]         = useState<DocumentResult | null>(null)
  const [certDrag, setCertDrag]             = useState(false)
  const [uploadedDocs, setUploadedDocs]     = useState<UploadedDoc[]>([])
  const [loadingDocs, setLoadingDocs]       = useState(false)

  const getToken = async (): Promise<string | null> => {
    const { data: { session } } = await supabase.auth.getSession()
    return session?.access_token ?? null
  }

  const refreshDocs = useCallback(async () => {
    setLoadingDocs(true)
    const token = await getToken()
    if (token) {
      const docs = await resumeClient.getDocuments(token)
      if (isMountedRef.current) setUploadedDocs(docs)
    }
    if (isMountedRef.current) setLoadingDocs(false)
  }, [])

  useEffect(() => {
    const init = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) { router.push('/auth/login'); return }
      setUser(user)
      const token = await getToken()
      if (token) {
        const [status] = await Promise.all([
          resumeClient.getStatus(token),
          resumeClient.getDocuments(token).then(setUploadedDocs),
        ])
        if (isMountedRef.current) setResumeStatus(status)
      }
      if (isMountedRef.current) setLoading(false)
    }
    init()
  }, [router])

  const handleResumeFile = useCallback((file: File) => {
    if (file.type !== 'application/pdf') { setResumeError('Only PDF files are supported.'); return }
    if (file.size > MAX_RESUME_SIZE) { setResumeError('File must be under 10MB.'); return }
    setResumeFile(file)
    setResumeError('')
  }, [])

  const handleResumeUpload = useCallback(async () => {
    if (!resumeFile || !user) return
    setResumeUploading(true)
    setResumeError('')
    try {
      const data = await resumeClient.uploadResume(resumeFile)
      if (data.success) {
        setResumeSuccess(true)
        setResumeStatus({ has_resume: true, filename: resumeFile.name })
        setResumeFile(null)
      }
    } catch (err: any) {
      setResumeError(err.message || 'Upload failed. Please try again.')
    } finally {
      if (isMountedRef.current) setResumeUploading(false)
    }
  }, [resumeFile, user])

  const addCertFiles = useCallback((incoming: File[]) => {
    setCertError('')
    const valid: File[] = []
    for (const f of incoming) {
      if (!ALLOWED_CERT_TYPES.includes(f.type)) { setCertError(`${f.name} — unsupported format.`); continue }
      if (f.size > MAX_CERT_SIZE) { setCertError(`${f.name} exceeds 5MB.`); continue }
      valid.push(f)
    }
    setCertFiles(prev => [...prev, ...valid].slice(0, 10))
  }, [])

  const removeCertFile = useCallback((index: number) => {
    setCertFiles(prev => prev.filter((_, i) => i !== index))
  }, [])

  const handleCertUpload = useCallback(async () => {
    if (!certFiles.length || !user) return
    setCertUploading(true)
    setCertError('')
    setCertResult(null)
    try {
      const token = await getToken()
      if (!token) throw new Error('Not authenticated')
      const result = await resumeClient.uploadCertificates(token, user.id, certFiles)
      if (isMountedRef.current) {
        setCertResult(result)
        setCertFiles([])
        await refreshDocs()
      }
    } catch (err: any) {
      if (isMountedRef.current) setCertError(err.message || 'Failed to process documents.')
    } finally {
      if (isMountedRef.current) setCertUploading(false)
    }
  }, [certFiles, user, refreshDocs])

  const deleteDoc = useCallback(async (docId: string) => {
    const token = await getToken()
    if (!token) return
    await resumeClient.deleteDocument(token, docId)
    if (isMountedRef.current) setUploadedDocs(prev => prev.filter(d => d.id !== docId))
  }, [])

  return {
    user, loading,
    resumeStatus, resumeFile, resumeUploading, resumeSuccess, resumeError, resumeDrag,
    setResumeFile, setResumeDrag, setResumeSuccess, handleResumeFile, handleResumeUpload,
    certFiles, certUploading, certError, certResult, certDrag, uploadedDocs, loadingDocs,
    setCertDrag, setCertResult, addCertFiles, removeCertFile, handleCertUpload, refreshDocs, deleteDoc,
  }
}