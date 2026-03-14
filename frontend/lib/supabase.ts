import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Type for user profile
export interface UserProfile {
  id: string
  email: string
  created_at: string
  github_url?: string
  leetcode_username?: string
  linkedin_url?: string
  resume_url?: string
  analysis_complete?: boolean
}

// Type for auth session
export interface AuthSession {
  access_token: string
  refresh_token: string
  user: {
    id: string
    email: string
  }
}
