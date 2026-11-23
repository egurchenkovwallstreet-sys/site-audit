"use client";

import { useRouter } from "next/navigation";
import { ScanForm } from "./ScanForm";
import { ThemeToggle } from "./ThemeToggle";
import styles from "../app/home.module.css";

export function HomeClient() {
  const router = useRouter();

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <ThemeToggle />
      </header>
      <main className={styles.main}>
        <header className={styles.hero}>
          <h1 className={styles.title}>
            <span className={styles.titleLine}>Проверка сайта по 152‑ФЗ</span>
            <span className={styles.titleLineAccent}>онлайн · до 10 минут</span>
          </h1>
          <div
            className={styles.checkScope}
            aria-labelledby="check-scope-heading"
          >
            <p id="check-scope-heading" className={styles.checkScopeHeading}>
              Что проверяет сервис
            </p>
            <p className={styles.checkScopeText}>
              <span className={styles.checkScopeLead}>152‑ФЗ и технические сигналы</span>
              : политика ПДн, cookie, формы и согласия, реквизиты, иностранные
              SDK, техзаголовки и типовые риски утечки.{" "}
              <span className={styles.checkScopeLead}>168‑ФЗ</span>, SEO-разметка и
              углублённый техаудит (Nuclei). Без регистрации.
            </p>
          </div>
        </header>
        <div className={styles.panel}>
          <ScanForm
            onStarted={(id) => router.push(`/check/${id}`)}
          />
        </div>
        <p className={styles.scopeNote}>
          До 22 страниц сайта (вход, ссылки с неё, sitemap) и типовые адреса
          политики ПДн — без ручного обхода.
        </p>
        <p className={styles.disclaimer}>
          Сервис выполняет только безопасные проверки. Мы не эксплуатируем
          уязвимости.
        </p>
      </main>
    </div>
  );
}