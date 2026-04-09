import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const PUBLIC_ROUTES = ['/', '/auth/login', '/auth/signup', '/auth/callback', '/onboarding']

export async function middleware(request: NextRequest) {
  const res = NextResponse.next()

  // Skip auth check for API routes - FastAPI handles auth separately
  if (request.nextUrl.pathname.startsWith('/api/')) {
    return res
  }

  const supabase = createMiddlewareClient({ req: request, res })

  // Use getUser() to properly validate the session token
  const { data: { user }, error } = await supabase.auth.getUser()

  const { pathname } = request.nextUrl

  if (PUBLIC_ROUTES.includes(pathname)) {
    return res
  }

  if (!user || error) {
    const loginUrl = new URL('/auth/login', request.url)
    loginUrl.searchParams.set('next', pathname)
    return NextResponse.redirect(loginUrl)
  }

  return res
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|public).*)'],
}
