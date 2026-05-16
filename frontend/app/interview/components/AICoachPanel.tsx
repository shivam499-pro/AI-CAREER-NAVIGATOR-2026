'use client'

import { motion } from 'framer-motion'
import { Brain, AlertTriangle, Sparkles } from 'lucide-react'

// ─── Types ────────────────────────────────────────────────────────────────────

interface AICoachPanelProps {
    weakestPath: string | null
    aiTip: string
    readinessScore: number
    loading?: boolean
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function AICoachPanel({
    weakestPath,
    aiTip,
    readinessScore,
    loading = false,
}: AICoachPanelProps) {

    if (loading) {
        return (
            <div className="bg-slate-800/50 border border-white/5 rounded-2xl p-4 text-center">
                <p className="text-slate-500 text-sm">Loading coach data...</p>
            </div>
        )
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 border border-purple-500/20 rounded-2xl p-4 space-y-4"
        >
            {/* Title */}
            <div className="flex items-center gap-2 border-b border-white/5 pb-3">
                <Brain className="w-5 h-5 text-purple-500" />
                <h3 className="font-black text-white tracking-wide text-sm">AI Interview Coach</h3>
            </div>

            {/* Weak Area */}
            <div className="space-y-1.5">
                <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">
                    Weak Area
                </p>
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 flex items-center gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
                    <span className="text-red-400 font-bold text-sm">
                        {weakestPath || 'Complete more sessions to identify weak areas'}
                    </span>
                </div>
            </div>

            {/* AI Tip */}
            <div className="space-y-1.5">
                <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">
                    AI Tip
                </p>
                <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg px-3 py-2 flex items-start gap-2">
                    <Sparkles className="w-3.5 h-3.5 text-purple-400 flex-shrink-0 mt-0.5" />
                    <span className="text-purple-300 font-medium text-sm leading-snug">{aiTip}</span>
                </div>
            </div>

            {/* Readiness Score */}
            <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">
                        Readiness
                    </p>
                    <span className="text-white font-black text-sm">{readinessScore}%</span>
                </div>
                <div className="h-2 w-full bg-slate-700 rounded-full overflow-hidden">
                    <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${readinessScore}%` }}
                        transition={{ duration: 0.8, ease: 'easeOut' }}
                        className={`h-full rounded-full ${readinessScore >= 70 ? 'bg-green-400' :
                            readinessScore >= 40 ? 'bg-gradient-to-r from-purple-600 to-violet-400' :
                                'bg-red-400'
                            }`}
                    />
                </div>
                <p className="text-[10px] text-slate-500 font-medium">
                    {readinessScore >= 70
                        ? 'Job ready — focus on system design depth'
                        : readinessScore >= 40
                            ? 'Growing — structure answers using STAR method'
                            : 'Foundation stage — focus on clarity and fundamentals'}
                </p>
            </div>
        </motion.div>
    )
}