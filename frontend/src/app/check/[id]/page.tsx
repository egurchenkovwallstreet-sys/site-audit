import type { Metadata } from "next";
import { CheckPageClient } from "./CheckPageClient";

export const metadata: Metadata = {
  title: "Результат проверки сайта",
  robots: { index: false, follow: false },
};

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function CheckPage({ params }: PageProps) {
  const { id: token } = await params;
  return <CheckPageClient scanToken={token} />;
}