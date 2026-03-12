import createMiddleware from "next-intl/middleware";

export default createMiddleware({
  // Supported locales
  locales: ["es", "en", "it"],
  // Default locale (no prefix for Spanish)
  defaultLocale: "es",
  localePrefix: "as-needed",
});

export const config = {
  // Match all pathnames except static files and Next.js internals
  matcher: [
    "/((?!_next|_vercel|.*\\..*).*)",
  ],
};
