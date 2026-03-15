import { createClient, type SupabaseClient } from '@supabase/supabase-js'

// Create client-side supabase client using localStorage
let supabaseClient: SupabaseClient | null = null

export function getSupabaseClient(): SupabaseClient {
  if (supabaseClient) {
    return supabaseClient
  }

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error('Missing Supabase environment variables')
  }

  supabaseClient = createClient(supabaseUrl, supabaseAnonKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
    },
  })

  return supabaseClient
}

// Export a singleton instance
export const supabase = getSupabaseClient()

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
