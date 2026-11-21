"use client";

import { useState } from "react";
import { ScanForm } from "./ScanForm";
import { ScanResults } from "./ScanResults";
import { ThemeToggle } from "./ThemeToggle";
import styles from "../app/home.module.css";

export function HomeClient() {
  const [active, setActive] = useState<{ id: number; url: string } | null>(null);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <ThemeToggle />
      </header>
      <main className={styles.main}>
        <header className={styles.hero}>
          <p className={styles.eyebrow}>152-ФЗ + технические сигналы</p>
          <h1 className={styles.title}>
            <span className={styles.titleLine}>Проверьте свой сайт</span>
            <span className={styles.titleLineAccent}>за 5 минут</span>
          </h1>
          <p className={styles.subtitle}>
            Уязвимости и риски штрафов по 152-ФЗ
          </p>
        </header>
        <div className={styles.panel}>
          {!active ? (
            <ScanForm
              onStarted={(id, url) => setActive({ id, url })}
            />
          ) : null}
          {active ? (
            <ScanResults
              scanId={active.id}
              targetUrl={active.url}
              onReset={() => setActive(null)}
            />
          ) : null}
        </div>
        <p className={styles.subscription}>
          Нужно проверять много сайтов? Подписка 1490 ₽/мес — расширенный
          отчёт 990 ₽ вместо 1990 ₽.
        </p>
        <p className={styles.disclaimer}>
          Сервис выполняет только безопасные проверки. Мы не эксплуатируем
          уязвимости.
        </p>
      </main>
    </div>
  );
}