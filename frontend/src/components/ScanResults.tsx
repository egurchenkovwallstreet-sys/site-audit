"use client";

import { useEffect, useMemo, useRef, useState } from "react";
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
  "Проверяем 152-ФЗ и 168-ФЗ",
  "SEO и технические риски",
] as const;

/** Ориентир 7–10 мин (бюджет скана на сервере до 10 мин). */
const ESTIMATE_MIN_MS = 7 * 60 * 1000;
const ESTIMATE_MAX_MS = 10 * 60 * 1000;
const TICK_MS = 100;
const COUNTDOWN_ZERO_MS = 45;

function initialEstimateMs(scanId: number): number {
  const spread = ESTIMATE_MAX_MS - ESTIMATE_MIN_MS;
  return ESTIMATE_MIN_MS + ((scanId * 2_654_435_761) >>> 0) % spread;
}

function formatCountdownTenths(remainingMs: number): string {
  const totalSec = Math.max(0, remainingMs) / 1000;
  const minutes = Math.floor(totalSec / 60);
  const seconds = Math.floor(totalSec % 60);
  const tenths = Math.floor((totalSec * 10) % 10);
  if (minutes > 0) {
    return `${minutes}:${seconds.toString().padStart(2, "0")}.${tenths}`;
  }
  return `${seconds}.${tenths}`;
}

function useScanCountdown(
  scanId: number,
  active: boolean,
  accelerating: boolean,
) {
  const deadlineRef = useRef<number | null>(null);
  const remainingRef = useRef(initialEstimateMs(scanId));
  const accelLambdaRef = useRef<number | null>(null);
  const [remainingMs, setRemainingMs] = useState(() => initialEstimateMs(scanId));
  const [finishing, setFinishing] = useState(false);
  const [zero, setZero] = useState(false);

  useEffect(() => {
    const est = initialEstimateMs(scanId);
    deadlineRef.current = Date.now() + est;
    remainingRef.current = est;
    accelLambdaRef.current = null;
    setRemainingMs(est);
    setFinishing(false);
    setZero(false);
  }, [scanId]);

  useEffect(() => {
    if (accelerating && accelLambdaRef.current === null) {
      const r0 = Math.max(remainingRef.current, COUNTDOWN_ZERO_MS + 20);
      const duration = Math.min(4_200, Math.max(1_400, r0 / 22));
      accelLambdaRef.current = Math.log(r0 / COUNTDOWN_ZERO_MS) / duration;
    }
    if (!accelerating) {
      accelLambdaRef.current = null;
    }
  }, [accelerating]);

  useEffect(() => {
    if (!active) {
      return;
    }

    const tick = () => {
      let left: number;
      if (accelerating && accelLambdaRef.current !== null) {
        const lambda = accelLambdaRef.current;
        left = remainingRef.current * Math.exp((-lambda * TICK_MS) / 1);
        if (left < COUNTDOWN_ZERO_MS) {
          left = 0;
          setZero(true);
        }
      } else {
        const end = deadlineRef.current ?? Date.now();
        left = Math.max(0, end - Date.now());
        if (left <= 0) {
          setZero(true);
        }
      }
      remainingRef.current = left;
      setRemainingMs(left);
      setFinishing(left <= 0 && !accelerating);
    };

    tick();
    const id = window.setInterval(tick, TICK_MS);
    return () => window.clearInterval(id);
  }, [active, accelerating]);

  useEffect(() => {
    if (!active && !accelerating) {
      remainingRef.current = 0;
      setRemainingMs(0);
    }
  }, [active, accelerating]);

  return { remainingMs, finishing, zero };
}

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

function EmailSendRow({ scanId, email }: { scanId: number; email: string }) {
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [errorText, setErrorText] = useState<string | null>(null);
  const [inboxUrl, setInboxUrl] = useState<string | null>(null);
  const [preview, setPreview] = useState<{
    subject: string;
    body: string;
    testInboxUrl: string | null;
  } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  async function showPreview() {
    setPreviewLoading(true);
    setErrorText(null);
    try {
      const q = encodeURIComponent(email);
      const res = await fetch(
        `/api/scans/${scanId}/outreach-email-preview?to_email=${q}`,
      );
      const data = (await res.json().catch(() => ({}))) as {
        detail?: string;
        subject?: string;
        body?: string;
        test_inbox_url?: string | null;
      };
      if (!res.ok || !data.subject || !data.body) {
        setErrorText(
          typeof data.detail === "string"
            ? data.detail
            : "Не удалось загрузить текст письма",
        );
        return;
      }
      setPreview({
        subject: data.subject,
        body: data.body,
        testInboxUrl: data.test_inbox_url ?? null,
      });
    } catch {
      setErrorText("Сеть недоступна");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function sendLetter() {
    if (state === "sending") return;
    setState("sending");
    setErrorText(null);
    try {
      const res = await fetch(`/api/scans/${scanId}/send-preview-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to_email: email }),
      });
      const data = (await res.json().catch(() => ({}))) as {
        detail?: string;
        test_inbox_url?: string | null;
      };
      if (!res.ok) {
        setState("error");
        setErrorText(
          typeof data.detail === "string"
            ? data.detail
            : "Не удалось отправить письмо",
        );
        return;
      }
      setInboxUrl(data.test_inbox_url ?? null);
      setState("sent");
    } catch {
      setState("error");
      setErrorText("Сеть недоступна");
    }
  }

  return (
    <li className={styles.emailRow}>
      <a className={styles.emailLink} href={`mailto:${email}`}>
        {email}
      </a>
      <div className={styles.emailActions}>
        <button
          type="button"
          className={styles.emailPreviewBtn}
          disabled={previewLoading}
          onClick={showPreview}
        >
          {previewLoading ? "Загрузка…" : "Текст письма"}
        </button>
        <button
          type="button"
          className={styles.emailSendBtn}
          disabled={state === "sending" || state === "sent"}
          onClick={sendLetter}
        >
          {state === "sending"
            ? "Отправляем…"
            : state === "sent"
              ? "Отправлено"
              : "Отправить письмо"}
        </button>
      </div>
      {preview ? (
        <div className={styles.emailPreviewBox}>
          <p className={styles.emailPreviewSubject}>
            <strong>Тема:</strong> {preview.subject}
          </p>
          <pre className={styles.emailPreviewBody}>{preview.body}</pre>
          {preview.testInboxUrl ? (
            <p className={styles.emailSendOk}>
              Тест без ящика: после «Отправить» смотрите письмо в{" "}
              <a
                href={preview.testInboxUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                тестовом почтовом ящике
              </a>
              .
            </p>
          ) : null}
        </div>
      ) : null}
      {state === "error" && errorText ? (
        <p className={styles.emailSendError} role="alert">
          {errorText}
        </p>
      ) : null}
      {state === "sent" ? (
        <p className={styles.emailSendOk}>
          {inboxUrl ? (
            <>
              Письмо в тестовом ящике (на {email} в интернет не ушло) —{" "}
              <a href={inboxUrl} target="_blank" rel="noopener noreferrer">
                открыть Mailpit
              </a>
            </>
          ) : (
            <>Письмо отправлено на {email}</>
          )}
        </p>
      ) : null}
    </li>
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
  const [accelerating, setAccelerating] = useState(false);
  const [countdownSettled, setCountdownSettled] = useState(false);

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

  useEffect(() => {
    setAccelerating(false);
    setCountdownSettled(false);
  }, [scanId]);

  const scanInFlight =
    !scan || scan.status === "pending" || scan.status === "running";
  const scanTerminal =
    scan?.status === "completed" || scan?.status === "failed";

  const countdownActive =
    !countdownSettled && (scanInFlight || accelerating);

  const { remainingMs, finishing, zero } = useScanCountdown(
    scanId,
    countdownActive,
    accelerating,
  );

  useEffect(() => {
    if (!scanTerminal || countdownSettled || accelerating) {
      return;
    }
    if (remainingMs > COUNTDOWN_ZERO_MS + 30) {
      setAccelerating(true);
    } else {
      setCountdownSettled(true);
    }
  }, [scanTerminal, remainingMs, countdownSettled, accelerating]);

  useEffect(() => {
    if (zero && accelerating) {
      setAccelerating(false);
      setCountdownSettled(true);
    }
  }, [zero, accelerating]);

  const busy = countdownActive;
  const revealOutcome = scanTerminal && countdownSettled;

  const {
    complianceFindings,
    seoFindings,
    breachFindings,
    accessFindings,
    riskSummary,
  } = useMemo(() => {
    const accessFindings = findings.filter((f) => f.type === "access");
    const complianceFindings = sortFindings(
      findings.filter((f) => f.type === "compliance"),
    );
    const seoFindings = sortFindings(
      findings.filter((f) => f.type === "seo"),
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
      seoFindings,
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
    revealOutcome &&
    scan?.status === "completed" &&
    complianceRan &&
    complianceFindings.length === 0 &&
    accessFindings.length === 0;
  const noFindingsAtAll =
    findings.filter((f) => f.type !== "access").length === 0;

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
        {accelerating && scan?.status === "completed"
          ? "Проверка завершена — собираем отчёт…"
          : scan
            ? (STATUS_TEXT[scan.status] ?? scan.status)
            : "Загрузка…"}
      </p>
      {busy ? (
        <>
          <div className={styles.countdownBlock} aria-live="polite">
            <p className={styles.countdownLabel}>
              {accelerating
                ? "Ускоряем отсчёт — отчёт уже готов"
                : finishing
                  ? "Проверка может занять до 10 минут — ждём сервер…"
                  : "Ориентир по времени (до 10 минут)"}
            </p>
            <p className={styles.countdownValue}>
              <span className={styles.countdownNumber}>
                {formatCountdownTenths(remainingMs)}
              </span>
              <span className={styles.countdownUnit}>
                {remainingMs >= 60_000 ? " мин" : " сек"}
              </span>
            </p>
          </div>
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
      {revealOutcome && accessFindings.length > 0 ? (
        <div className={styles.accessBanner} role="status">
          <p className={styles.accessTitle}>{accessFindings[0].title}</p>
          <p className={styles.itemMeta}>{accessFindings[0].description}</p>
        </div>
      ) : null}
      {revealOutcome && scan?.status === "completed" && scan.context ? (
        <CheckContextPanel context={scan.context} />
      ) : null}
      {complianceClean && revealOutcome ? (
        <div className={styles.successBanner}>
          По 152-ФЗ на проверенной странице нарушений со штрафом не найдено.
        </div>
      ) : null}
      {revealOutcome && scan?.status === "completed" ? (
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
              aria-labelledby="seo-heading"
            >
              <h3 id="seo-heading" className={styles.sectionTitle}>
                SEO и разметка
              </h3>
              <p className={styles.sectionHint}>
                Title, description, H1, robots/sitemap, canonical — по открытому
                HTML. Не гарантирует позиции в поиске.
              </p>
              {seoFindings.length > 0 ? (
                <FindingItems items={seoFindings} />
              ) : (
                <p className={styles.sectionEmpty}>
                  Критичных SEO-замечаний не найдено.
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
                оферту (там часто указана почта оператора). «Текст письма» —
                без отправки. «Отправить» кладёт копию в тестовый ящик Mailpit
                (без своего SMTP); смотрите ссылку после отправки.
              </p>
              {scan.context?.contact_emails &&
              scan.context.contact_emails.length > 0 ? (
                <ul className={styles.emailList}>
                  {scan.context.contact_emails.map((email) => (
                    <EmailSendRow key={email} scanId={scanId} email={email} />
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