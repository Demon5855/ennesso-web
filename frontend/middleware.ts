import createMiddleware from "next-intl/middleware";
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { defineRouting } from "next-intl/routing";

const routing = defineRouting({
  locales: ["es", "en", "it"],
  defaultLocale: "es",
  localePrefix: "as-needed",
});

const intlMiddleware = createMiddleware(routing);

export default async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Always run intl middleware first so it sets the x-next-intl-locale header.
  // If it issues a redirect (e.g. normalizing the locale prefix), respect it immediately.
  const intlResponse = intlMiddleware(request);
  if (intlResponse.status !== 200) return intlResponse;

  const isDashboard = pathname.includes("/dashboard");

  if (isDashboard) {
    // Build the base response, carrying forward the intl headers
    // so that requestLocale in i18n/request.ts resolves correctly.
    const supabaseInit = { request };
    let supabaseResponse = NextResponse.next(supabaseInit);

    // Copy all headers set by intlMiddleware onto supabaseResponse
    intlResponse.headers.forEach((value, key) => {
      supabaseResponse.headers.set(key, value);
    });

    const supabase = createServerClient(
      process.env["NEXT_PUBLIC_SUPABASE_URL"]!,
      process.env["NEXT_PUBLIC_SUPABASE_ANON_KEY"]!,
      {
        cookies: {
          getAll() { return request.cookies.getAll(); },
          setAll(cookiesToSet) {
            cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
            supabaseResponse = NextResponse.next(supabaseInit);
            // Re-copy intl headers after supabaseResponse is re-created
            intlResponse.headers.forEach((value, key) => {
              supabaseResponse.headers.set(key, value);
            });
            cookiesToSet.forEach(({ name, value, options }) =>
              supabaseResponse.cookies.set(name, value, options)
            );
          },
        },
      }
    );

    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      const url = request.nextUrl.clone();
      url.pathname = "/auth/sign-in";
      return NextResponse.redirect(url);
    }

    return supabaseResponse;
  }

  return intlResponse;
}

export const config = {
  matcher: ["/((?!_next|_vercel|.*\\..*).*)" ],
};
