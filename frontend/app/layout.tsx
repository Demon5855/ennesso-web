import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    default: "Ennesso — Energy Data Governance",
    template: "%s | Ennesso",
  },
  description:
    "Energy data governance and balance platform for Ecuador's electricity system. " +
    "Generation mix, carbon accounting, and data lineage from CENACE.",
  metadataBase: new URL("https://ennesso.energy"),
  openGraph: {
    type: "website",
    locale: "es_EC",
    url: "https://ennesso.energy",
    siteName: "Ennesso",
    title: "Ennesso — Energy Data Governance",
    description:
      "Real-time energy balance, carbon intensity, and data lineage for " +
      "Ecuador's national electricity system (SNI).",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Ennesso Energy Dashboard",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Ennesso — Energy Data Governance",
    description:
      "Energy balance and carbon accounting for Ecuador's electricity system.",
    images: ["/og-image.png"],
  },
  keywords: [
    "Ecuador energy",
    "CENACE",
    "energy governance",
    "carbon intensity",
    "SNI Ecuador",
    "renewable energy",
    "energy data",
  ],
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
