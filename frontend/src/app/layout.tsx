import type { Metadata } from "next";
import "./globals.css";
import { ThemeScript } from "@/components/ThemeScript";

const siteUrl = (
  process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"
).replace(/\/$/, "");

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Проверка сайта на 152-ФЗ, 168-ФЗ и уязвимости",
    template: "%s | Проверка сайта",
  },
  description:
    "Онлайн-аудит сайта: 152-ФЗ, cookie, формы, 168-ФЗ, SEO, техриски и Nuclei. До 30 приоритетных страниц, таймер на экране 7:59.",
  keywords: [
    "проверка сайта",
    "152-ФЗ",
    "168-ФЗ",
    "аудит сайта",
    "штрафы сайт",
    "политика персональных данных",
    "проверка на соответствие законодательству",
  ],
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    locale: "ru_RU",
    url: siteUrl,
    siteName: "Проверка сайта",
    title: "Проверка сайта на 152-ФЗ и технические риски",
    description:
      "Автоматический аудит: 152-ФЗ, SEO, безопасность. Без регистрации.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Проверка сайта — 152-ФЗ и безопасность",
    description:
      "Онлайн-скан сайта на риски штрафов и технические уязвимости.",
  },
  robots: { index: true, follow: true },
  other: { google: "notranslate" },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "Проверка сайта — 152-ФЗ и безопасность",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  url: siteUrl,
  inLanguage: "ru",
  description:
    "Онлайн-аудит сайта: 152-ФЗ, cookie, формы, 168-ФЗ, SEO и технические проверки.",
  offers: { "@type": "Offer", price: "0", priceCurrency: "RUB" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" translate="no" data-theme="dark" suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body className="notranslate">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        {children}
      </body>
    </html>
  );
}