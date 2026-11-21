"use client";

import { useEffect, useState } from "react";
import styles from "./ScanResults.module.css";

type Scan = { id: number; target_url: string; status: string };

type Finding = {
  id: number;
  type: string;
  title: string;
  description: string;
  legal_article: string | null;
  max_penalty: number | null;
};

const STATUS_TEXT: Record<string, string> = {
  pending: "Готовим проверку…",
  running: "Сканируем безопасность и 152-ФЗ…",
  completed: "Готово",
  failed: "Не удалось завершить проверку",
};

export function ScanResults({
  scanId,
  targetUrl,
  onReset,
}: {
  scanId: number;
  targetUrl: string;
  onReset: () => void;
}) {
  const [scan, setScan] = useState<Scan | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);

  useEffect(() => {
    let active = true;

    async function poll() {
      const res = await fetch(`/api/scans/${scanId}`);
      if (!res.ok) return;
      const data: Scan = await res.json();
      if (!active) return;
      setScan(data);

      if (data.status === "completed") {
        const fr = await fetch(`/api/scans/${scanId}/findings`);
        if (fr.ok) setFindings(await fr.json());
        return;
      }
      if (data.status === "failed") return;
      setTimeout(poll, 3000);
    }

    poll();
    return () => {
      active = false;
    };
  }, [scanId]);

  const busy = !scan || scan.status === "pending" || scan.status === "running";

  return (
    <section className={styles.wrap}>
      <div className={styles.head}>
        <h2 className={styles.title}>Результат</h2>
        <button type="button" className={styles.reset} onClick={onReset}>
          Новая проверка
        </button>
      </div>
      <p className={styles.url}>{targetUrl}</p>
      <p className={styles.status}>
        {scan ? STATUS_TEXT[scan.status] ?? scan.status : "Загрузка…"}
      </p>
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
                <p className={styles.badge}>
                  {f.type === "security" ? "Безопасность" : "152-ФЗ"}
                </p>
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
    </section>
  );
}