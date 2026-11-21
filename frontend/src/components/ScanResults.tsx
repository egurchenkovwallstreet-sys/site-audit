"use client";

import { useEffect, useMemo, useState } from "react";
import styles from "./ScanResults.module.css";
import {
  resolveRiskColor,
  severityLabel,
  sortFindings,
  type RiskColor,
} from "@/lib/findingRisk";

type Scan = { id: number; target_url: string; status: string };

type Finding = {
  id: number;
  type: string;
  severity: string;
  title: string;
  description: string;
  legal_article: string | null;
  max_penalty: number | null;
  color: string | null;
};

const STATUS_TEXT: Record<string, string> = {
  pending: "Готовим проверку…",
  running: "Сканируем безопасность и 152-ФЗ…",
  completed: "Готово",
  failed: "Не удалось завершить проверку",
};

const RISK_ITEM_CLASS: Record<RiskColor, string> = {
  red: styles.itemRed,
  yellow: styles.itemYellow,
  green: styles.itemGreen,
};

const RISK_PILL_CLASS: Record<RiskColor, string> = {
  red: styles.riskPillRed,
  yellow: styles.riskPillYellow,
  green: styles.riskPillGreen,
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
        if (fr.ok) {
          const raw: Finding[] = await fr.json();
          setFindings(sortFindings(raw));
        }
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

  const riskSummary = useMemo(() => {
    let red = 0;
    let yellow = 0;
    let topPenalty = 0;
    for (const f of findings) {
      const c = resolveRiskColor(f);
      if (c === "red") red += 1;
      if (c === "yellow") yellow += 1;
      if (f.max_penalty != null && f.max_penalty > topPenalty) {
        topPenalty = f.max_penalty;
      }
    }
    return { red, yellow, topPenalty };
  }, [findings]);

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
        {scan ? (STATUS_TEXT[scan.status] ?? scan.status) : "Загрузка…"}
      </p>
      {busy ? (
        <div className={styles.loader}>
          <div className={styles.loaderBar} />
        </div>
      ) : null}
      {scan?.status === "completed" ? (
        findings.length > 0 ? (
          <>
            <div className={styles.legend} aria-label="Шкала рисков">
              <span className={styles.legendTitle}>Шкала по ТЗ:</span>
              <span className={`${styles.legendDot} ${styles.dotGreen}`} />
              до 10 000 ₽
              <span className={`${styles.legendDot} ${styles.dotYellow}`} />
              до 100 000 ₽
              <span className={`${styles.legendDot} ${styles.dotRed}`} />
              свыше 100 000 ₽ и критичные уязвимости
            </div>
            {riskSummary.red > 0 || riskSummary.topPenalty > 0 ? (
              <p className={styles.summary}>
                {riskSummary.red > 0 ? (
                  <>
                    <span className={styles.summaryCritical}>
                      Критичных: {riskSummary.red}
                    </span>
                    {riskSummary.yellow > 0
                      ? ` · средний риск: ${riskSummary.yellow}`
                      : ""}
                    {riskSummary.topPenalty > 0 ? " · " : ""}
                  </>
                ) : null}
                {riskSummary.topPenalty > 0 ? (
                  <>
                    Максимальный штраф по пункту:{" "}
                    <span className={styles.summaryPenalty}>
                      до {riskSummary.topPenalty.toLocaleString("ru-RU")} ₽
                    </span>
                  </>
                ) : null}
              </p>
            ) : null}
            <ul className={styles.list}>
              {findings.map((f) => {
                const risk = resolveRiskColor(f);
                return (
                  <li
                    key={f.id}
                    className={`${styles.item} ${RISK_ITEM_CLASS[risk]}`}
                  >
                    <div className={styles.itemHead}>
                      <p className={styles.badge}>
                        {f.type === "security" ? "Безопасность" : "152-ФЗ"}
                      </p>
                      <span
                        className={`${styles.riskPill} ${RISK_PILL_CLASS[risk]}`}
                      >
                        {severityLabel(f.severity)}
                      </span>
                    </div>
                    <p className={styles.itemTitle}>{f.title}</p>
                    <p className={styles.itemMeta}>{f.description}</p>
                    {f.legal_article ? (
                      <p className={styles.itemMeta}>{f.legal_article}</p>
                    ) : null}
                    {f.max_penalty != null ? (
                      <p
                        className={`${styles.penalty} ${styles[`penalty_${risk}`]}`}
                      >
                        Штраф до {f.max_penalty.toLocaleString("ru-RU")} ₽
                      </p>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </>
        ) : (
          <p className={styles.itemMeta}>
            Замечаний по 152-ФЗ на главной странице не найдено.
          </p>
        )
      ) : null}
    </section>
  );
}