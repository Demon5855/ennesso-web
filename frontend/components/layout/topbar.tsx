"use client";

import { useState } from "react";
import { CalendarIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface TopbarProps {
  title: string;
  onDateChange?: (start: string, end: string) => void;
}

function defaultDates(): { start: string; end: string } {
  const end = new Date();
  const start = new Date();
  start.setMonth(start.getMonth() - 12);
  return {
    start: start.toISOString().split("T")[0] ?? "",
    end: end.toISOString().split("T")[0] ?? "",
  };
}

export function Topbar({ title, onDateChange }: TopbarProps) {
  const defaults = defaultDates();
  const [startDate, setStartDate] = useState(defaults.start);
  const [endDate, setEndDate] = useState(defaults.end);

  function handleApply() {
    onDateChange?.(startDate, endDate);
  }

  return (
    <header className="h-14 border-b border-border bg-background flex items-center justify-between px-6 flex-shrink-0">
      <h1 className="font-mono text-sm font-semibold text-foreground tracking-wide">
        {title}
      </h1>

      <div className="flex items-center gap-3">
        <CalendarIcon size={14} className="text-muted" />

        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          className={cn(
            "bg-surface border border-border rounded px-2 py-1",
            "font-mono text-xs text-foreground",
            "focus:outline-none focus:border-primary"
          )}
        />
        <span className="font-mono text-xs text-muted">→</span>
        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          className={cn(
            "bg-surface border border-border rounded px-2 py-1",
            "font-mono text-xs text-foreground",
            "focus:outline-none focus:border-primary"
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
          Apply
        </button>
      </div>
    </header>
  );
}
