import type { MetadataRoute } from "next";

function siteUrl(): string {
  const raw =
    process.env.NEXT_PUBLIC_SITE_URL ||
    (process.env.VERCEL_URL && `https://${process.env.VERCEL_URL}`) ||
    "http://localhost:3000";
  return raw.replace(/\/$/, "");
}

export default function sitemap(): MetadataRoute.Sitemap {
  const base = siteUrl();
  const now = new Date();
  return [
    {
      url: base,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${base}/privacy`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.6,
    },
  ];
}