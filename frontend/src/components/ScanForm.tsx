"use client";

import { FormEvent, useState } from "react";
import styles from "./ScanForm.module.css";

export function ScanForm({
  onStarted,
}: {
  onStarted: (scanId: number, url: string) => void;
}) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const trimmed = url.trim();
    if (!trimmed) {
      setError("Вставьте ссылку на сайт.");
      return;
    }
    if (!/^https?:\/\//i.test(trimmed)) {
      setError("Ссылка должна начинаться с http:// или https://");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/scans", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_url: trimmed }),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        setError(
          typeof detail === "string"
            ? detail
            : "Не удалось запустить проверку. Проверьте ссылку.",
        );
        return;
      }
      onStarted(data.id, trimmed);
    } catch {
      setError("Сервер недоступен. Попробуйте позже.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={onSubmit}>
      <label className={styles.label} htmlFor="site-url">
        Ссылка на сайт
      </label>
      <div className={styles.row}>
        <input
          id="site-url"
          className={styles.input}
          type="url"
          inputMode="url"
          placeholder="https://ваш-сайт.ru"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={loading}
          autoComplete="url"
        />
        <button className={styles.button} type="submit" disabled={loading}>
          {loading ? "Запуск…" : "Проверить"}
        </button>
      </div>
      {error ? <p className={styles.error}>{error}</p> : null}
      <p className={styles.hint}>Бесплатно. Полный отчёт — от 990 ₽.</p>
    </form>
  );
}