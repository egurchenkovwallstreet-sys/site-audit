"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import styles from "./check.module.css";

type Scan = { id: number; target_url: string; status: string };

type Finding = {
  id: number;
  title: string;
  description: string;
  legal_article: string | null;
  max_penalty: number | null;
  color: string | null;
};

const STEPS: Record<string, string> = {
  pending: "Готовим проверку…",
  running: "Проверяем 152-ФЗ…",
  completed: "Готово",
  failed: "Не удалось завершить проверку",
};

export function CheckView({ scanId }: { scanId: string }) {
  const [scan, setScan] = useState<Scan | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const res = await fetch(`/api/scans/${scanId}`);
        if (!res.ok) throw new Error("not_found");
        const data: Scan = await res.json();
        if (!active) return;
        setScan(data);

        if (data.status === "completed") {
          const fr = await fetch(`/api/scans/${scanId}/findings`);
          if (fr.ok) {
            setFindings(await fr.json());
          }
          return;
        }
        if (data.status === "failed") return;

        setTimeout(poll, 3000);
      } catch {
        if (active) setError("Проверка не найдена.");
      }
    }

    poll();
    return () => {
      active = false;
    };
  }, [scanId]);

  const busy = scan && (scan.status === "pending" || scan.status === "running");

  return (
    <div className={styles.page}>
      <Link href="/" className={styles.back}>
        ← Новая проверка
      </Link>
      <h1 className={styles.title}>Результат проверки</h1>
      {scan ? <p className={styles.url}>{scan.target_url}</p> : null}
      {error ? <p className={styles.error}>{error}</p> : null}
      {scan ? (
        <p className={styles.status}>{STEPS[scan.status] ?? scan.status}</p>
      ) : (
        <p className={styles.status}>Загрузка…</p>
      )}
      {busy ? (
        <div className={styles.loader}>
          <div className={styles.loaderBar} />
        </div>
      ) : null}
      {scan?.status === "completed" ? (
        findings.length > 0 ? (
          <ul className={styles.list}>
            {findings.map((f) => (
              <li key={f.id} className={styles.item}>
                <p className={styles.itemTitle}>{f.title}</p>
                <p className={styles.itemMeta}>{f.description}</p>
                {f.legal_article ? (
                  <p className={styles.itemMeta}>{f.legal_article}</p>
                ) : null}
                {f.max_penalty != null ? (
                  <p className={styles.penalty}>
                    До {f.max_penalty.toLocaleString("ru-RU")} ₽
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className={styles.itemMeta}>
            Замечаний по 152-ФЗ на главной странице не найдено.
          </p>
        )
      ) : null}
    </div>
  );
}