"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import styles from "./admin.module.css";

type PeriodKey = "day" | "week" | "month" | "all";

type AdminIncident = {
  id: number;
  scan_id: number | null;
  created_at: string | null;
  kind: string;
  severity: string;
  title: string;
  target_url: string;
  detail: unknown;
  resolved: boolean;
};

type StatsPayload = {
  period: string;
  summary: {
    scans_created: number;
    scans_completed: number;
    scans_failed: number;
    queued_now: number;
    running_now: number;
    success_rate_pct: number | null;
    unique_ips: number;
    new_unique_ips: number;
    scans_from_new_ips: number;
    avg_completion_sec: number | null;
    findings_total: number;
    payments_succeeded_count: number;
    payments_succeeded_sum_rub: number;
    payments_pending_count: number;
    payments_pending_sum_rub: number;
    payments_short_count: number;
    payments_short_sum_rub: number;
    payments_extended_count: number;
    payments_extended_sum_rub: number;
    queue_max_waiting: number;
    queue_alert_threshold: number;
    queue_over_threshold_samples: number;
    max_concurrent_scans: number;
  };
  queue_peaks: {
    recorded_at: string | null;
    queued_count: number;
    running_count: number;
    max_concurrent: number;
  }[];
  by_status: { status: string; count: number }[];
  top_target_urls: { url: string; count: number }[];
  new_ips: { client_ip: string; scans_in_period: number }[];
  payments_by_report: {
    tier: string;
    label: string;
    list_price_rub: number;
    count: number;
    amount_rub: number;
  }[];
  payments_by_status: { status: string; count: number; amount_rub: number }[];
  findings_by_type: { type: string; count: number }[];
  findings_by_severity: { severity: string; count: number }[];
};

const PERIOD_LABELS: Record<PeriodKey, string> = {
  day: "Сутки",
  week: "Неделя",
  month: "Месяц",
  all: "Всего",
};

const PERIOD_HINT: Record<PeriodKey, string> = {
  day: "последние 24 часа",
  week: "последние 7 дней",
  month: "последние 30 дней",
  all: "за всё время",
};

function fmtDuration(sec: number | null): string {
  if (sec == null) return "—";
  const m = Math.round(sec / 60);
  if (m < 60) return `~${m} мин`;
  return `~${Math.floor(m / 60)} ч ${m % 60} мин`;
}

function fmtRub(n: number): string {
  return `${n.toLocaleString("ru-RU")} ₽`;
}

function Section({
  id,
  title,
  hint,
  children,
  variant,
}: {
  id?: string;
  title: string;
  hint?: string;
  children: ReactNode;
  variant?: "default" | "alert";
}) {
  const cls =
    variant === "alert"
      ? `${styles.sectionBlock} ${styles.sectionAlert}`
      : styles.sectionBlock;
  return (
    <section className={cls} aria-labelledby={id}>
      <div className={styles.sectionHead}>
        <h2 id={id} className={styles.sectionTitle}>
          {title}
        </h2>
        {hint ? <p className={styles.sectionHint}>{hint}</p> : null}
      </div>
      {children}
    </section>
  );
}

function Kpi({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <div className={styles.kpi}>
      <span className={styles.kpiLabel}>{label}</span>
      <span className={styles.kpiValue}>{value}</span>
      {sub ? <span className={styles.kpiSub}>{sub}</span> : null}
    </div>
  );
}

export function AdminDashboardClient() {
  const router = useRouter();
  const [period, setPeriod] = useState<PeriodKey>("day");
  const [stats, setStats] = useState<StatsPayload | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [incidents, setIncidents] = useState<AdminIncident[]>([]);
  const [incidentsError, setIncidentsError] = useState<string | null>(null);
  const [queueLive, setQueueLive] = useState<{
    queued_now: number;
    running_now: number;
    max_concurrent: number;
    alert_threshold: number;
  } | null>(null);
  const [queueHistory, setQueueHistory] = useState<
    { recorded_at: string | null; queued_count: number; running_count: number }[]
  >([]);

  const loadQueueLive = useCallback(async () => {
    const res = await fetch("/api/admin/queue/live", { credentials: "include" });
    if (res.ok) setQueueLive(await res.json());
  }, []);

  const loadQueueHistory = useCallback(async (p: PeriodKey) => {
    const res = await fetch(
      `/api/admin/queue/history?period=${p}&limit=80&high_load_only=false`,
      { credentials: "include" },
    );
    if (res.ok) {
      const data = await res.json();
      setQueueHistory(data.items ?? []);
    }
  }, []);

  const loadIncidents = useCallback(async () => {
    setIncidentsError(null);
    const res = await fetch("/api/admin/incidents?limit=30&unresolved_only=false", {
      credentials: "include",
    });
    if (!res.ok) {
      setIncidentsError(
        res.status === 401
          ? "Сессия истекла — обновите страницу или войдите снова."
          : `Не удалось загрузить инциденты (${res.status}).`,
      );
      return;
    }
    const data = await res.json();
    setIncidents(data.items ?? []);
  }, []);

  const load = useCallback(async (p: PeriodKey) => {
    setError(null);
    const me = await fetch("/api/admin/me", { credentials: "include" });
    if (!me.ok) {
      router.replace("/admin/login");
      return;
    }
    const meData = await me.json();
    setEmail(meData.email ?? null);

    const res = await fetch(`/api/admin/stats?period=${p}`, {
      credentials: "include",
    });
    if (!res.ok) {
      setError("Не удалось загрузить статистику");
      return;
    }
    setStats(await res.json());
  }, [router]);

  useEffect(() => {
    void load(period);
    void loadIncidents();
    void loadQueueLive();
    void loadQueueHistory(period);
    const t1 = setInterval(() => void loadIncidents(), 30_000);
    const t2 = setInterval(() => void loadQueueLive(), 15_000);
    return () => {
      clearInterval(t1);
      clearInterval(t2);
    };
  }, [period, load, loadIncidents, loadQueueLive, loadQueueHistory]);

  async function resolveIncident(id: number) {
    await fetch(`/api/admin/incidents/${id}/resolve`, {
      method: "POST",
      credentials: "include",
    });
    void loadIncidents();
  }

  async function backfillFailed() {
    setIncidentsError(null);
    const res = await fetch("/api/admin/incidents/backfill-failed?limit=40", {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) {
      setIncidentsError(`Импорт не удался (${res.status}).`);
      return;
    }
    void loadIncidents();
  }

  function severityClass(sev: string): string {
    if (sev === "critical") return styles.sevCritical;
    if (sev === "warn") return styles.sevWarn;
    return styles.sevInfo;
  }

  async function logout() {
    await fetch("/api/admin/logout", {
      method: "POST",
      credentials: "include",
    });
    router.replace("/admin/login");
  }

  const s = stats?.summary;
  const activeIncidents = incidents.filter((i) => !i.resolved);
  const alertThreshold =
    queueLive?.alert_threshold ?? s?.queue_alert_threshold ?? 5;
  const queuedNow = queueLive?.queued_now ?? s?.queued_now ?? 0;
  const queueAlert = queuedNow >= alertThreshold;

  return (
    <main className={styles.wrap}>
      {queueAlert ? (
        <motion aria-live="polite" className={styles.queueAlert}>
          <strong>Высокая очередь:</strong> сейчас в ожидании{" "}
          <strong>{queuedNow}</strong> проверок (порог {alertThreshold}). Смотрите блок
          «Очередь» и журнал сбоев — возможно, нужны мощности.
        </motion>
      ) : null}
      <header className={styles.toolbar}>
        <div>
          <h1 className={styles.title}>Админ-кабинет</h1>
          <p className={styles.headerSub}>Статистика проверок и оплат audit152fz.online</p>
        </div>
        <div className={styles.toolbarRight}>
          {email ? <span className={styles.muted}>{email}</span> : null}
          <button type="button" className={styles.ghostBtn} onClick={() => void logout()}>
            Выйти
          </button>
        </div>
      </header>

      <div className={styles.periodBar}>
        <span className={styles.periodBarLabel}>Период:</span>
        <div className={styles.tabs}>
          {(Object.keys(PERIOD_LABELS) as PeriodKey[]).map((key) => (
            <button
              key={key}
              type="button"
              className={period === key ? `${styles.tab} ${styles.tabActive}` : styles.tab}
              onClick={() => setPeriod(key)}
            >
              {PERIOD_LABELS[key]}
            </button>
          ))}
        </div>
        <span className={styles.periodHint}>{PERIOD_HINT[period]}</span>
      </div>

      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}

      {!stats ? (
        <p className={styles.muted}>Загрузка…</p>
      ) : (
        <>
          <Section
            id="sec-scans"
            title="1. Проверки сайтов"
            hint={`Итоги за выбранный период (${PERIOD_HINT[period]})`}
          >
            <div className={styles.kpiRow}>
              <Kpi label="Запущено" value={s?.scans_created ?? 0} />
              <Kpi label="Завершено" value={s?.scans_completed ?? 0} />
              <Kpi label="С ошибкой" value={s?.scans_failed ?? 0} />
              <Kpi
                label="Доля завершённых"
                value={s?.success_rate_pct != null ? `${s.success_rate_pct}%` : "—"}
                sub="от числа запущенных"
              />
              <Kpi label="Среднее время" value={fmtDuration(s?.avg_completion_sec ?? null)} />
              <Kpi label="Находок (findings)" value={s?.findings_total ?? 0} />
            </div>
          </Section>

          <Section
            id="sec-live"
            title="2. Очередь проверок"
            hint="Live ~15 с. История — снимки каждые 30 с в БД. Уведомление в журнале при ≥ порога."
          >
            <div className={styles.kpiRow}>
              <Kpi
                label="Сейчас в очереди"
                value={queueLive?.queued_now ?? s?.queued_now ?? 0}
                sub="ожидают старт"
              />
              <Kpi
                label="Сейчас выполняется"
                value={queueLive?.running_now ?? s?.running_now ?? 0}
                sub={`макс. параллельно ${queueLive?.max_concurrent ?? s?.max_concurrent_scans ?? 2}`}
              />
              <Kpi
                label="Макс. очередь за период"
                value={s?.queue_max_waiting ?? 0}
                sub="пик ожидающих"
              />
              <Kpi
                label={`Снимков при ≥${s?.queue_alert_threshold ?? 5} в очереди`}
                value={s?.queue_over_threshold_samples ?? 0}
                sub="за выбранный период"
              />
            </div>
            {stats.queue_peaks.length > 0 ? (
              <>
                <h3 className={styles.h3}>Пики очереди за период</h3>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th className={styles.thLeft}>Время (UTC)</th>
                      <th className={styles.thRight}>В очереди</th>
                      <th className={styles.thRight}>Выполнялось</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.queue_peaks.map((row) => (
                      <tr key={row.recorded_at ?? row.queued_count}>
                        <td className={styles.urlCell}>{row.recorded_at ?? "—"}</td>
                        <td className={styles.num}>{row.queued_count}</td>
                        <td className={styles.num}>{row.running_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            ) : (
              <p className={styles.emptyNote}>
                Пиков за период пока нет — история накапливается после выката (~30 с на точку).
              </p>
            )}
            {queueHistory.length > 0 ? (
              <>
                <h3 className={styles.h3}>Последние снимки (хронология)</h3>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th className={styles.thLeft}>Время</th>
                      <th className={styles.thRight}>Очередь</th>
                      <th className={styles.thRight}>Running</th>
                    </tr>
                  </thead>
                  <tbody>
                    {queueHistory.slice(0, 25).map((row) => (
                      <tr key={row.recorded_at ?? `${row.queued_count}`}>
                        <td className={styles.urlCell}>{row.recorded_at ?? "—"}</td>
                        <td className={styles.num}>{row.queued_count}</td>
                        <td className={styles.num}>{row.running_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            ) : null}
          </Section>

          <Section
            id="sec-visitors"
            title="3. Посетители (IP)"
            hint={
              stats.period === "all"
                ? "Уникальные адреса и таблица по числу проверок"
                : "Новый IP — впервые зашёл на проверку в этом периоде"
            }
          >
            <div className={styles.kpiRow}>
              <Kpi label="Уникальных IP за период" value={s?.unique_ips ?? 0} />
              <Kpi
                label={stats.period === "all" ? "Всего уникальных" : "Новых IP"}
                value={s?.new_unique_ips ?? 0}
              />
              <Kpi
                label={
                  stats.period === "all" ? "Проверок с указанным IP" : "Проверок с новых IP"
                }
                value={s?.scans_from_new_ips ?? 0}
              />
            </div>
            {stats.new_ips.length > 0 ? (
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th className={styles.thLeft}>IP</th>
                    <th className={styles.thRight}>Проверок</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.new_ips.map((row) => (
                    <tr key={row.client_ip}>
                      <td className={styles.urlCell}>{row.client_ip}</td>
                      <td className={styles.num}>{row.scans_in_period}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className={styles.emptyNote}>Нет данных по IP за период.</p>
            )}
          </Section>

          <Section
            id="sec-payments"
            title="4. Оплаты отчётов"
            hint="Успешные платежи (ЮKassa). Суммы — фактически оплаченные рубли."
          >
            <div className={styles.paymentTotal}>
              <span>Итого успешно:</span>
              <strong>
                {s?.payments_succeeded_count ?? 0} оплат · {fmtRub(s?.payments_succeeded_sum_rub ?? 0)}
              </strong>
              {(s?.payments_pending_count ?? 0) > 0 ? (
                <span className={styles.muted}>
                  {" "}
                  · в ожидании: {s?.payments_pending_count} (
                  {fmtRub(s?.payments_pending_sum_rub ?? 0)})
                </span>
              ) : null}
            </div>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.thLeft}>Вид отчёта</th>
                  <th className={styles.thRight}>Цена</th>
                  <th className={styles.thRight}>Оплат</th>
                  <th className={styles.thRight}>Сумма</th>
                </tr>
              </thead>
              <tbody>
                {(stats.payments_by_report ?? []).map((row) => (
                  <tr key={row.tier}>
                    <td>{row.label}</td>
                    <td className={styles.num}>{fmtRub(row.list_price_rub)}</td>
                    <td className={styles.num}>{row.count}</td>
                    <td className={styles.num}>{fmtRub(row.amount_rub)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {(s?.payments_succeeded_count ?? 0) === 0 ? (
              <p className={styles.emptyNote}>Оплат пока нет — появятся после подключения ЮKassa.</p>
            ) : null}
          </Section>

          <Section
            id="sec-details"
            title="5. Детализация"
            hint="Статусы, популярные URL и состав findings"
          >
            <div className={styles.detailsGrid}>
              <div>
                <h3 className={styles.h3}>Статусы проверок</h3>
                <table className={styles.table}>
                  <tbody>
                    {stats.by_status.map((row) => (
                      <tr key={row.status}>
                        <td>{row.status}</td>
                        <td className={styles.num}>{row.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div>
                <h3 className={styles.h3}>Топ проверяемых URL</h3>
                <table className={styles.table}>
                  <tbody>
                    {stats.top_target_urls.map((row) => (
                      <tr key={row.url}>
                        <td className={styles.urlCell}>{row.url}</td>
                        <td className={styles.num}>{row.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div>
                <h3 className={styles.h3}>Findings по типу</h3>
                <table className={styles.table}>
                  <tbody>
                    {stats.findings_by_type.map((row) => (
                      <tr key={row.type}>
                        <td>{row.type}</td>
                        <td className={styles.num}>{row.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div>
                <h3 className={styles.h3}>Findings по severity</h3>
                <table className={styles.table}>
                  <tbody>
                    {stats.findings_by_severity.map((row) => (
                      <tr key={row.severity}>
                        <td>{row.severity}</td>
                        <td className={styles.num}>{row.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </Section>
        </>
      )}

      <Section
        id="sec-incidents"
        title="6. Журнал сбоев и долгих проверок"
        hint="Обновление ~30 с. Разбираем вместе по scan #."
        variant={activeIncidents.length > 0 ? "alert" : "default"}
      >
        {incidentsError ? (
          <p className={styles.error} role="alert">
            {incidentsError}
          </p>
        ) : null}
        {activeIncidents.length === 0 && incidents.length === 0 && !incidentsError ? (
          <>
            <p className={styles.emptyNote}>Записей нет. Новые появятся при таймауте 20 мин и сбоях.</p>
            <button type="button" className={styles.resolveBtn} onClick={() => void backfillFailed()}>
              Импортировать старые failed из БД
            </button>
          </>
        ) : null}
        {incidents.map((inc) => (
          <div key={inc.id} className={styles.incidentItem}>
            <p className={severityClass(inc.severity)}>
              <strong>{inc.title}</strong> — {inc.target_url}
              {inc.resolved ? " · разобрано" : ""}
            </p>
            <p className={styles.muted}>
              {inc.kind}
              {inc.scan_id != null ? ` · scan #${inc.scan_id}` : ""}
              {inc.created_at ? ` · ${inc.created_at}` : ""}
            </p>
            {inc.detail != null ? (
              <pre className={styles.detailPre}>
                {typeof inc.detail === "string"
                  ? inc.detail
                  : JSON.stringify(inc.detail, null, 2)}
              </pre>
            ) : null}
            {!inc.resolved ? (
              <button
                type="button"
                className={styles.resolveBtn}
                onClick={() => void resolveIncident(inc.id)}
              >
                Отметить разобрано
              </button>
            ) : null}
          </div>
        ))}
      </Section>
    </main>
  );
}

function motion({
  className,
  children,
  ...rest
}: {
  className?: string;
  children: ReactNode;
  "aria-live"?: "polite" | "assertive" | "off";
}) {
  return (
    <div className={className} {...rest}>
      {children}
    </div>
  );
}