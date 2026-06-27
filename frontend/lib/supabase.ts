import { createBrowserClient } from '@supabase/ssr'
import { type SupabaseClient } from '@supabase/supabase-js'

// Create client-side supabase client using HTTP-only cookies
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

  supabaseClient = createBrowserClient(supabaseUrl, supabaseAnonKey)

  return supabaseClient
}

/**
 * Export a singleton instance - but LAZILY.
 *
 * IMPORTANT: this used to be `export const supabase = getSupabaseClient()`,
 * which called getSupabaseClient() immediately at module-import time. That
 * defeated the entire point of getSupabaseClient()'s lazy-singleton design:
 * simply importing ANYTHING from this module (or from another module that
 * re-exports from here, e.g. career-safe.ts) would throw immediately if
 * NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY weren't set -
 * even for code that never actually touches Supabase. This broke, for
 * example, unit-testing career-safe.ts's pure helper functions, and would
 * equally break any environment (local dev without .env.local, preview
 * deploys, etc.) that imports this module before env vars are configured.
 *
 * A Proxy defers the real getSupabaseClient() call until the first actual
 * property access (e.g. supabase.auth.getSession()), so existing call
 * sites need no changes, but the throw now only happens when Supabase is
 * genuinely used - which is the original intent.
 */
export const supabase: SupabaseClient = new Proxy({} as SupabaseClient, {
  get(_target, prop, receiver) {
    const client = getSupabaseClient()
    return Reflect.get(client, prop, receiver)
  },
})

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