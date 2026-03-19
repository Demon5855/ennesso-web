"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  BarChart2,
  Zap,
  TrendingUp,
  Wind,
  Sliders,
  FileText,
  GitBranch,
  Activity,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/dashboard/overview", label: "Overview", icon: BarChart2 },
  { href: "/dashboard/generation", label: "Generation", icon: Zap },
  { href: "/dashboard/demand", label: "Demand", icon: TrendingUp },
  { href: "/dashboard/carbon", label: "Carbon", icon: Wind },
  { href: "/dashboard/simulator", label: "Simulator", icon: Sliders },
  { href: "/dashboard/reports", label: "Reports", icon: FileText },
  { href: "/dashboard/lineage", label: "Lineage", icon: GitBranch },
] as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 flex-shrink-0 bg-surface border-r border-border flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-border">
        <span className="font-mono text-lg font-semibold text-primary">
          Ennesso
        </span>
        <span className="font-sans text-xs text-muted block mt-0.5">
          Energy Governance
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname.includes(href.split("/").pop() ?? "");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-md transition-colors",
                "font-sans text-sm",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted hover:text-foreground hover:bg-white/5"
              )}
            >
              <Icon
                size={15}
                className={cn(active ? "text-primary" : "text-muted")}
              />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-border">
        <div className="flex items-center gap-2">
          <Activity size={12} className="text-[#00C2A8]" />
          <span className="font-mono text-xs text-muted">EC · Live</span>
        </div>
      </div>
    </aside>
  );
}
