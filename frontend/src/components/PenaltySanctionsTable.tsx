import styles from "./PenaltySanctionsTable.module.css";
import { formatRubMax, type PenaltySanctions } from "@/lib/penaltySanctions";

function cellRepeat(value: number | null): string {
  if (value == null || value <= 0) {
    return "—";
  }
  return formatRubMax(value);
}

export function PenaltySanctionsTable({
  sanctions,
  compact,
}: {
  sanctions: PenaltySanctions;
  compact?: boolean;
}) {
  return (
    <div
      className={compact ? styles.wrapCompact : styles.wrap}
      role="group"
      aria-label={`Штрафы КоАП ${sanctions.koap_part}`}
    >
      <p className={styles.caption}>
        Пределы по КоАП РФ ({sanctions.koap_part}
        {sanctions.koap_repeat_part
          ? `, повтор — ${sanctions.koap_repeat_part}`
          : ""}
        )
      </p>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Субъект</th>
            <th scope="col">Первичное</th>
            <th scope="col">Повторное</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">ИП</th>
            <td>{formatRubMax(sanctions.ip_max)}</td>
            <td>{cellRepeat(sanctions.ip_repeat_max)}</td>
          </tr>
          <tr>
            <th scope="row">Юрлицо</th>
            <td>{formatRubMax(sanctions.legal_max)}</td>
            <td>{cellRepeat(sanctions.legal_repeat_max)}</td>
          </tr>
        </tbody>
      </table>
      {sanctions.ip_note ? (
        <p className={styles.note}>{sanctions.ip_note}</p>
      ) : null}
      <p className={styles.disclaimer}>
        Орган назначает сумму внутри диапазона КоАП. Повторное — если нарушение
        повторилось в срок, установленный кодексом (обычно 1 год после исполнения
        прошлого постановления).
      </p>
    </div>
  );
}