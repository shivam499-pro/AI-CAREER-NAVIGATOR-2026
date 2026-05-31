'use client'

import { motion } from 'framer-motion'
import { Brain, AlertTriangle, Sparkles, TrendingUp } from 'lucide-react'

// ─── Types ───────────────────────────────────────────────────────────────────
// ALL UNCHANGED

interface AICoachPanelProps {
    weakestPath: string | null
    aiTip: string
    readinessScore: number
    loading?: boolean
}

// ─── Skeleton shimmer — replaces the plain grey box ──────────────────────────

function SkeletonLine({ w = 'w-full', h = 'h-3' }: { w?: string; h?: string }) {
    return (
        <div className={`${w} ${h} rounded-lg bg-white/[0.04] relative overflow-hidden`}>
            <motion.div
                className="absolute inset-y-0 left-0 w-1/2 bg-gradient-to-r from-transparent via-white/[0.06] to-transparent"
                animate={{ x: ['-100%', '300%'] }}
                transition={{ duration: 1.6, repeat: Infinity, ease: 'linear' }}
            />
        </div>
    )
}

// ─── Readiness label ──────────────────────────────────────────────────────────

function readinessLabel(score: number): string {
    if (score >= 70) return 'Job ready — focus on system design depth'
    if (score >= 40) return 'Growing — structure answers using STAR method'
    return 'Foundation stage — focus on clarity and fundamentals'
}

function readinessGradient(score: number): string {
    if (score >= 70) return 'from-emerald-500 to-green-400'
    if (score >= 40) return 'from-purple-600 to-violet-400'
    return 'from-red-600 to-rose-400'
}

function readinessGlow(score: number): string {
    if (score >= 70) return '0 0 12px rgba(52,211,153,0.35)'
    if (score >= 40) return '0 0 12px rgba(139,92,246,0.35)'
    return '0 0 12px rgba(239,68,68,0.35)'
}

function readinessColor(score: number): string {
    if (score >= 70) return 'text-emerald-400'
    if (score >= 40) return 'text-purple-400'
    return 'text-red-400'
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function AICoachPanel({
    weakestPath, aiTip, readinessScore, loading = false,
}: AICoachPanelProps) {

    // ── Loading skeleton — ALL logic unchanged, design upgraded ──────────────
    if (loading) {
        return (
            <div className="rounded-2xl border border-white/[0.06] overflow-hidden
                bg-gradient-to-br from-[#131C2E] to-[#0C1525]
                shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
                <div className="flex items-center gap-2.5 px-4 py-3.5 border-b border-white/[0.05]">
                    <div className="w-7 h-7 rounded-xl bg-white/[0.04]" />
                    <SkeletonLine w="w-32" h="h-3" />
                </div>
                <div className="p-4 space-y-4">
                    <div className="space-y-2">
                        <SkeletonLine w="w-16" h="h-2" />
                        <SkeletonLine w="w-full" h="h-9" />
                    </div>
                    <div className="space-y-2">
                        <SkeletonLine w="w-14" h="h-2" />
                        <SkeletonLine w="w-full" h="h-14" />
                    </div>
                    <div className="space-y-2">
                        <SkeletonLine w="w-20" h="h-2" />
                        <SkeletonLine w="w-full" h="h-2" />
                    </div>
                </div>
            </div>
        )
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="rounded-2xl border overflow-hidden
                bg-gradient-to-br from-[#131C2E] to-[#0C1525]
                shadow-[0_0_0_1px_rgba(139,92,246,0.1),inset_0_1px_0_rgba(255,255,255,0.03)]"
            style={{ borderColor: 'rgba(139,92,246,0.12)' }}
        >
            {/* Purple top accent line */}
            <div className="h-px w-full bg-gradient-to-r from-purple-500/40 via-violet-400/20 to-transparent" />

            {/* Header */}
            <div className="flex items-center gap-2.5 px-4 pt-4 pb-3.5 border-b border-white/[0.05]">
                <div className="w-7 h-7 rounded-xl flex items-center justify-center
                    bg-gradient-to-br from-purple-500/30 to-violet-600/10
                    border border-purple-500/20
                    shadow-[0_0_10px_rgba(139,92,246,0.2)]">
                    <Brain className="w-3.5 h-3.5 text-purple-400" />
                </div>
                <h3 className="text-[11px] font-black text-white uppercase tracking-[0.14em]">
                    AI Interview Coach
                </h3>
            </div>

            <div className="p-4 space-y-4">

                {/* ── Weak Area ──────────────────────────────────────────────── */}
                <div className="space-y-2">
                    <p className="text-[9px] font-black uppercase tracking-[0.16em] text-slate-600 flex items-center gap-1.5">
                        <AlertTriangle className="w-2.5 h-2.5 text-red-500/70" />
                        Weak Area
                    </p>
                    <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl
                        bg-red-500/[0.07] border border-red-500/[0.15]
                        shadow-[inset_0_1px_0_rgba(239,68,68,0.05)]">
                        <span className="text-red-400 font-semibold text-[13px] leading-snug">
                            {weakestPath || 'Complete more sessions to identify weak areas'}
                        </span>
                    </div>
                </div>

                {/* ── AI Tip ─────────────────────────────────────────────────── */}
                <div className="space-y-2">
                    <p className="text-[9px] font-black uppercase tracking-[0.16em] text-slate-600 flex items-center gap-1.5">
                        <Sparkles className="w-2.5 h-2.5 text-purple-400" />
                        AI Tip
                    </p>
                    <div className="flex items-start gap-2.5 px-3 py-2.5 rounded-xl
                        bg-purple-500/[0.07] border border-purple-500/[0.15]
                        shadow-[inset_0_1px_0_rgba(139,92,246,0.05)]">
                        <p className="text-purple-200/80 font-medium text-[13px] leading-relaxed">
                            {aiTip}
                        </p>
                    </div>
                </div>

                {/* Divider */}
                <div className="h-px bg-white/[0.04]" />

                {/* ── Readiness Score ────────────────────────────────────────── */}
                <div className="space-y-2.5">
                    <div className="flex items-center justify-between">
                        <p className="text-[9px] font-black uppercase tracking-[0.16em] text-slate-600 flex items-center gap-1.5">
                            <TrendingUp className="w-2.5 h-2.5 text-slate-500" />
                            Readiness
                        </p>
                        <span className={`text-sm font-black tabular-nums ${readinessColor(readinessScore)}`}>
                            {readinessScore}%
                        </span>
                    </div>

                    {/* Bar track */}
                    <div className="h-1.5 w-full bg-slate-800/80 rounded-full overflow-hidden">
                        <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${readinessScore}%` }}
                            transition={{ duration: 1, ease: [0.25, 0.46, 0.45, 0.94], delay: 0.1 }}
                            className={`h-full rounded-full bg-gradient-to-r ${readinessGradient(readinessScore)}`}
                            style={{ boxShadow: readinessGlow(readinessScore) }}
                        />
                    </div>

                    <p className="text-[11px] text-slate-600 font-medium leading-snug">
                        {readinessLabel(readinessScore)}
                    </p>
                </div>

            </div>
        </motion.div>
    )
}