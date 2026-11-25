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
function securityKoapFallback(maxPenalty: number): SanctionPair {
  if (maxPenalty >= 200_000) {
    return { ip: 40_000, legal: 90_000 };
  }
  if (maxPenalty >= 100_000) {
    return { ip: 40_000, legal: 90_000 };
  }
  return { ip: 20_000, legal: 60_000 };
}

function sanctionContribution(f: FindingWithSanctions): SanctionPair {
  if (f.sanctions) {
    return {
      ip: f.sanctions.ip_max,
      legal: f.sanctions.legal_max,
    };
  }
  if (f.type === "security" && f.max_penalty != null && f.max_penalty > 0) {
    return securityKoapFallback(f.max_penalty);
  }
  return { ip: 0, legal: 0 };
}

function totalsForType(items: FindingWithSanctions[], type: string): SanctionPair {
  return items
    .filter((f) => f.type === type)
    .reduce<SanctionPair>(
      (acc, f) => {
        const c = sanctionContribution(f);
        return { ip: acc.ip + c.ip, legal: acc.legal + c.legal };
      },
      { ip: 0, legal: 0 },
    );
}

/** Суммы верхних границ по фактам 152‑ФЗ / 168‑ФЗ. */
export function complianceSanctionTotals(items: FindingWithSanctions[]) {
  const pair = totalsForType(items, "compliance");
  return {
    ip: pair.ip,
    legal: pair.legal,
    ipRepeat: 0,
    legalRepeat: 0,
  };
}

export function breachSanctionTotals(items: FindingWithSanctions[]) {
  const pair = totalsForType(items, "security");
  return {
    ip: pair.ip,
    legal: pair.legal,
    ipRepeat: 0,
    legalRepeat: 0,
  };
}