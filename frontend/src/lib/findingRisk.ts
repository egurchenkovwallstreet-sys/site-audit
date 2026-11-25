export type RiskColor = "green" | "yellow" | "red";

export type FindingLike = {
  color: string | null;
  severity: string;
  max_penalty: number | null;
};

const SEVERITY_LABEL: Record<string, string> = {
  critical: "Критично",
  high: "Высокий риск",
  medium: "Средний риск",
  low: "Низкий риск",
};

/** Критичные пункты в сводке «Итого»: красный риск и severity high/critical. */
export function isCriticalSummaryFinding(f: FindingLike): boolean {
  if (resolveRiskColor(f) !== "red") return false;
  return f.severity === "high" || f.severity === "critical";
}

export function resolveRiskColor(f: FindingLike): RiskColor {
  if (f.color === "green" || f.color === "yellow" || f.color === "red") {
    return f.color;
  }
  if (f.max_penalty != null) {
    if (f.max_penalty < 10_000) return "green";
    if (f.max_penalty <= 100_000) return "yellow";
    return "red";
  }
  if (f.severity === "critical" || f.severity === "high") return "red";
  if (f.severity === "medium") return "yellow";
  return "green";
}

export function riskSortKey(f: FindingLike): number {
  const order: Record<RiskColor, number> = { red: 0, yellow: 1, green: 2 };
  return order[resolveRiskColor(f)];
}

export function severityLabel(severity: string): string {
  return SEVERITY_LABEL[severity] ?? "Риск";
}

export function sortFindings<T extends FindingLike & { id: number }>(items: T[]): T[] {
  return [...items].sort((a, b) => {
    const byRisk = riskSortKey(a) - riskSortKey(b);
    if (byRisk !== 0) return byRisk;
    const pa = a.max_penalty ?? 0;
    const pb = b.max_penalty ?? 0;
    if (pa !== pb) return pb - pa;
    return a.id - b.id;
  });
}

export type FindingWithType = FindingLike & { type: string };

export function sumPenalties(items: FindingLike[]): number {
  return items.reduce((acc, f) => acc + (f.max_penalty ?? 0), 0);
}

/** Штрафы по уже выявленным нарушениям 152-ФЗ (не сценарии взлома). */
export function sumCompliancePenalties(items: FindingWithType[]): number {
  return items
    .filter((f) => f.type === "compliance")
    .reduce((acc, f) => acc + (f.max_penalty ?? 0), 0);
}

/** Суммарный потолок штрафов, если уязвимости приведут к утечке / взлому. */
export function sumBreachPenalties(items: FindingWithType[]): number {
  return items
    .filter((f) => f.type === "security")
    .reduce((acc, f) => acc + (f.max_penalty ?? 0), 0);
}

export function totalPenaltyColor(total: number): RiskColor {
  if (total <= 0) return "green";
  if (total < 10_000) return "green";
  if (total <= 100_000) return "yellow";
  return "red";
}