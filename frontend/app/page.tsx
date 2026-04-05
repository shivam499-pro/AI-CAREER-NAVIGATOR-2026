'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import { 
  ArrowRight, 
  Github, 
  Linkedin, 
  FileText, 
  Brain, 
  Target, 
  TrendingUp, 
  Mic, 
  Briefcase, 
  Award, 
  Map,
  CheckCircle2,
  Quote
} from 'lucide-react'

export default function Home() {
  const fadeIn = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.5 }
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* NAVBAR */}
      <header className="border-b border-primary/10 bg-background/95 backdrop-blur-md sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-10 h-10 rounded-lg bg-primary-violet flex items-center justify-center">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-white tracking-tight">AI Career Navigator</span>
          </div>
          <div className="flex items-center space-x-6">
            <Link 
              href="/auth/login"
              className="text-sm font-medium text-muted-foreground hover:text-white transition-colors"
            >
              Sign In
            </Link>
            <Link 
              href="/auth/signup"
              className="bg-primary-violet text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-primary-violet/90 transition-all shadow-lg shadow-primary-violet/20"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-grow">
        {/* HERO SECTION */}
        <section className="relative pt-20 pb-24 overflow-hidden bg-[#001F5B]">
          <div className="absolute inset-0 bg-gradient-to-b from-primary-violet/10 to-transparent pointer-events-none" />
          
          <div className="container mx-auto px-4 relative z-10">
            <motion.div 
              {...fadeIn}
              className="max-w-4xl mx-auto text-center"
            >
              <div className="inline-flex items-center space-x-2 bg-primary-violet/20 border border-primary-violet/30 px-3 py-1 rounded-full mb-6">
                <div className="w-2 h-2 rounded-full bg-primary-violet animate-pulse" />
                <span className="text-xs font-bold text-primary-violet uppercase tracking-wider">
                  Powered by Google Gemini AI
                </span>
              </div>
              
              <h1 className="text-5xl md:text-6xl font-extrabold text-white mb-6 leading-tight tracking-tight">
                Your Personal AI <span className="text-primary-violet">Career Mentor</span>
              </h1>
              
              <p className="text-xl text-blue-100/80 mb-10 max-w-2xl mx-auto leading-relaxed">
                We analyze your real GitHub, LeetCode, LinkedIn, and Resume profiles to provide 
                personalized career guidance — not just self-reported data.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
                <Link 
                  href="/auth/signup"
                  className="bg-primary-violet text-white px-8 py-4 rounded-xl text-lg font-bold hover:bg-primary-violet/90 transition-all flex items-center justify-center gap-2 shadow-xl shadow-primary-violet/30"
                >
                  Start Free Analysis <ArrowRight className="w-5 h-5" />
                </Link>
                <Link 
                  href="#features"
                  className="bg-white/5 border border-white/10 text-white px-8 py-4 rounded-xl text-lg font-bold hover:bg-white/10 transition-all backdrop-blur-sm"
                >
                  Learn More
                </Link>
              </div>

              {/* Stats Row */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8 py-8 border-y border-white/10">
                <div className="flex items-center justify-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-primary-violet" />
                  <span className="text-white font-medium">100% Real Data</span>
                </div>
                <div className="flex items-center justify-center gap-3 border-x border-white/10">
                  <CheckCircle2 className="w-5 h-5 text-primary-violet" />
                  <span className="text-white font-medium">0 Mock Results</span>
                </div>
                <div className="flex items-center justify-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-primary-violet" />
                  <span className="text-white font-medium">Free to Start</span>
                </div>
              </div>
              
              <p className="mt-8 text-sm font-semibold text-blue-100 uppercase tracking-widest">
                Built for Indian CS students and fresh graduates
              </p>
            </motion.div>
          </div>
        </section>

        {/* FEATURES SECTION */}
        <section id="features" className="py-24 bg-[#001F5B] border-t border-white/5">
          <div className="container mx-auto px-4">
            <div className="text-center mb-20">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 tracking-tight">Hard Metrics, Better Careers</h2>
              <p className="text-blue-100/60 max-w-2xl mx-auto text-lg leading-relaxed mt-4">
                Unlike other career tools, we read your ACTUAL profiles to give you 
                honest, data-driven recommendations.
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              <FeatureCard 
                icon={<Github className="w-7 h-7" />}
                title="GitHub Analysis"
                description="We analyze your real repos and coding activity to understand your true technical strengths."
                delay={0.1}
              />
              <FeatureCard 
                icon={<Mic className="w-7 h-7" />}
                title="Voice Interview"
                description="Practice real-world technical and HR interviews by speaking naturally, not just typing."
                delay={0.2}
              />
              <FeatureCard 
                icon={<Map className="w-7 h-7" />}
                title="AI Career Roadmap"
                description="A personalized 24-week action plan tailored to your target goal and current skill level."
                delay={0.3}
              />
              <FeatureCard 
                icon={<Target className="w-7 h-7" />}
                title="Skill Gap Finder"
                description="See exactly what skills you are missing for specific job roles based on industry data."
                delay={0.4}
              />
              <FeatureCard 
                icon={<Briefcase className="w-7 h-7" />}
                title="Job Matching"
                description="Discover real job and internship opportunities that match your verified skill level."
                delay={0.5}
              />
              <FeatureCard 
                icon={<Award className="w-7 h-7" />}
                title="Streaks & XP"
                description="Stay consistent and motivated with daily study streaks, XP rewards, and leaderboard status."
                delay={0.6}
              />
            </div>
          </div>
        </section>

        {/* TESTIMONIALS SECTION */}
        <section className="py-24 bg-[#001F5B] border-t border-white/5">
          <div className="container mx-auto px-4">
            <h2 className="text-3xl font-bold text-white text-center mb-16 italic opacity-90">What our students say</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto">
              <motion.div 
                {...fadeIn}
                className="bg-slate-900/40 p-8 rounded-2xl border border-white/5 relative shadow-inner shadow-white/5"
              >
                <Quote className="absolute top-6 right-8 w-10 h-10 text-primary-violet opacity-20" />
                <p className="text-xl text-white font-medium mb-8 leading-relaxed">
                  "Finally a tool that reads my actual GitHub instead of asking me to fill forms. The insights are surprisingly accurate."
                </p>
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-primary-violet/20 flex items-center justify-center text-primary-violet font-bold text-lg border border-primary-violet/30">RK</div>
                  <div>
                    <h4 className="text-white font-bold">Rahul K.</h4>
                    <p className="text-blue-100/50 text-sm">CS Student</p>
                  </div>
                </div>
              </motion.div>

              <motion.div 
                {...fadeIn}
                className="bg-slate-900/40 p-8 rounded-2xl border border-white/5 relative shadow-inner shadow-white/5"
              >
                <Quote className="absolute top-6 right-8 w-10 h-10 text-primary-violet opacity-20" />
                <p className="text-xl text-white font-medium mb-8 leading-relaxed">
                  "The voice interview practice helped me crack my first placement round. It feels like talking to a real interviewer."
                </p>
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-primary-violet/20 flex items-center justify-center text-primary-violet font-bold text-lg border border-primary-violet/30">PS</div>
                  <div>
                    <h4 className="text-white font-bold">Priya S.</h4>
                    <p className="text-blue-100/50 text-sm">Final Year, NIT</p>
                  </div>
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* CTA SECTION */}
        <section className="py-24 bg-[#011640] relative overflow-hidden border-t border-white/5">
          <div className="absolute inset-0 bg-primary-violet/5 pointer-events-none" />
          <div className="container mx-auto px-4 text-center relative z-10">
            <h2 className="text-4xl font-extrabold text-white mb-6">
              Ready to discover your ideal career path?
            </h2>
            <p className="text-blue-100/70 mb-10 max-w-2xl mx-auto text-lg font-medium">
              Connect your GitHub and LeetCode. Get your personalized career analysis in minutes.
            </p>
            <Link 
              href="/auth/signup"
              className="bg-primary-violet text-white px-10 py-5 rounded-xl text-xl font-bold hover:bg-primary-violet/90 transition-all inline-flex items-center gap-3 shadow-2xl shadow-primary-violet/20"
            >
              Get Started Now <ArrowRight className="w-6 h-6" />
            </Link>
          </div>
        </section>
      </main>

      {/* FOOTER */}
      <footer className="bg-[#000d26] py-16 border-t border-white/5 text-blue-100/40">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center gap-8">
            <div className="flex items-center space-x-2">
              <div className="w-10 h-10 rounded-lg bg-primary-violet/20 flex items-center justify-center">
                <Brain className="w-6 h-6 text-primary-violet" />
              </div>
              <span className="text-white font-bold text-lg tracking-tight">AI Career Navigator</span>
            </div>
            <div className="flex items-center gap-8 text-sm font-medium">
              <Link href="#" className="hover:text-white transition-colors">Privacy Policy</Link>
              <Link href="#" className="hover:text-white transition-colors">Terms of Service</Link>
              <Link href="#" className="hover:text-white transition-colors">Support</Link>
            </div>
            <p className="text-sm">
              © 2026 AI Career Navigator. Optimized for Indian graduates.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({ icon, title, description, delay }: { icon: React.ReactNode; title: string; description: string; delay: number }) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay }}
      className="p-8 rounded-2xl border border-white/10 bg-slate-900/30 hover:bg-slate-900/50 hover:border-primary-violet/40 transition-all group shadow-2xl"
    >
      <div className="w-14 h-14 rounded-xl bg-primary-violet/20 flex items-center justify-center text-primary-violet mb-6 group-hover:scale-110 transition-transform border border-primary-violet/30">
        {icon}
      </div>
      <h3 className="text-xl font-bold text-white mb-3 tracking-tight">{title}</h3>
      <p className="text-blue-100/60 leading-relaxed font-medium text-sm">{description}</p>
    </motion.div>
  )
}
