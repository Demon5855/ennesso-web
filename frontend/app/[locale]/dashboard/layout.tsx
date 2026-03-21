import { Sidebar } from "@/components/layout/sidebar";
import { DateRangeProvider } from "@/hooks/use-date-range";
import { Suspense } from "react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    // Suspense required because DateRangeProvider uses useSearchParams
    <Suspense>
      <DateRangeProvider>
        <div className="flex h-screen bg-background overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto">{children}</main>
        </div>
      </DateRangeProvider>
    </Suspense>
  );
}
