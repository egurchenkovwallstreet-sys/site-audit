"use client";

import { useCallback, useEffect, useState } from "react";
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
    payments_all_count: number;
    payments_all_sum_rub: number;
  };
  by_status: { status: string; count: number }[];
  top_target_urls: { url: string; count: number }[];
  new_ips: { client_ip: string; scans_in_period: number }[];
  payments_by_tier: { tier: string; count: number; amount_rub: number }[];
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

function fmtDuration(sec: number | null): string {
  if (sec == null) return "—";
  const m = Math.round(sec / 60);
  if (m < 60) return `~${m} мин`;
  return `~${Math.floor(m / 60)} ч ${m % 60} мин`;
}

function fmtRub(n: number): string {
  return `${n.toLocaleString("ru-RU")} ₽`;
}

export function AdminDashboardClient() {
  const router = useRouter();
  const [period, setPeriod] = useState<PeriodKey>("day");
  const [stats, setStats] = useState<StatsPayload | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [incidents, setIncidents] = useState<AdminIncident[]>([]);
  const [incidentsError, setIncidentsError] = useState<string | null>(null);

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
    const t = setInterval(() => void loadIncidents(), 30_000);
    return () => clearInterval(t);
  }, [period, load, loadIncidents]);

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

  return (
    <main className={styles.wrap}>
      <div className={styles.toolbar}>
        <h1 className={styles.title}>Статистика site-audit</h1>
        <div className={styles.toolbarRight}>
          {email ? (
            <span className={styles.muted}>{email}</span>
          ) : null}
          <button type="button" className={styles.ghostBtn} onClick={() => void logout()}>
            Выйти
          </button>
        </div>
      </div>

      <section className={styles.incidentPanel} aria-labelledby="incidents-h">
        <h2 id="incidents-h" className={styles.h2}>
          Сбои и долгие проверки
          {incidents.filter((i) => !i.resolved).length > 0
            ? ` (${incidents.filter((i) => !i.resolved).length} активных)`
            : ""}
        </h2>
        <p className={styles.muted}>
          Журнал пополняется при таймаутах 20 мин, автоповторах и сбоях после выката. Старые
          проверки до этого момента сюда не переносятся автоматически.
        </p>
        {incidentsError ? (
          <p className={styles.error} role="alert">
            {incidentsError}
          </p>
        ) : null}
        {incidents.length === 0 && !incidentsError ? (
          <>
            <p className={styles.muted}>Активных и недавних инцидентов пока нет.</p>
            <button
              type="button"
              className={styles.resolveBtn}
              onClick={() => void backfillFailed()}
            >
              Подтянуть старые failed из базы
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
              <pre
                className={styles.muted}
                style={{ fontSize: "0.75rem", whiteSpace: "pre-wrap" }}
              >
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
      </section>

      <div className={styles.tabs}>
        {(Object.keys(PERIOD_LABELS) as PeriodKey[]).map((key) => (
          <button
            key={key}
            type="button"
            className={
              period === key ? `${styles.tab} ${styles.tabActive}` : styles.tab
            }
            onClick={() => setPeriod(key)}
          >
            {PERIOD_LABELS[key]}
          </button>
        ))}
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
          <section className={styles.grid}>
            <StatCard label="Создано проверок" value={s?.scans_created ?? 0} />
            <StatCard label="Завершено" value={s?.scans_completed ?? 0} />
            <StatCard label="С ошибкой" value={s?.scans_failed ?? 0} />
            <StatCard
              label="Успешность"
              value={
                s?.success_rate_pct != null ? `${s.success_rate_pct}%` : "—"
              }
            />
            <StatCard label="В очереди сейчас" value={s?.queued_now ?? 0} />
            <StatCard label="Идёт сейчас" value={s?.running_now ?? 0} />
            <StatCard label="Уникальных IP" value={s?.unique_ips ?? 0} />
            <StatCard
              label={
                stats.period === "all" ? "Уникальных IP (всего)" : "Новых IP"
              }
              value={s?.new_unique_ips ?? 0}
            />
            <StatCard
              label={
                stats.period === "all"
                  ? "Проверок с IP"
                  : "Проверок с новых IP"
              }
              value={s?.scans_from_new_ips ?? 0}
            />
            <StatCard
              label="Оплат отчётов (успешно)"
              value={s?.payments_succeeded_count ?? 0}
            />
            <StatCard
              label="Сумма оплат (успешно)"
              value={fmtRub(s?.payments_succeeded_sum_rub ?? 0)}
            />
            <StatCard
              label="Среднее время"
              value={fmtDuration(s?.avg_completion_sec ?? null)}
            />
            <StatCard label="Находок (findings)" value={s?.findings_total ?? 0} />
          </section>

          <section className={styles.split}>
            <div className={styles.panel}>
              <h2 className={styles.h2}>
                {stats.period === "all"
                  ? "IP по числу проверок"
                  : "Новые IP (первая проверка за период)"}
              </h2>
              {stats.new_ips.length === 0 ? (
                <p className={styles.muted}>Нет данных по IP.</p>
              ) : (
                <table className={styles.table}>
                  <tbody>
                    {stats.new_ips.map((row) => (
                      <tr key={row.client_ip}>
                        <td className={styles.urlCell}>{row.client_ip}</td>
                        <td className={styles.num}>{row.scans_in_period}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div className={styles.panel}>
              <h2 className={styles.h2}>Оплаты отчётов</h2>
              <p className={styles.muted}>
                Успешно: {s?.payments_succeeded_count ?? 0} на{" "}
                {fmtRub(s?.payments_succeeded_sum_rub ?? 0)}
                {(s?.payments_pending_count ?? 0) > 0
                  ? ` · в ожидании: ${s?.payments_pending_count} (${fmtRub(s?.payments_pending_sum_rub ?? 0)})`
                  : ""}
              </p>
              {stats.payments_by_tier.length > 0 ? (
                <>
                  <p className={styles.muted}>По тарифу (успешные):</p>
                  <table className={styles.table}>
                    <tbody>
                      {stats.payments_by_tier.map((row) => (
                        <tr key={row.tier}>
                          <td>{row.tier}</td>
                          <td className={styles.num}>
                            {row.count} · {fmtRub(row.amount_rub)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              ) : (
                <p className={styles.muted}>
                  Успешных оплат за период нет (ЮKassa подключится в фазе B).
                </p>
              )}
              {stats.payments_by_status.length > 0 ? (
                <table className={styles.table}>
                  <tbody>
                    {stats.payments_by_status.map((row) => (
                      <tr key={row.status}>
                        <td>{row.status}</td>
                        <td className={styles.num}>
                          {row.count} · {fmtRub(row.amount_rub)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : null}
            </div>
          </section>

          <section className={styles.panel}>
            <h2 className={styles.h2}>По статусам</h2>
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
          </section>

          <section className={styles.panel}>
            <h2 className={styles.h2}>Топ URL</h2>
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
          </section>

          <section className={styles.split}>
            <div className={styles.panel}>
              <h2 className={styles.h2}>Findings по типу</h2>
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
            <div className={styles.panel}>
              <h2 className={styles.h2}>Findings по severity</h2>
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
          </section>
        </>
      )}
    </main>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className={styles.statCard}>
      <p className={styles.statLabel}>{label}</p>
      <p className={styles.statValue}>{value}</p>
    </div>
  );
}