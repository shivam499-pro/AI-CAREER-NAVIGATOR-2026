'use client'

import { Mic, Loader2 } from 'lucide-react'

export default function Loading() {
  return (
    <div className="min-h-screen bg-[#1A1410] flex items-center justify-center">
      <div className="text-center">
        <div className="relative mb-12">
          <div className="w-32 h-32 mx-auto">
            <div className="absolute inset-0 rounded-full border-4 border-[#C2652A]/20" />
            <div className="absolute inset-0 rounded-full border-4 border-[#C2652A] border-t-transparent animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center">
              <Mic className="w-12 h-12 text-[#C2652A] drop-shadow-[0_0_10px_rgba(194,101,42,0.5)]" />
            </div>
          </div>
        </div>
        <h2 className="text-3xl font-black text-white mb-3 tracking-tight">
          Preparing Interview
        </h2>
        <p className="text-slate-400 mb-8 font-medium">Generating personalized questions...</p>
        <div className="space-y-4 max-w-xs mx-auto">
          {['Analyzing profile', 'Generating questions', 'Setting up session'].map((step, i) => (
            <div key={i} className="flex items-center gap-3 text-sm font-bold text-slate-300">
              <Loader2 className={`w-5 h-5 animate-spin text-[#C2652A] ${i < 2 ? '' : 'opacity-30'}`} />
              <span>{step}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
