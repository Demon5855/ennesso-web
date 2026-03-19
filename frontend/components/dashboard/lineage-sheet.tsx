"use client";

import { useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { QualityBadge } from "@/components/ui/quality-badge";
import { fetchLineage } from "@/lib/api-client";
import type { LineageResponse } from "@/types/api";

interface LineageSheetProps {
  recordId: string | null;
  onClose: () => void;
}

export function LineageSheet({ recordId, onClose }: LineageSheetProps) {
  const [lineage, setLineage] = useState<LineageResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const open = recordId !== null;

  // Fetch when opened
  const handleOpenChange = async (isOpen: boolean) => {
    if (!isOpen) {
      onClose();
      return;
    }
    if (!recordId) return;

    setLoading(true);
    setError(null);
    try {
      const data = await fetchLineage(recordId);
      setLineage(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load lineage");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent
        className="w-[480px] sm:w-[540px] bg-surface border-border overflow-y-auto"
        side="right"
      >
        <SheetHeader className="pb-4 border-b border-border">
          <SheetTitle className="font-mono text-foreground">
            Data Lineage
          </SheetTitle>
          <SheetDescription className="font-sans text-muted text-sm">
            Full provenance for record{" "}
            <span className="font-mono text-xs">{recordId?.slice(0, 8)}…</span>
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-4">
          {loading && (
            <p className="font-mono text-sm text-muted animate-pulse">
              Loading lineage…
            </p>
          )}

          {error && (
            <p className="font-mono text-sm text-red-400">{error}</p>
          )}

          {!loading && !error && lineage.map((entry) => (
            <div
              key={entry.id}
              className="border border-border rounded-lg p-4 space-y-3"
            >
              {/* Header */}
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-muted">
                  {new Date(entry.ingested_at).toLocaleString()}
                </span>
                <QualityBadge flag={entry.quality_flag} showLabel />
              </div>

              {/* Source */}
              <div className="space-y-1">
                <Label>Source URL</Label>
                <a
                  href={entry.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-xs text-primary hover:underline break-all"
                >
                  {entry.source_url}
                </a>
              </div>

              {/* Method */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Method</Label>
                  <Value>{entry.ingestion_method}</Value>
                </div>
                <div>
                  <Label>Pipeline</Label>
                  <Value>{entry.pipeline_version ?? "—"}</Value>
                </div>
              </div>

              {/* Values */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Raw value</Label>
                  <Value>{entry.raw_value ?? "—"}</Value>
                </div>
                <div>
                  <Label>Transformed</Label>
                  <Value>{entry.transformed_value ?? "—"}</Value>
                </div>
              </div>

              {/* Correction */}
              {entry.correction_note && (
                <div>
                  <Label>Correction note</Label>
                  <p className="font-mono text-xs text-[#F5A623]">
                    {entry.correction_note}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-sans text-xs text-muted uppercase tracking-wide mb-0.5">
      {children}
    </p>
  );
}

function Value({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-xs text-foreground">{children}</p>
  );
}
