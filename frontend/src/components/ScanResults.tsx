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

type ScanContext = {
  scope?: string;
  privacy_found?: boolean;
  privacy_source?: string | null;
  consent_found?: boolean;
  consent_source?: string | null;
  requested_url?: string;
  scanned_url?: string;
  used_fallback?: boolean;
  tried_urls?: string[];
  scanned_urls?: string[];
  pages_checked?: number;
  contact_emails?: string[];
};

type Scan = {
  id: number;
  target_url: string;
  status: string;
  context?: ScanContext | null;
};

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

const STEPS = [
  "Загружаем страницу",
  "Проверяем требования 152-ФЗ",
  "Оцениваем технические риски",
] as const;

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

function CheckContextPanel({ context }: { context: ScanContext }) {
  const complianceRan = (context.pages_checked ?? 0) > 0;
  return (
    <div className={styles.contextBlock}>
      <p className={styles.contextTitle}>Что проверили</p>
      {context.pages_checked != null && context.pages_checked > 0 ? (
        <p className={styles.contextMeta}>
          Проверено страниц: {context.pages_checked}
          {context.used_fallback && context.scanned_url
            ? ` (вход: ${context.scanned_url}, главная под антиботом)`
            : ""}
          .
        </p>
      ) : null}
      {context.scanned_urls && context.scanned_urls.length > 0 ? (
        <details className={styles.contextDetails}>
          <summary className={styles.contextMeta}>Список страниц</summary>
          <ul className={styles.contextList}>
            {context.scanned_urls.map((u) => (
              <li key={u}>
                <span className={styles.contextMeta}>{u}</span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      {context.scope ? (
        <p className={styles.contextMeta}>{context.scope}</p>
      ) : null}
      <ul className={styles.contextList}>
        <li>
          Политика ПДн:{" "}
          {!complianceRan ? (
            <span className={styles.contextWarn}>
              не проверяли (HTML сайта не прочитан)
            </span>
          ) : context.privacy_found ? (
            <span className={styles.contextOk}>найдена</span>
          ) : (
            <span className={styles.contextWarn}>не обнаружена</span>
          )}
          {context.privacy_source ? (
            <span className={styles.contextMeta}> — {context.privacy_source}</span>
          ) : null}
        </li>
        <li>
          Согласие / cookie:{" "}
          {!complianceRan ? (
            <span className={styles.contextWarn}>
              не проверяли (HTML сайта не прочитан)
            </span>
          ) : context.consent_found ? (
            <span className={styles.contextOk}>признаки есть</span>
          ) : (
            <span className={styles.contextWarn}>признаков нет</span>
          )}
          {context.consent_source ? (
            <span className={styles.contextMeta}> — {context.consent_source}</span>
          ) : null}
        </li>
      </ul>
    </div>
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
  const [progressStep, setProgressStep] = useState(0);

  useEffect(() => {
    let active = true;
    let tick = 0;

    async function poll() {
      const res = await fetch(`/api/scans/${scanId}`);
      if (!res.ok) return;
      const data: Scan = await res.json();
      if (!active) return;
      setScan(data);
      tick += 1;
      if (data.status === "pending") {
        setProgressStep(0);
      } else if (data.status === "running") {
        setProgressStep(Math.min(2, 1 + Math.floor(tick / 2)));
      }

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

  const { complianceFindings, breachFindings, accessFindings, riskSummary } =
    useMemo(() => {
    const accessFindings = findings.filter((f) => f.type === "access");
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
      accessFindings,
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

  const complianceRan = (scan?.context?.pages_checked ?? 0) > 0;
  const complianceClean =
    scan?.status === "completed" &&
    complianceRan &&
    complianceFindings.length === 0 &&
    accessFindings.length === 0;
  const noFindingsAtAll = findings.filter((f) => f.type !== "access").length === 0;

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
        <>
          <ol className={styles.steps}>
            {STEPS.map((label, index) => (
              <li
                key={label}
                className={
                  index <= progressStep
                    ? styles.stepActive
                    : styles.stepPending
                }
              >
                {label}
              </li>
            ))}
          </ol>
          <div className={styles.loader}>
            <div className={styles.loaderBar} />
          </div>
        </>
      ) : null}
      {accessFindings.length > 0 ? (
        <div className={styles.accessBanner} role="status">
          <p className={styles.accessTitle}>{accessFindings[0].title}</p>
          <p className={styles.itemMeta}>{accessFindings[0].description}</p>
        </div>
      ) : null}
      {scan?.status === "completed" && scan.context ? (
        <CheckContextPanel context={scan.context} />
      ) : null}
      {complianceClean ? (
        <div className={styles.successBanner}>
          По 152-ФЗ на проверенной странице нарушений со штрафом не найдено.
        </div>
      ) : null}
      {scan?.status === "completed" ? (
        noFindingsAtAll ? (
          <p className={styles.sectionEmpty}>
            Замечаний по 152-ФЗ и техническому прогнозу не найдено.
          </p>
        ) : (
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
                Каждый пункт привязан к норме 152-ФЗ и возможной статье КоАП;
                в описании указано, что именно искали на странице.
              </p>
              {complianceFindings.length > 0 ? (
                <FindingItems items={complianceFindings} />
              ) : (
                <p className={styles.sectionEmpty}>
                  {complianceRan
                    ? "По комплаенсу замечаний со штрафом не найдено."
                    : "Проверка 152-ФЗ по содержимому страниц не выполнялась (см. блок доступа выше). Штраф за отсутствие политики без анализа HTML не выставляется."}
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

            <section
              className={styles.sectionBlock}
              aria-labelledby="email-heading"
            >
              <h3 id="email-heading" className={styles.sectionTitle}>
                E-mail на сайте
              </h3>
              <p className={styles.sectionHint}>
                Смотрим открытые страницы, при возможности — политику ПДн и
                оферту (там часто указана почта оператора).
              </p>
              {scan.context?.contact_emails &&
              scan.context.contact_emails.length > 0 ? (
                <ul className={styles.emailList}>
                  {scan.context.contact_emails.map((email) => (
                    <li key={email}>
                      <a className={styles.emailLink} href={`mailto:${email}`}>
                        {email}
                      </a>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className={styles.sectionEmpty}>Почта не найдена.</p>
              )}
            </section>
          </>
        )
      ) : null}
    </section>
  );
}