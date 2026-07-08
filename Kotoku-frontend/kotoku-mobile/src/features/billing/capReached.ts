import type { CurrentPlanResponse, UpgradeOption } from "@/api/billing";

export function formatCapResetDate(periodEndIso?: string | null): string | null {
  if (!periodEndIso) return null;
  const parsed = new Date(periodEndIso);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export function getCapReachedMessage(
  plan: CurrentPlanResponse,
  upgrade?: UpgradeOption,
): string {
  const resetDate = formatCapResetDate(plan.usage.period.end);
  const used = plan.usage.sealed_agreements_this_period;
  const cap = plan.plan.max_agreements_per_month;
  const base =
    `You've used ${used} of ${cap} seal${cap === 1 ? "" : "s"} this month on ${plan.plan.name}.`;
  const wait = resetDate
    ? ` Wait until ${resetDate} when your monthly limit resets.`
    : " Wait until next month when your monthly limit resets.";

  if (!upgrade) {
    return `${base} Upgrade now for more seals, or${wait}`;
  }

  return (
    `${base} Upgrade now to ${upgrade.name} for up to ` +
    `${upgrade.max_agreements_per_month} seals per month, or${wait}`
  );
}
