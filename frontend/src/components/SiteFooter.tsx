import Link from "next/link";
import styles from "./SiteFooter.module.css";

export function SiteFooter() {
  return (
    <footer className={styles.footer}>
      <Link href="/privacy" className={styles.link}>
        Политика обработки персональных данных
      </Link>
    </footer>
  );
}