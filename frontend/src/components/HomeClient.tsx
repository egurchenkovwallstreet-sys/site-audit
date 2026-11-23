"use client";

import { useRouter } from "next/navigation";
import { HomePitch } from "./HomePitch";
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
        </header>
        <HomePitch />
        <div className={styles.panel}>
          <ScanForm
            onStarted={(id) => router.push(`/check/${id}`)}
          />
        </div>
        <p className={styles.scopeNote}>
          152‑ФЗ, 168‑ФЗ, SEO и техаудит (Nuclei). До 22 страниц (вход, ссылки,
          sitemap) и типовые адреса политики — без регистрации и ручного обхода.
        </p>
        <p className={styles.disclaimer}>
          Сервис выполняет только безопасные проверки. Мы не эксплуатируем
          уязвимости.
        </p>
      </main>
    </div>
  );
}