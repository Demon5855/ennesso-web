import type { Metadata } from "next";
import { useTranslations } from "next-intl";

export const metadata: Metadata = {
  title: "Dashboard",
};

export default function DashboardPage() {
  const t = useTranslations("dashboard");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-mono text-2xl font-semibold text-foreground">
          {t("title")}
        </h1>
        <p className="text-muted-foreground mt-1">{t("subtitle")}</p>
      </div>
      {/* TODO: Generation balance chart */}
      {/* TODO: KPI cards */}
      {/* TODO: Hourly dispatch table */}
    </div>
  );
}
