"use client";

import { useRouter, usePathname } from "@/lib/i18n-navigation";
import { useLocale } from "next-intl";
import { cn } from "@/lib/utils";
import { useState, useRef, useEffect } from "react";

const LOCALES = [
  { code: "es", label: "Español", short: "ES" },
  { code: "en", label: "English", short: "EN" },
  { code: "it", label: "Italiano", short: "IT" },
] as const;

type LocaleCode = (typeof LOCALES)[number]["code"];


export function LanguageSwitcher() {
  const router = useRouter();
  const pathname = usePathname(); // already locale-stripped by next-intl
  const locale = useLocale() as LocaleCode;
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function switchLocale(newLocale: LocaleCode) {
    router.replace(pathname || "/", { locale: newLocale });
    setOpen(false);
  }

  const current = LOCALES.find((l) => l.code === locale) ?? LOCALES[0]!;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "flex items-center gap-1.5 px-2.5 py-1.5 rounded",
          "font-mono text-xs text-muted border border-transparent",
          "hover:border-border hover:text-foreground transition-colors"
        )}
      >
        <span>{current.short}</span>
        <svg width="10" height="10" viewBox="0 0 10 10"
          className={cn("transition-transform", open ? "rotate-180" : "rotate-0")}
        >
          <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" />
        </svg>
      </button>

      {open && (
        <div className={cn(
          "absolute right-0 top-full mt-1 z-50",
          "bg-surface border border-border rounded-md shadow-lg",
          "min-w-[120px] py-1"
        )}>
          {LOCALES.map((l) => (
            <button
              key={l.code}
              onClick={() => switchLocale(l.code)}
              className={cn(
                "w-full flex items-center gap-2.5 px-3 py-2",
                "font-sans text-sm text-left transition-colors",
                l.code === locale
                  ? "text-primary bg-primary/5"
                  : "text-muted hover:text-foreground hover:bg-white/5"
              )}
            >
              <span className="font-mono text-xs w-5">{l.short}</span>
              <span>{l.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}