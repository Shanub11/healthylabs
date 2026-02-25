import { NextResponse, type NextRequest } from 'next/server';
import { createServerClient } from '@supabase/ssr';

// Suppress specific console errors from Supabase client to avoid noise in dev
const originalConsoleError = console.error;
console.error = (...args) => {
  if (args.length > 0) {
    const arg = args[0];
    if (arg instanceof Error && (
      arg.message.includes('fetch failed') ||
      arg.message.includes('Failed to fetch') ||
      arg.message.includes('AuthRetryableFetchError')
    )) {
      return;
    }
  }
  originalConsoleError(...args);
};

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({
            request,
          });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  let session = null;
  try {
    const { data } = await supabase.auth.getSession();
    session = data.session;
  } catch (error) {
    // Suppress fetch errors to prevent noise in dev console when network is unstable
    if (error instanceof Error && !error.message.includes('fetch failed') && !error.message.includes('Failed to fetch')) {
      console.error('Middleware session check failed:', error);
    }
  }

  // Define paths that are accessible without authentication
  const publicPaths = ['/', '/Login', '/Register'];
  const isPublicPath = publicPaths.includes(request.nextUrl.pathname);

  // If not logged in and trying to access a protected route
  if (!session && !isPublicPath) {
    return NextResponse.redirect(new URL('/Login', request.url));
  }

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - images - .svg, .png, .jpg, .jpeg, .gif, .webp
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};