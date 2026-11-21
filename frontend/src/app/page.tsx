import { ScanForm } from "@/components/ScanForm";
import { ThemeToggle } from "@/components/ThemeToggle";
import styles from "./home.module.css";

export default function Home() {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <ThemeToggle />
      </header>
      <main className={styles.main}>
        <p className={styles.eyebrow}>152-ФЗ + технические сигналы</p>
        <h1 className={styles.title}>Проверьте свой сайт за 5 минут</h1>
        <p className={styles.subtitle}>
          Уязвимости и риски штрафов по 152-ФЗ. Без ручной работы.
        </p>
        <div className={styles.panel}>
          <ScanForm />
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