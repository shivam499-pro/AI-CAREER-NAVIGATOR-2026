import Link from 'next/link'
import { ArrowRight, Github, Linkedin, FileText, Brain, Target, TrendingUp } from 'lucide-react'

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-10 h-10 rounded-lg gradient-primary flex items-center justify-center">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-primary">AI Career Navigator</span>
          </div>
          <div className="flex items-center space-x-4">
            <Link 
              href="/auth/signup"
              className="text-foreground hover:text-primary transition-colors"
            >
              Sign In
            </Link>
            <Link 
              href="/auth/signup"
              className="bg-primary text-white px-5 py-2 rounded-md hover:bg-primary/90 transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="gradient-hero py-20">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto text-center">
            <h1 className="text-5xl font-bold text-primary mb-6 leading-tight">
              Your Personal AI Career Mentor
            </h1>
            <p className="text-xl text-muted-foreground mb-8">
              We analyze your real GitHub, LeetCode, LinkedIn, and Resume profiles to provide 
              personalized career guidance — not just self-reported data.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link 
                href="/auth/signup"
                className="bg-primary text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-primary/90 transition-all flex items-center justify-center gap-2"
              >
                Start Free Analysis <ArrowRight className="w-5 h-5" />
              </Link>
              <Link 
                href="#features"
                className="border border-primary text-primary px-8 py-4 rounded-lg text-lg font-semibold hover:bg-primary/5 transition-all"
              >
                Learn More
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-primary mb-4">Why AI Career Navigator?</h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Unlike other career tools, we read your ACTUAL profiles to give you 
              honest, data-driven recommendations.
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard 
              icon={<Github className="w-8 h-8" />}
              title="GitHub Analysis"
              description="We analyze your repositories, languages, activity, and project quality to understand your technical strengths."
            />
            <FeatureCard 
              icon={<FileText className="w-8 h-8" />}
              title="Resume Parser"
              description="Upload your resume and we'll extract your skills, experience, and projects automatically."
            />
            <FeatureCard 
              icon={<Target className="w-8 h-8" />}
              title="Career Matching"
              description="Get matched with career paths that align with your actual skills and experience level."
            />
            <FeatureCard 
              icon={<TrendingUp className="w-8 h-8" />}
              title="Skill Gap Analysis"
              description="Visual breakdown of skills you have vs. skills you need for your target career."
            />
            <FeatureCard 
              icon={<Brain className="w-8 h-8" />}
              title="AI-Powered Roadmap"
              description="Get a personalized, time-bound action plan to reach your career goals."
            />
            <FeatureCard 
              icon={<Linkedin className="w-8 h-8" />}
              title="Job Suggestions"
              description="See real job and internship opportunities matched to your profile."
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 gradient-primary">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold text-white mb-6">
            Ready to Discover Your Ideal Career Path?
          </h2>
          <p className="text-white/80 mb-8 max-w-2xl mx-auto">
            Join thousands of students and professionals who have found clarity in their career journey.
          </p>
          <Link 
            href="/auth/signup"
            className="bg-white text-primary px-8 py-4 rounded-lg text-lg font-semibold hover:bg-white/90 transition-all inline-flex items-center gap-2"
          >
            Get Started Now <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-foreground py-12">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center space-x-2 mb-4 md:mb-0">
              <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <span className="text-white font-semibold">AI Career Navigator</span>
            </div>
            <p className="text-white/60 text-sm">
              © 2024 AI Career Navigator. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="p-6 rounded-xl border bg-card hover:shadow-card-hover transition-shadow">
      <div className="w-14 h-14 rounded-lg bg-primary/10 flex items-center justify-center text-primary mb-4">
        {icon}
      </div>
      <h3 className="text-xl font-semibold text-foreground mb-2">{title}</h3>
      <p className="text-muted-foreground">{description}</p>
    </div>
  )
}
