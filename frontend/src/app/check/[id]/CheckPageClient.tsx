"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { ScanResults } from "@/components/ScanResults";
import { ThemeToggle } from "@/components/ThemeToggle";
import styles from "../../home.module.css";

const TOKEN_RE = /^[A-Za-z0-9_-]{16,64}$/;

export function CheckPageClient({ scanToken }: { scanToken: string }) {
  const router = useRouter();
  const valid = TOKEN_RE.test(scanToken);

  useEffect(() => {
    if (!valid) {
      router.replace("/");
    }
  }, [valid, router]);

  if (!valid) {
    return null;
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <ThemeToggle />
      </header>
      <main className={styles.main}>
        <div className={styles.panel}>
          <ScanResults
            scanToken={scanToken}
            onReset={() => router.push("/")}
          />
        </div>
        <p className={styles.disclaimer}>
          Ссылку на эту страницу можно отправить коллеге — отчёт обновляется по
          мере проверки.
        </p>
      </main>
    </div>
  );
}