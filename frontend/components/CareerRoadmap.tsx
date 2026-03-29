'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { CheckCircle2, Circle, Flag, Target } from 'lucide-react'

interface Milestone {
  week: number
  title: string
  description: string
  skills?: string[]
  deliverable?: string
}

interface CareerRoadmapProps {
  roadmap: {
    target_career: string
    duration_months: number
    total_weeks: number
    milestones: Milestone[]
  }
}

export default function CareerRoadmap({ roadmap }: CareerRoadmapProps) {
  if (!roadmap || !roadmap.milestones) return null

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2
      }
    }
  }

  const item = {
    hidden: { opacity: 0, x: -20 },
    show: { 
      opacity: 1, 
      x: 0,
      transition: {
        type: 'spring',
        duration: 0.8,
        bounce: 0.4
      }
    }
  }

  return (
    <section className="mb-10">
      <h3 className="text-xl font-bold text-foreground mb-8 flex items-center gap-2">
        <Target className="w-5 h-5 text-[#6C3FC8]" />
        Your Career Roadmap to {roadmap.target_career}
      </h3>

      <motion.div 
        variants={container}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, margin: "-100px" }}
        className="relative ml-4 md:ml-8 border-l-2 border-[#1E3A5F]/20 pl-8 pb-4"
      >
        {roadmap.milestones.map((milestone, i) => (
          <motion.div 
            key={i} 
            variants={item}
            className="mb-10 relative"
          >
            {/* Timeline Connector Dot */}
            <div className="absolute -left-[45px] top-1.5 w-6 h-6 rounded-full bg-white border-4 border-[#1E3A5F] flex items-center justify-center">
              <div className="w-2 h-2 rounded-full bg-[#6C3FC8]" />
            </div>

            <div className="bg-card rounded-xl border p-6 shadow-sm hover:shadow-md transition-shadow group">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                <span className="text-sm font-bold text-[#6C3FC8] py-1 px-3 bg-[#6C3FC8]/10 rounded-full">
                  Week {milestone.week}
                </span>
                <div className="flex items-center text-green-600 text-sm font-medium">
                  <CheckCircle2 className="w-4 h-4 mr-1" />
                  Upcoming
                </div>
              </div>

              <h4 className="text-lg font-bold text-[#1E3A5F] mb-2">
                {milestone.title}
              </h4>
              
              <p className="text-muted-foreground text-sm mb-4 leading-relaxed">
                {milestone.description}
              </p>

              {(milestone.skills && milestone.skills.length > 0) && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {milestone.skills.map((skill, si) => (
                    <span key={si} className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                      {skill}
                    </span>
                  ))}
                </div>
              )}

              {milestone.deliverable && (
                <div className="bg-blue-50/50 p-3 rounded-lg border border-blue-100 flex items-start gap-3">
                  <Flag className="w-4 h-4 text-blue-600 mt-0.5" />
                  <div>
                    <span className="text-[10px] font-bold text-blue-600 uppercase block">Weekly Goal</span>
                    <p className="text-sm text-blue-900 font-medium">{milestone.deliverable}</p>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        ))}
        
        {/* End of Timeline Dot */}
        <div className="absolute -left-[45px] bottom-0 w-6 h-6 rounded-full bg-[#1E3A5F] flex items-center justify-center text-white border-4 border-white">
          <CheckCircle2 className="w-3 h-3" />
        </div>
      </motion.div>

      <div className="mt-8 p-6 bg-gradient-to-r from-[#1E3A5F]/5 to-[#6C3FC8]/5 rounded-2xl border border-dashed border-[#1E3A5F]/20 text-center">
        <p className="text-sm text-muted-foreground italic">
          Tip: This roadmap is adaptive and will update automatically as you connect more data sources or upload new projects.
        </p>
      </div>
    </section>
  )
}
