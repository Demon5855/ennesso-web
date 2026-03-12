import { createLocalizedPathnamesNavigation } from "next-intl/navigation";
import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["es", "en", "it"] as const,
  defaultLocale: "es",
  localePrefix: "as-needed",
  pathnames: {
    "/": "/",
    "/dashboard": "/dashboard",
    "/auth/sign-in": "/auth/sign-in",
  },
});

export const { Link, redirect, usePathname, useRouter } =
  createLocalizedPathnamesNavigation(routing);
