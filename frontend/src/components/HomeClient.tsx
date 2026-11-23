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
          <p className={styles.eyebrow}>152-ФЗ + технические сигналы</p>
          <h1 className={styles.title}>
            <span className={styles.titleLine}>Проверка сайта по 152‑ФЗ</span>
            <span className={styles.titleLineAccent}>онлайн · до 10 минут</span>
          </h1>
          <p className={styles.subtitle}>
            168‑ФЗ, cookie, формы, SEO-разметка и технические риски — без
            регистрации
          </p>
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