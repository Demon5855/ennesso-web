import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import "@/app/globals.css";

export const metadata: Metadata = {
  title: { default: "Ennesso — Energy Data Governance", template: "%s | Ennesso" },
  description: "Platform for energy data governance.",
  metadataBase: new URL("https://ennesso.energy"),
};

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
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
  return ["es", "en", "it"].map((locale) => ({ locale }));
}