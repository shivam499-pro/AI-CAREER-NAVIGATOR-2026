'use client'

import { useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { AlertTriangle, RefreshCw, Mic, Home } from 'lucide-react'
import Link from 'next/link'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error('Interview error:', error)
  }, [error])

  return (
    <div className="min-h-screen bg-[#0F172A] text-white flex items-center justify-center p-4">
      <div className="max-w-md w-full text-center">
        <div className="w-20 h-20 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
          <AlertTriangle className="w-10 h-10 text-red-500" />
        </div>
        
        <h1 className="text-3xl font-black text-white mb-4">
          Interview Error
        </h1>
        
        <p className="text-slate-400 mb-8 font-medium">
          Something went wrong while setting up your interview session. 
          Please try again.
        </p>

        {error?.digest && (
          <p className="text-xs text-slate-500 mb-6 font-mono">
            Error ID: {error.digest}
          </p>
        )}
        
        <div className="flex flex-col gap-3">
          <Button
            onClick={reset}
            className="w-full bg-[#6C3FC8] hover:bg-[#6C3FC8]/90 text-white font-black uppercase tracking-widest h-12 rounded-xl"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Try Again
          </Button>
          
          <Link href="/dashboard">
            <Button
              variant="outline"
              className="w-full border-white/10 text-slate-400 hover:text-white hover:border-white/30 h-12 rounded-xl font-black uppercase tracking-widest"
            >
              <Home className="w-4 h-4 mr-2" />
              Back to Dashboard
            </Button>
          </Link>
        </div>
      </div>
    </div>
  )
}
