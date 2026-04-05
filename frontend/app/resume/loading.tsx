'use client'

import { FileText, Loader2 } from 'lucide-react'

export default function Loading() {
  return (
    <div className="min-h-screen bg-[#0F172A] flex items-center justify-center">
      <div className="text-center">
        <div className="relative mb-12">
          <div className="w-32 h-32 mx-auto">
            <div className="absolute inset-0 rounded-full border-4 border-[#6C3FC8]/20" />
            <div className="absolute inset-0 rounded-full border-4 border-[#6C3FC8] border-t-transparent animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center">
              <FileText className="w-12 h-12 text-[#6C3FC8] drop-shadow-[0_0_10px_rgba(108,63,200,0.5)]" />
            </div>
          </div>
        </div>
        <h2 className="text-3xl font-black text-white mb-3 tracking-tight">
          Processing Resume
        </h2>
        <p className="text-slate-400 mb-8 font-medium">Extracting text from your PDF...</p>
        <div className="space-y-4 max-w-xs mx-auto">
          {['Validating file', 'Parsing PDF', 'Analyzing content'].map((step, i) => (
            <div key={i} className="flex items-center gap-3 text-sm font-bold text-slate-300">
              <Loader2 className={`w-5 h-5 animate-spin text-[#6C3FC8] ${i < 2 ? '' : 'opacity-30'}`} />
              <span>{step}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
