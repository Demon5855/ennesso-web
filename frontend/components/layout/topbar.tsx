"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { CalendarIcon, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  useDateRange,
  MIN_DATE,
} from "@/hooks/use-date-range";
import { LanguageSwitcher } from "@/components/layout/language-switcher";

interface TopbarProps {
  title: string;
  showDatePicker?: boolean;
}

function todayISO(): string {
  return new Date().toISOString().split("T")[0] ?? "";
}

export function Topbar({ title, showDatePicker = true }: TopbarProps) {
  const t = useTranslations("common");
  const tDR = useTranslations("dateRange");
  const { startDate, endDate, setDateRange, error, label } = useDateRange();

  const [draftStart, setDraftStart] = useState(startDate);
  const [draftEnd, setDraftEnd] = useState(endDate);
  const [localError, setLocalError] = useState<string | null>(null);

  // Keep draft in sync if context changes externally (e.g. URL navigation)
  useEffect(() => {
    setDraftStart(startDate);
    setDraftEnd(endDate);
  }, [startDate, endDate]);

  function handleApply() {
    const ok = setDateRange(draftStart, draftEnd);
    if (!ok && error) {
      const KEY_MAP: Record<NonNullable<typeof error>, string> = {
        start_too_early: "startTooEarly",
        end_in_future: "endInFuture",
        start_after_end: "startAfterEnd",
        range_too_large: "rangeTooLarge",
      };
      setLocalError(tDR(KEY_MAP[error]));
    } else {
      setLocalError(null);
    }
  }

  function handleStartChange(value: string) {
    setDraftStart(value);
    setLocalError(null);
  }

  function handleEndChange(value: string) {
    setDraftEnd(value);
    setLocalError(null);
  }

  return (
    <header className="flex-shrink-0 border-b border-border bg-background">
      <div className="h-14 flex items-center justify-between px-6">
        {/* Title */}
        <h1 className="font-mono text-sm font-semibold text-foreground tracking-widest uppercase">
          {title}
        </h1>

        <div className="flex items-center gap-4">
          {/* Date range picker */}
          {showDatePicker && (
            <div className="flex items-center gap-2">
              <CalendarIcon size={13} className="text-muted flex-shrink-0" />

              {/* Range label (compact display) */}
              <span className="font-mono text-xs text-muted hidden lg:block min-w-[140px]">
                {label}
              </span>

              <div className="flex items-center gap-1.5">
                <input
                  type="date"
                  value={draftStart}
                  min={MIN_DATE}
                  max={todayISO()}
                  onChange={(e) => handleStartChange(e.target.value)}
                  className={cn(
                    "bg-surface border rounded px-2 py-1",
                    "font-mono text-xs text-foreground",
                    "focus:outline-none focus:border-primary",
                    localError ? "border-red-500" : "border-border"
                  )}
                />
                <span className="font-mono text-xs text-muted">→</span>
                <input
                  type="date"
                  value={draftEnd}
                  min={MIN_DATE}
                  max={todayISO()}
                  onChange={(e) => handleEndChange(e.target.value)}
                  className={cn(
                    "bg-surface border rounded px-2 py-1",
                    "font-mono text-xs text-foreground",
                    "focus:outline-none focus:border-primary",
                    localError ? "border-red-500" : "border-border"
                  )}
                />
                <button
                  onClick={handleApply}
                  className={cn(
                    "px-3 py-1 rounded bg-primary text-background",
                    "font-sans text-xs font-medium",
                    "hover:opacity-90 transition-opacity"
                  )}
                >
                  {t("apply")}
                </button>
              </div>
            </div>
          )}

          {/* Language switcher */}
          <LanguageSwitcher />
        </div>
      </div>

      {/* Validation error — shown below the topbar bar */}
      {localError && (
        <div className="px-6 pb-2 flex items-center gap-2">
          <AlertCircle size={12} className="text-red-400 flex-shrink-0" />
          <span className="font-mono text-xs text-red-400">{localError}</span>
        </div>
      )}
    </header>
  );
}
