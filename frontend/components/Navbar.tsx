'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter, usePathname } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import {
  Menu, X, LayoutDashboard, Brain, Mic, User,
  FileText, Briefcase, LogOut, TrendingUp, Trophy
} from 'lucide-react'

const navLinks = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/analysis', label: 'Analysis', icon: Brain },
  { href: '/interview', label: 'Interview', icon: Mic },
  { href: '/challenges', label: 'Challenges', icon: Trophy },
  { href: '/progress', label: 'Progress', icon: TrendingUp },
  { href: '/profile', label: 'Profile', icon: User },
  { href: '/resume', label: 'Resume', icon: FileText },
  { href: '/jobs', label: 'Jobs', icon: Briefcase },
]

export default function Navbar() {
  const router = useRouter()
  const pathname = usePathname()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/auth/login')
  }

  return (
    <nav className="bg-[#1E3A5F] text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/dashboard" className="flex items-center gap-2">
              <Brain className="h-8 w-8 text-[#6C3FC8]" />
              <span className="font-bold text-xl">AI Career Navigator</span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-1">
            {navLinks.map((link) => {
              const Icon = link.icon
              const isActive = pathname === link.href
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isActive
                      ? 'bg-[#6C3FC8] text-white'
                      : 'text-gray-200 hover:bg-white/10 hover:text-white'
                    }`}
                >
                  <Icon className="h-4 w-4" />
                  {link.label}
                </Link>
              )
            })}
            <Button
              variant="ghost"
              onClick={handleLogout}
              className="ml-4 text-gray-200 hover:text-white hover:bg-white/10 flex items-center gap-2"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </Button>
          </div>

          {/* Mobile menu button */}
          <div className="flex items-center md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="inline-flex items-center justify-center p-2 rounded-md text-gray-200 hover:text-white hover:bg-white/10 focus:outline-none"
            >
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-white/10">
          <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3">
            {navLinks.map((link) => {
              const Icon = link.icon
              const isActive = pathname === link.href
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-3 py-3 rounded-lg text-base font-medium ${isActive
                      ? 'bg-[#6C3FC8] text-white'
                      : 'text-gray-200 hover:bg-white/10 hover:text-white'
                    }`}
                >
                  <Icon className="h-5 w-5" />
                  {link.label}
                </Link>
              )
            })}
            <button
              onClick={handleLogout}
              className="flex w-full items-center gap-3 px-3 py-3 rounded-lg text-base font-medium text-gray-200 hover:bg-white/10 hover:text-white"
            >
              <LogOut className="h-5 w-5" />
              Logout
            </button>
          </div>
        </div>
      )}
    </nav>
  )
}
