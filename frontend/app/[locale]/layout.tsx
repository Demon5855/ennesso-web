import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import "@/app/globals.css";

const locales = ["es", "en", "it"] as const;
type Locale = (typeof locales)[number];

export const metadata: Metadata = {
  title: {
    default: "Ennesso — Energy Data Governance",
    template: "%s | Ennesso",
  },
  description:
    "Platform for energy data governance and balance in Ecuador's electricity system.",
  metadataBase: new URL("https://ennesso.energy"),
};

interface LocaleLayoutProps {
  children: React.ReactNode;
  params: { locale: string };
}

export default async function LocaleLayout({
  children,
  params: { locale },
}: LocaleLayoutProps) {
  // Validate locale
  if (!locales.includes(locale as Locale)) {
    notFound();
  }

  const messages = await getMessages();

  return (
    <html lang={locale} className="dark">
      <body>
        <NextIntlClientProvider messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}
