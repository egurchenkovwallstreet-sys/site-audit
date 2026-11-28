"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./admin.module.css";

type PeriodKey = "day" | "week" | "month" | "all";

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
    avg_completion_sec: number | null;
    findings_total: number;
  };
  by_status: { status: string; count: number }[];
  top_target_urls: { url: string; count: number }[];
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

export function AdminDashboardClient() {
  const router = useRouter();
  const [period, setPeriod] = useState<PeriodKey>("day");
  const [stats, setStats] = useState<StatsPayload | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
  }, [period, load]);

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
              label="Среднее время"
              value={fmtDuration(s?.avg_completion_sec ?? null)}
            />
            <StatCard label="Находок (findings)" value={s?.findings_total ?? 0} />
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