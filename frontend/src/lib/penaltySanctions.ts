export type PenaltySanctions = {
  koap_part: string;
  koap_repeat_part: string | null;
  ip_max: number;
  legal_max: number;
  ip_repeat_max: number | null;
  legal_repeat_max: number | null;
  ip_note: string | null;
};

export type FindingWithSanctions = {
  type: string;
  max_penalty: number | null;
  sanctions?: PenaltySanctions | null;
};

export function formatRubMax(amount: number): string {
  return `до ${amount.toLocaleString("ru-RU")} ₽`;
}

type SumKey = "ip_max" | "legal_max" | "ip_repeat_max" | "legal_repeat_max";

function sumSanctionKey(
  items: FindingWithSanctions[],
  type: string,
  key: SumKey,
): number {
  return items
    .filter((f) => f.type === type && f.sanctions)
    .reduce((acc, f) => {
      const v = f.sanctions?.[key];
      return acc + (typeof v === "number" ? v : 0);
    }, 0);
}

/** Суммы верхних границ по фактам 152-ФЗ (не складывать смешанно в одну цифру). */
export function complianceSanctionTotals(items: FindingWithSanctions[]) {
  return {
    ip: sumSanctionKey(items, "compliance", "ip_max"),
    legal: sumSanctionKey(items, "compliance", "legal_max"),
    ipRepeat: sumSanctionKey(items, "compliance", "ip_repeat_max"),
    legalRepeat: sumSanctionKey(items, "compliance", "legal_repeat_max"),
  };
}

export function breachSanctionTotals(items: FindingWithSanctions[]) {
  return {
    ip: sumSanctionKey(items, "security", "ip_max"),
    legal: sumSanctionKey(items, "security", "legal_max"),
    ipRepeat: sumSanctionKey(items, "security", "ip_repeat_max"),
    legalRepeat: sumSanctionKey(items, "security", "legal_repeat_max"),
  };
}