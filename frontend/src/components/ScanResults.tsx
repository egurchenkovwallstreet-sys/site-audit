"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import styles from "./ScanResults.module.css";
import {
  resolveRiskColor,
  severityLabel,
  sortFindings,
  totalPenaltyColor,
  type RiskColor,
} from "@/lib/findingRisk";
import {
  breachSanctionTotals,
  complianceSanctionTotals,
  formatRubMax,
} from "@/lib/penaltySanctions";
import type { PenaltySanctions } from "@/lib/penaltySanctions";
import { PenaltySanctionsTable } from "./PenaltySanctionsTable";

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
  remediation?: string | null;
  sanctions?: PenaltySanctions | null;
};

const SEO_PRIORITY_LABEL: Record<string, string> = {
  critical: "Высокий приоритет",
  high: "Высокий приоритет",
  medium: "Средний приоритет",
  low: "Низкий приоритет",
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

function fmtTotal(n: number): string {
  return n > 0 ? formatRubMax(n) : "—";
}

function pluralRu(
  n: number,
  one: string,
  few: string,
  many: string,
): string {
  const nAbs = Math.abs(n);
  const mod10 = nAbs % 10;
  const mod100 = nAbs % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

function violationCountPhrase(n: number): string {
  const word = pluralRu(n, "нарушение", "нарушения", "нарушений");
  return `На вашем сайте выявлено ${n} ${word}, которые влекут к штрафам на сумму:`;
}

function vulnerabilityCountPhrase(n: number): string {
  const word = pluralRu(n, "уязвимость", "уязвимости", "уязвимостей");
  return `На данный момент мы нашли ${n} ${word} на вашем сайте, в случае взлома и утечки данных вам грозит штраф`;
}

function TotalsColumns({ ip, legal }: { ip: number; legal: number }) {
  return (
    <div className={styles.totalFigures} role="group" aria-label="Ориентиры штрафов">
      <div className={styles.totalFigure}>
        <span className={styles.totalFigureLabel}>ИП</span>
        <span className={styles.totalFigureValue}>{fmtTotal(ip)}</span>
      </div>
      <div className={styles.totalFigureDivider} aria-hidden />
      <div className={styles.totalFigure}>
        <span className={styles.totalFigureLabel}>Юрлицо</span>
        <span className={styles.totalFigureValue}>{fmtTotal(legal)}</span>
      </div>
    </div>
  );
}

function GrandTotalBlock({
  compliance,
  breach,
  breachCount,
  complianceCount,
}: {
  compliance: ReturnType<typeof complianceSanctionTotals>;
  breach: ReturnType<typeof breachSanctionTotals>;
  breachCount: number;
  complianceCount: number;
}) {
  const complianceEmpty = complianceCount === 0;
  const complianceColor = totalPenaltyColor(
    Math.max(compliance.ip, compliance.legal),
  );
  const breachColor =
    breachCount === 0 && breach.ip === 0 && breach.legal === 0
      ? "green"
      : totalPenaltyColor(Math.max(breach.ip, breach.legal));

  return (
  <div className={styles.grandTotal}>
    <p className={styles.grandTotalTitle}>Итого</p>
    <div
      className={`${styles.totalSection} ${styles[`totalSection_${complianceColor}`]}`}
    >
      {complianceEmpty ? (
        <p className={styles.totalSectionText}>
          На данный момент на сайте не выявлено нарушений в ходе проверки по
          статьям 152 и 168.
        </p>
      ) : (
        <>
          <p className={styles.totalSectionLeadUrgent}>
            {violationCountPhrase(complianceCount)}
          </p>
          <TotalsColumns ip={compliance.ip} legal={compliance.legal} />
        </>
      )}
    </div>
    <div
      className={`${styles.totalSection} ${styles[`totalSection_${breachColor}`]}`}
    >
      {breachCount === 0 ? (
        <p className={styles.totalSectionText}>
          Технических уязвимостей со штрафным риском не найдено.
        </p>
      ) : (
        <>
          <p className={styles.totalSectionText}>
            {vulnerabilityCountPhrase(breachCount)}
          </p>
          <TotalsColumns ip={breach.ip} legal={breach.legal} />
        </>
      )}
    </div>
  </div>
  );
}

function SeoRecommendationItems({ items }: { items: Finding[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <ul className={styles.list}>
      {items.map((f) => (
        <li key={f.id} className={`${styles.item} ${styles.itemSeo}`}>
          <div className={styles.itemHead}>
            <p className={styles.badge}>Рекомендация · SEO</p>
            <span className={styles.seoPill}>
              {SEO_PRIORITY_LABEL[f.severity] ?? "Рекомендация"}
            </span>
          </div>
          <p className={styles.itemTitle}>{f.title}</p>
          <p className={styles.itemMeta}>{f.description}</p>
          {f.remediation ? (
            <p className={styles.itemRemediation}>
              <span className={styles.itemRemediationLead}>Что сделать: </span>
              {f.remediation}
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

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
            {f.sanctions ? (
              <PenaltySanctionsTable sanctions={f.sanctions} compact />
            ) : f.max_penalty != null ? (
              <p
                className={`${styles.penalty} ${styles[`penalty_${risk}`]}`}
              >
                {isForecast
                  ? "Возможный штраф при утечке или взломе через эту уязвимость: "
                  : "Ориентир штрафа: "}
                {formatRubMax(f.max_penalty)}
              </p>
            ) : null}
          </li>
        );
      })}
    </ul>
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
  targetUrl?: string;
  onReset: () => void;
}) {
  const [scan, setScan] = useState<Scan | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [shareFeedback, setShareFeedback] = useState<"idle" | "copied">("idle");
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

  const { complianceFindings, seoFindings, breachFindings, accessFindings } =
    useMemo(() => {
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
      return {
        accessFindings,
        complianceFindings,
        seoFindings,
        breachFindings,
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

  const complianceSanctions = useMemo(
    () => complianceSanctionTotals(findings),
    [findings],
  );
  const breachSanctions = useMemo(
    () => breachSanctionTotals(findings),
    [findings],
  );

  const displayUrl = targetUrl || scan?.target_url || "…";

  async function shareResult() {
    const url = window.location.href;
    const title = "Результат проверки сайта";
    if (typeof navigator.share === "function") {
      try {
        await navigator.share({ title, url });
        return;
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
      }
    }
    try {
      await navigator.clipboard.writeText(url);
      setShareFeedback("copied");
      window.setTimeout(() => setShareFeedback("idle"), 2500);
    } catch {
      /* clipboard denied */
    }
  }

  return (
    <section className={styles.wrap}>
      <div className={styles.head}>
        <h2 className={styles.title}>Результат</h2>
        <div className={styles.headActions}>
          <button
            type="button"
            className={styles.headBtnShare}
            onClick={shareResult}
          >
            {shareFeedback === "copied"
              ? "Ссылка скопирована"
              : "Поделиться результатом"}
          </button>
          <button
            type="button"
            className={styles.headBtnHome}
            onClick={onReset}
          >
            На главную
          </button>
        </div>
      </div>
      <p className={styles.url}>{displayUrl}</p>
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
              <GrandTotalBlock
                compliance={complianceSanctions}
                breach={breachSanctions}
                breachCount={breachFindings.length}
                complianceCount={complianceFindings.length}
              />
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
                Рекомендации по title, description, H1, robots/sitemap,
                canonical — по открытому HTML. Без штрафов и юридических
                рисков, не гарантирует позиции в поиске.
              </p>
              {seoFindings.length > 0 ? (
                <SeoRecommendationItems items={seoFindings} />
              ) : (
                <p className={styles.sectionEmpty}>
                  Рекомендаций по SEO не найдено.
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