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

export type SanctionPair = { ip: number; legal: number };

export function formatRubMax(amount: number): string {
  return `до ${amount.toLocaleString("ru-RU")} ₽`;
}

/** КоАП при отсутствии sanctions в API (типичные коды утечки по техрискам). */
/** Ст. 13.11 ч. 5 при утечке через техпробел (ч. 5.1 при повторе). */
const SECURITY_KOAP_FALLBACK = {
  ip: 40_000,
  legal: 90_000,
  ipRepeat: 100_000,
  legalRepeat: 500_000,
} as const;

function securityKoapFallback(maxPenalty: number): SanctionPair {
  if (maxPenalty >= 200_000) {
    return { ip: 40_000, legal: 90_000 };
  }
  if (maxPenalty >= 100_000) {
    return { ip: 40_000, legal: 90_000 };
  }
  return { ip: 20_000, legal: 60_000 };
}

type SanctionTotals = SanctionPair & { ipRepeat: number; legalRepeat: number };

function sanctionContribution(f: FindingWithSanctions): SanctionTotals {
  if (f.sanctions) {
    return {
      ip: f.sanctions.ip_max,
      legal: f.sanctions.legal_max,
      ipRepeat: f.sanctions.ip_repeat_max ?? 0,
      legalRepeat: f.sanctions.legal_repeat_max ?? 0,
    };
  }
  if (f.type === "security" && f.max_penalty != null && f.max_penalty > 0) {
    const base = securityKoapFallback(f.max_penalty);
    return {
      ...base,
      ipRepeat: SECURITY_KOAP_FALLBACK.ipRepeat,
      legalRepeat: SECURITY_KOAP_FALLBACK.legalRepeat,
    };
  }
  return { ip: 0, legal: 0, ipRepeat: 0, legalRepeat: 0 };
}

function totalsForType(
  items: FindingWithSanctions[],
  type: string,
): SanctionTotals {
  return items
    .filter((f) => f.type === type)
    .reduce<SanctionTotals>(
      (acc, f) => {
        const c = sanctionContribution(f);
        return {
          ip: acc.ip + c.ip,
          legal: acc.legal + c.legal,
          ipRepeat: acc.ipRepeat + c.ipRepeat,
          legalRepeat: acc.legalRepeat + c.legalRepeat,
        };
      },
      { ip: 0, legal: 0, ipRepeat: 0, legalRepeat: 0 },
    );
}

/** Суммы верхних границ по фактам 152‑ФЗ / 168‑ФЗ. */
export function complianceSanctionTotals(items: FindingWithSanctions[]) {
  return totalsForType(items, "compliance");
}

export function breachSanctionTotals(items: FindingWithSanctions[]) {
  return totalsForType(items, "security");
}