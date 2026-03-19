"use client";

import Link from "next/link";
import { ArrowRight, Database, BarChart2, Shield, Zap } from "lucide-react";

const STATS = [
  { value: "2021–2025", label: "Historical data" },
  { value: "~50K+", label: "MWh records" },
  { value: "5", label: "Generation types" },
  { value: "IPCC AR5", label: "Carbon methodology" },
];

const FEATURES = [
  {
    icon: Database,
    title: "Data Governance",
    description:
      "Full lineage tracking from CENACE source to dashboard. Every record is traceable to its origin URL, ingestion method, and transformation pipeline.",
  },
  {
    icon: BarChart2,
    title: "Energy Balance",
    description:
      "Daily generation mix, capacity factors, and demand estimates for Ecuador's SNI. Hydraulic, thermal, solar, wind, and biomass sources.",
  },
  {
    icon: Zap,
    title: "Carbon Engine",
    description:
      "IPCC AR5 lifecycle emission factors applied to the real generation mix. Tracks CO₂ intensity, avoided emissions, and renewable share.",
  },
  {
    icon: Shield,
    title: "Quality Control",
    description:
      "Automated validation rules flag data anomalies before they reach the database. Every record carries a quality flag with full audit history.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Nav */}
      <nav className="border-b border-border px-8 py-4 flex items-center justify-between">
        <span className="font-mono text-lg font-semibold text-primary">
          Ennesso
        </span>
        <div className="flex items-center gap-6">
          <span className="font-sans text-xs text-muted uppercase tracking-widest">
            Ecuador Energy Governance
          </span>
          <Link
            href="/dashboard/overview"
            className="flex items-center gap-2 px-4 py-2 bg-primary text-background rounded font-sans text-sm font-medium hover:opacity-90 transition-opacity"
          >
            Dashboard <ArrowRight size={14} />
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="px-8 py-24 max-w-5xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 border border-border rounded-full mb-8">
          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
          <span className="font-mono text-xs text-muted">
            Live · Ecuador SNI · CENACE data
          </span>
        </div>

        <h1 className="font-mono text-5xl font-semibold text-foreground leading-tight mb-6">
          Energy data
          <br />
          <span className="text-primary">governance</span> platform
          <br />
          for Ecuador.
        </h1>

        <p className="font-sans text-lg text-muted max-w-2xl mb-10 leading-relaxed">
          Ennesso ingests, validates, and serves generation data from CENACE
          with full lineage tracking, IPCC-aligned carbon accounting, and
          structured exports for institutional clients.
        </p>

        <div className="flex items-center gap-4">
          <Link
            href="/dashboard/overview"
            className="flex items-center gap-2 px-6 py-3 bg-primary text-background rounded font-sans font-medium hover:opacity-90 transition-opacity"
          >
            Open Dashboard <ArrowRight size={16} />
          </Link>
          <Link
            href="/dashboard/simulator"
            className="flex items-center gap-2 px-6 py-3 border border-border text-foreground rounded font-sans font-medium hover:border-primary/50 transition-colors"
          >
            Try Simulator
          </Link>
        </div>
      </section>

      {/* Stats strip */}
      <section className="border-y border-border bg-surface">
        <div className="max-w-5xl mx-auto px-8 py-8 grid grid-cols-4 divide-x divide-border">
          {STATS.map(({ value, label }) => (
            <div key={label} className="px-8 first:pl-0 last:pr-0">
              <p className="font-mono text-2xl font-semibold text-primary">
                {value}
              </p>
              <p className="font-sans text-xs text-muted mt-1">{label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-8 py-20">
        <p className="font-mono text-xs text-muted uppercase tracking-widest mb-10">
          Platform capabilities
        </p>
        <div className="grid grid-cols-2 gap-6">
          {FEATURES.map(({ icon: Icon, title, description }) => (
            <div
              key={title}
              className="border border-border rounded-lg p-6 bg-surface hover:border-primary/30 transition-colors"
            >
              <div className="flex items-center gap-3 mb-3">
                <Icon size={16} className="text-primary" />
                <h3 className="font-mono text-sm font-semibold text-foreground">
                  {title}
                </h3>
              </div>
              <p className="font-sans text-sm text-muted leading-relaxed">
                {description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Data sources */}
      <section className="border-t border-border bg-surface">
        <div className="max-w-5xl mx-auto px-8 py-12">
          <p className="font-mono text-xs text-muted uppercase tracking-widest mb-6">
            Data sources
          </p>
          <div className="flex flex-wrap gap-4">
            {[
              "CENACE — Información Operativa (daily HTML)",
              "CENACE — CKAN Portal (quarterly CSV)",
              "ARCERNNR — Boletín Estadístico (V2)",
            ].map((src) => (
              <span
                key={src}
                className="px-3 py-1.5 border border-border rounded font-mono text-xs text-muted"
              >
                {src}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border px-8 py-6 flex items-center justify-between">
        <span className="font-mono text-sm text-primary">Ennesso</span>
        <span className="font-sans text-xs text-muted">
          Perennia Systems · Ecuador · {new Date().getFullYear()}
        </span>
      </footer>
    </div>
  );
}
