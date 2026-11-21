"use client";

import { useEffect, useMemo, useState } from "react";
import styles from "./ScanResults.module.css";
import {
  resolveRiskColor,
  severityLabel,
  sortFindings,
  sumBreachPenalties,
  sumCompliancePenalties,
  totalPenaltyColor,
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

function FindingItems({ items }: { items: Finding[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <ul className={styles.list}>
      {items.map((f) => {
        const risk = resolveRiskColor(f);
        const isForecast = f.type === "security";
        return (
          <li
            key={f.id}
            className={`${styles.item} ${RISK_ITEM_CLASS[risk]}`}
          >
            <div className={styles.itemHead}>
              <p className={styles.badge}>
                {isForecast ? "Прогноз · безопасность" : "Факт · 152-ФЗ"}
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
                {isForecast
                  ? "Возможный штраф при утечке или взломе через эту уязвимость: до "
                  : "Штраф по выявленному нарушению: до "}
                {f.max_penalty.toLocaleString("ru-RU")} ₽
              </p>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

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

  const { complianceFindings, breachFindings, riskSummary } = useMemo(() => {
    const complianceFindings = sortFindings(
      findings.filter((f) => f.type === "compliance"),
    );
    const breachFindings = sortFindings(
      findings.filter((f) => f.type === "security"),
    );
    const complianceTotal = sumCompliancePenalties(findings);
    const breachTotal = sumBreachPenalties(findings);
    let red = 0;
    let yellow = 0;
    for (const f of findings) {
      const c = resolveRiskColor(f);
      if (c === "red") red += 1;
      if (c === "yellow") yellow += 1;
    }
    return {
      complianceFindings,
      breachFindings,
      riskSummary: {
        red,
        yellow,
        complianceTotal,
        breachTotal,
        complianceColor: totalPenaltyColor(complianceTotal),
        breachColor: totalPenaltyColor(breachTotal),
      },
    };
  }, [findings]);

  const hasFindings = findings.length > 0;

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
        hasFindings ? (
          <>
            <div className={styles.totalsBlock} role="status">
              <div
                className={`${styles.totalRow} ${styles.totalRowFact} ${styles[`total_${riskSummary.complianceColor}`]}`}
              >
                <p className={styles.totalLabel}>
                  Факты: сумма штрафов по выявленным нарушениям 152-ФЗ
                </p>
                <p className={styles.totalAmount}>
                  {riskSummary.complianceTotal > 0
                    ? `до ${riskSummary.complianceTotal.toLocaleString("ru-RU")} ₽`
                    : "нарушений со штрафом не найдено"}
                </p>
              </div>
              <div
                className={`${styles.totalRow} ${styles.totalRowDivider} ${styles.totalRowForecast} ${styles[`total_${riskSummary.breachColor}`]}`}
              >
                <p className={styles.totalLabel}>
                  Прогноз: сумма штрафов при утечке или взломе
                </p>
                <p className={styles.totalAmount}>
                  {riskSummary.breachTotal > 0
                    ? `до ${riskSummary.breachTotal.toLocaleString("ru-RU")} ₽`
                    : "сценариев со штрафом не найдено"}
                </p>
              </div>
              <p className={styles.totalNote}>
                Верхняя строка — только зафиксированные нарушения. Нижняя — оценка
                при эксплуатации уязвимостей. Итог назначает орган.
              </p>
            </div>

            <section className={styles.sectionBlock} aria-labelledby="facts-heading">
              <h3 id="facts-heading" className={styles.sectionTitle}>
                Выявленные нарушения (факты)
              </h3>
              <p className={styles.sectionHint}>
                То, что сервис нашёл на проверенной странице по 152-ФЗ.
              </p>
              {complianceFindings.length > 0 ? (
                <FindingItems items={complianceFindings} />
              ) : (
                <p className={styles.sectionEmpty}>
                  По комплаенсу замечаний со штрафом не найдено.
                </p>
              )}
            </section>

            <section
              className={styles.sectionBlock}
              aria-labelledby="forecast-heading"
            >
              <h3 id="forecast-heading" className={styles.sectionTitle}>
                Прогноз при утечке или взломе
              </h3>
              <p className={styles.sectionHint}>
                Технические уязвимости и возможные штрафы, если их используют
                для компрометации или утечки данных.
              </p>
              {breachFindings.length > 0 ? (
                <FindingItems items={breachFindings} />
              ) : (
                <p className={styles.sectionEmpty}>
                  Технических сценариев со штрафом не найдено.
                </p>
              )}
            </section>
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