import { useTranslations } from "next-intl";
import { Link } from "@/lib/i18n-navigation";

export default function HomePage() {
  const t = useTranslations("home");

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
      <div className="text-center space-y-4">
        <h1 className="font-mono text-4xl font-semibold text-primary">
          Ennesso
        </h1>
        <p className="text-muted-foreground text-lg max-w-md">
          {t("tagline")}
        </p>
      </div>
      <Link
        href="/dashboard"
        className="px-6 py-3 bg-primary text-primary-foreground rounded-md font-sans font-medium hover:opacity-90 transition-opacity"
      >
        {t("cta")}
      </Link>
    </main>
  );
}
