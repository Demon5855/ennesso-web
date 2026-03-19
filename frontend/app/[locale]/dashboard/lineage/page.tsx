"use client";

import { useEffect, useState } from "react";
import { Topbar } from "@/components/layout/topbar";
import { QualityBadge } from "@/components/ui/quality-badge";
import { LineageSheet } from "@/components/dashboard/lineage-sheet";
import { fetchQualitySummary } from "@/lib/api-client";
import type { QualitySummaryResponse } from "@/types/api";

function defaultDates() {
  const end = new Date();
  const start = new Date();
  start.setMonth(start.getMonth() - 3);
  return {
    start: start.toISOString().split("T")[0] ?? "",
    end: end.toISOString().split("T")[0] ?? "",
  };
}

export default function LineagePage() {
  const dates = defaultDates();
  const [summary, setSummary] = useState<QualitySummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  async function load(start: string, end: string) {
    setLoading(true);
    try {
      setSummary(await fetchQualitySummary(start, end));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(dates.start, dates.end); }, []);

  return (
    <div className="flex flex-col h-full">
      <Topbar title="LINEAGE" onDateChange={(s, e) => void load(s, e)} />

      <div className="p-6 space-y-5">
        {/* Summary strip */}
        {summary && (
          <div className="flex gap-6 p-4 bg-surface border border-border rounded-lg">
            <Stat label="Total records" value={summary.total_records} />
            <Stat label="OK" value={summary.ok_count} color="#00C2A8" />
            <Stat label="Warning" value={summary.warning_count} color="#F5A623" />
            <Stat label="Error" value={summary.error_count} color="#EF4444" />
          </div>
        )}

        {/* Error records table */}
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <div className="px-5 py-3 border-b border-border">
            <h2 className="font-mono text-xs text-muted uppercase tracking-widest">
              Recent quality issues — click to inspect lineage
            </h2>
          </div>

          {loading && (
            <p className="font-mono text-sm text-muted p-5 animate-pulse">
              Loading…
            </p>
          )}

          {!loading && summary?.recent_errors.length === 0 && (
            <p className="font-mono text-sm text-muted p-5">
              No errors in this period. ✓
            </p>
          )}

          {!loading && summary && summary.recent_errors.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {["Record ID", "Date", "Type", "Notes", "Flag"].map((h) => (
                    <th
                      key={h}
                      className="px-5 py-2.5 text-left font-sans text-xs text-muted uppercase tracking-wide"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {summary.recent_errors.map((row) => (
                  <tr
                    key={row.record_id}
                    onClick={() => setSelectedId(row.record_id)}
                    className="border-b border-border hover:bg-white/5 cursor-pointer transition-colors"
                  >
                    <td className="px-5 py-3 font-mono text-xs text-primary">
                      {row.record_id.slice(0, 8)}…
                    </td>
                    <td className="px-5 py-3 font-mono text-xs text-foreground">
                      {row.record_date}
                    </td>
                    <td className="px-5 py-3 font-sans text-xs text-foreground capitalize">
                      {row.generation_type}
                    </td>
                    <td className="px-5 py-3 font-sans text-xs text-muted max-w-xs truncate">
                      {row.quality_notes ?? "—"}
                    </td>
                    <td className="px-5 py-3">
                      <QualityBadge flag="error" showLabel />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <LineageSheet
        recordId={selectedId}
        onClose={() => setSelectedId(null)}
      />
    </div>
  );
}

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div>
      <p className="font-sans text-xs text-muted mb-0.5">{label}</p>
      <p
        className="font-mono text-xl font-semibold"
        style={{ color: color ?? "#E8EAF0" }}
      >
        {value.toLocaleString()}
      </p>
    </div>
  );
}
