import styles from "../app/home.module.css";

export function HomePitch() {
  return (
    <section className={styles.pitch} aria-labelledby="pitch-heading">
      <div className={styles.pitchHook}>
        <p id="pitch-heading" className={styles.pitchQuestion}>
          Ваш сайт уже собирает ПДн?
        </p>
        <p className={styles.pitchAlert}>
          Вы уверены, что завтра вам не придёт штраф на{" "}
          <span className={styles.pitchEm}>сотни тысяч</span>?
        </p>
      </div>

      <div className={styles.pitchFines}>
        <p className={styles.pitchFinesIntro}>
          С 2025–2026 пределы в КоАП выросли. Ориентиры при привлечении к
          ответственности:
        </p>
        <div className={styles.pitchFinesGrid}>
          <div className={styles.pitchFineCard}>
            <p className={styles.pitchFineRole}>ООО</p>
            <p className={styles.pitchFineAmount}>до 300 000 ₽</p>
            <p className={styles.pitchFineNote}>типичный потолок</p>
            <p className={styles.pitchFineRepeat}>
              Повтор — до <strong>500 000 ₽</strong> и выше по тяжёлым составам
            </p>
          </div>
          <div className={styles.pitchFineCard}>
            <p className={styles.pitchFineRole}>ИП</p>
            <p className={styles.pitchFineAmount}>десятки — сотни тыс. ₽</p>
            <p className={styles.pitchFineNote}>как должностное лицо</p>
            <p className={styles.pitchFineRepeat}>При повторе — выше</p>
          </div>
        </div>
        <p className={styles.pitchFinesFoot}>
          Узнать из постановления обычно{" "}
          <strong>дороже и позже</strong>, чем один вечер правок.
        </p>
      </div>

      <p className={styles.pitchBody}>
        Роскомнадзор усилил контроль, в том числе{" "}
        <strong>автоматизированный анализ сайтов</strong>. Пока вы не смотрели — не
        знаете, есть ли у вас те же признаки, за которые уже режут соседей по
        нише.
      </p>

      <div className={styles.pitchOffer}>
        <p className={styles.pitchOfferTitle}>Наш сервис</p>
        <p className={styles.pitchOfferText}>
          Проверка за <strong>до 10 минут</strong>: где вас могут оштрафовать по
          152‑ФЗ уже сейчас, и какие <strong>риски безопасности</strong> могут
          вылиться в крупные санкции позже.
        </p>
        <p className={styles.pitchOfferText}>
          Чеклист с приоритетами — что чинить первым и ссылка для разработчика.
          Исправить <strong>до претензии</strong>, а не после штрафа.
        </p>
      </div>

      <p className={styles.pitchLegal}>
        Ориентиры по КоАП, не юридическое заключение. Итоговую сумму назначает
        орган.
      </p>
    </section>
  );
}