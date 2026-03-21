"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { FileText, Table, Loader2 } from "lucide-react";
import { Topbar } from "@/components/layout/topbar";
import { downloadReport } from "@/lib/api-client";
import { useDateRange } from "@/hooks/use-date-range";
import { cn } from "@/lib/utils";

export default function ReportsPage() {
  const t = useTranslations("reports");
  const { startDate, endDate } = useDateRange();
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
      <Topbar title={t("title").toUpperCase()} />
      <div className="p-6 max-w-2xl space-y-6">
        <p className="font-sans text-sm text-muted">
          {t("generatingFor", { start: startDate, end: endDate })}
        </p>

        <div className="bg-surface border border-border rounded-lg p-6 space-y-4">
          <h2 className="font-mono text-xs text-muted uppercase tracking-widest">
            {t("exportOptions")}
          </h2>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={includeLineage}
              onChange={(e) => setIncludeLineage(e.target.checked)}
              className="accent-primary h-4 w-4"
            />
            <span className="font-sans text-sm text-foreground">
              {t("includeLineage")}
            </span>
          </label>

          {error && (
            <p className="font-mono text-xs text-red-400">{error}</p>
          )}
        </div>

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
              <p className="font-sans text-sm font-medium text-foreground">{t("exportExcel")}</p>
              <p className="font-sans text-xs text-muted">{t("xlsxDesc")}</p>
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
              <p className="font-sans text-sm font-medium text-foreground">{t("exportPdf")}</p>
              <p className="font-sans text-xs text-muted">{t("pdfDesc")}</p>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
