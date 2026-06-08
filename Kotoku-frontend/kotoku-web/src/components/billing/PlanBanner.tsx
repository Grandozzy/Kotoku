"use client";

import Link from "next/link";
import { TrendingUp, AlertTriangle, ArrowRight } from "lucide-react";
import { usePlan } from "@/hooks/usePlan";

/**
 * Compact upgrade / cap banner shown at the top of authenticated pages.
 * Renders nothing for Enterprise accounts or when there is no billing data.
 */
export function PlanBanner() {
  const { data: plan } = usePlan();

  if (!plan || plan.flags.is_enterprise) return null;

  const { usage, flags } = plan;
  const capReached = usage.is_cap_reached;
  const nearCap = usage.is_near_cap;

  if (!capReached && !nearCap && !flags.show_upgrade_recommendation) return null;

  const isError = capReached;
  const bgClass = isError
    ? "bg-red-50 border-red-200"
    : "bg-amber-50 border-amber-200";
  const textClass = isError ? "text-red-800" : "text-amber-800";
  const subClass = isError ? "text-red-600" : "text-amber-600";
  const Icon = isError ? AlertTriangle : TrendingUp;

  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 rounded-xl border ${bgClass} text-sm mb-6`}
    >
      <Icon size={16} className={`mt-0.5 shrink-0 ${subClass}`} strokeWidth={2} />
      <div className="flex-1 min-w-0">
        <p className={`font-semibold ${textClass}`}>
          {capReached
            ? `You've used all ${plan.plan.max_agreements_per_month} seals for ${plan.plan.name} this month`
            : flags.business_usage_suspected
            ? "You're using Kotoku like a business"
            : `${usage.remaining_agreements_this_period} seal${usage.remaining_agreements_this_period === 1 ? "" : "s"} left this month on ${plan.plan.name}`}
        </p>
        <p className={`text-xs mt-0.5 ${subClass}`}>
          {capReached
            ? "Upgrade to seal more agreements, or wait until next month."
            : flags.business_usage_suspected
            ? "An Enterprise plan gives you higher volume, team access, and longer retention."
            : "Upgrade for a higher limit."}
        </p>
      </div>
      {plan.recommended_upgrades[0] && (
        <Link
          href="/pricing"
          className={`inline-flex items-center gap-1 shrink-0 text-xs font-semibold px-3 py-1.5 rounded-full border ${
            isError
              ? "border-red-300 text-red-700 hover:bg-red-100"
              : "border-amber-300 text-amber-700 hover:bg-amber-100"
          } transition-colors`}
        >
          View plans <ArrowRight size={11} strokeWidth={2.5} />
        </Link>
      )}
    </div>
  );
}
