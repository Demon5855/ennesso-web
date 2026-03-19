"use client";

import { useState } from "react";
import { FileText, Table, Loader2 } from "lucide-react";
import { Topbar } from "@/components/layout/topbar";
import { downloadReport } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export default function ReportsPage() {
  const [startDate, setStartDate] = useState(() => {
    const d = new Date();
    d.setMonth(d.getMonth() - 3);
    return d.toISOString().split("T")[0] ?? "";
  });
  const [endDate, setEndDate] = useState(
    () => new Date().toISOString().split("T")[0] ?? ""
  );
  const [includeLineage, setIncludeLineage] = useState(false);
  const [loadingExcel, setLoadingExcel] = useState(false);
  const [loadingPdf, setLoadingPdf] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDownload(format: "excel" | "pdf") {
    setError(null);
    const setter = format === "excel" ? setLoadingExcel : setLoadingPdf;
    setter(true);
    try {
      await downloadReport(format, {
        start_date: startDate,
        end_date: endDate,
        include_lineage: includeLineage,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setter(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <Topbar title="REPORTS" />

      <div className="p-6 max-w-2xl space-y-6">
        <p className="font-sans text-sm text-muted">
          Generate energy reports with generation data and carbon summary.
          Exports are available in Excel and PDF formats.
        </p>

        {/* Config card */}
        <div className="bg-surface border border-border rounded-lg p-6 space-y-5">
          <h2 className="font-mono text-xs text-muted uppercase tracking-widest">
            Report Parameters
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="font-sans text-xs text-muted">
                Start date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className={cn(
                  "w-full bg-background border border-border rounded px-3 py-2",
                  "font-mono text-sm text-foreground",
                  "focus:outline-none focus:border-primary"
                )}
              />
            </div>
            <div className="space-y-1.5">
              <label className="font-sans text-xs text-muted">End date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className={cn(
                  "w-full bg-background border border-border rounded px-3 py-2",
                  "font-mono text-sm text-foreground",
                  "focus:outline-none focus:border-primary"
                )}
              />
            </div>
          </div>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={includeLineage}
              onChange={(e) => setIncludeLineage(e.target.checked)}
              className="accent-primary h-4 w-4"
            />
            <span className="font-sans text-sm text-foreground">
              Include data lineage audit section
            </span>
          </label>

          {error && (
            <p className="font-mono text-xs text-red-400">{error}</p>
          )}
        </div>

        {/* Export buttons */}
        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={() => void handleDownload("excel")}
            disabled={loadingExcel}
            className={cn(
              "flex items-center justify-center gap-3 p-5",
              "bg-surface border border-border rounded-lg",
              "hover:border-primary/50 transition-colors",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {loadingExcel ? (
              <Loader2 size={18} className="animate-spin text-primary" />
            ) : (
              <Table size={18} className="text-[#7ED321]" />
            )}
            <div className="text-left">
              <p className="font-sans text-sm font-medium text-foreground">
                Export Excel
              </p>
              <p className="font-sans text-xs text-muted">
                .xlsx — Generation + Carbon sheets
              </p>
            </div>
          </button>

          <button
            onClick={() => void handleDownload("pdf")}
            disabled={loadingPdf}
            className={cn(
              "flex items-center justify-center gap-3 p-5",
              "bg-surface border border-border rounded-lg",
              "hover:border-primary/50 transition-colors",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {loadingPdf ? (
              <Loader2 size={18} className="animate-spin text-primary" />
            ) : (
              <FileText size={18} className="text-[#E05C2A]" />
            )}
            <div className="text-left">
              <p className="font-sans text-sm font-medium text-foreground">
                Export PDF
              </p>
              <p className="font-sans text-xs text-muted">
                .pdf — Summary report with tables
              </p>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
