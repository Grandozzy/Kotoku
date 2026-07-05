"use client";

import Link from "next/link";
import { useState } from "react";
import { AlertCircle, ArrowLeft, Check, Loader2, ShieldCheck, Users } from "lucide-react";
import { usePlan } from "@/hooks/usePlan";
import { paymentsApi } from "@/api/payments";

// ── Plan data ─────────────────────────────────────────────────────────────────

type PlanFamily = "personal" | "enterprise";

interface PlanDef {
  id: string;
  family: PlanFamily;
  name: string;
  tagline: string;
  price: number;
  highlights: string[];
}

const PLANS: PlanDef[] = [
  {
    id: "personal_basic",
    family: "personal",
    name: "Personal Basic",
    tagline: "Protect one important deal each month",
    price: 10,
    highlights: [
      "Up to 1 sealed agreement per month",
      "Keep each agreement for 12 months",
      "Photos, IDs, and voice notes included",
      "Downloadable PDF summary",
    ],
  },
  {
    id: "personal_plus",
    family: "personal",
    name: "Personal Plus",
    tagline: "Ideal for side hustles and small landlords",
    price: 25,
    highlights: [
      "Up to 3 sealed agreements per month",
      "Keep each agreement for 24 months",
      "Photos, IDs, and voice notes included",
      "Priority PDF generation",
    ],
  },
  {
    id: "personal_protect",
    family: "personal",
    name: "Personal Protect",
    tagline: "For serious individual dealmakers",
    price: 60,
    highlights: [
      "Up to 7 sealed agreements per month",
      "Keep each agreement for 36 months",
      "Photos, IDs, and voice notes included",
      "Fast PDF generation and export",
      "Priority in-app support",
    ],
  },
  {
    id: "enterprise_standard",
    family: "enterprise",
    name: "Enterprise Standard",
    tagline: "Run your operation on solid agreements",
    price: 400,
    highlights: [
      "~20 sealed agreements per month included",
      "Up to 3 team members",
      "Keep agreements for 5 years",
      "Bulk PDF exports and case packs",
      "Basic reporting",
      "Email + chat support",
    ],
  },
  {
    id: "enterprise_plus",
    family: "enterprise",
    name: "Enterprise Plus",
    tagline: "For high-volume dealers and platforms",
    price: 1200,
    highlights: [
      "~80 sealed agreements per month included",
      "Up to 10 team members",
      "Keep agreements for 10 years",
      "Archive search and advanced filters",
      "Full audit bundles and exportable case packs",
      "Priority support with SLA",
      "Optional API access (pilot)",
    ],
  },
];

// Flat tier order — used to determine upgrade vs downgrade direction.
const TIER: Record<string, number> = {
  personal_basic: 0,
  personal_plus: 1,
  personal_protect: 2,
  enterprise_standard: 3,
  enterprise_plus: 4,
};

// ── Plan card ─────────────────────────────────────────────────────────────────

function PlanCard({
  plan,
  currentPlanId,
  recommendedUpgradeIds,
  onAction,
  isActing,
}: {
  plan: PlanDef;
  currentPlanId: string | null;
  recommendedUpgradeIds: string[];
  onAction: (planId: string) => void;
  isActing: boolean;
}) {
  const isCurrent = plan.id === currentPlanId;
  const isRecommended = recommendedUpgradeIds.includes(plan.id);

  const currentTier = currentPlanId != null ? (TIER[currentPlanId] ?? -1) : -1;
  const planTier = TIER[plan.id] ?? -1;
  const isUpgrade = !isCurrent && planTier > currentTier;
  const isDowngrade = !isCurrent && planTier < currentTier;

  // Card border / background
  const cardCls = isCurrent
    ? "border-neutral-200 bg-neutral-50 opacity-75"
    : isRecommended
    ? "border-blue-500 shadow-lg shadow-blue-500/10 bg-white"
    : "border-neutral-200 bg-white";

  // CTA
  let ctaLabel = "Get started";
  let ctaStyle =
    "w-full text-center py-2.5 rounded-xl text-sm font-medium transition-colors bg-neutral-900 text-white hover:bg-neutral-700";

  if (isCurrent) {
    ctaLabel = "Current plan";
    ctaStyle =
      "w-full text-center py-2.5 rounded-xl text-sm font-medium bg-neutral-200 text-neutral-500 cursor-default";
  } else if (isRecommended) {
    ctaLabel = "Upgrade";
    ctaStyle =
      "w-full text-center py-2.5 rounded-xl text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700";
  } else if (isUpgrade) {
    ctaLabel = "Upgrade";
    ctaStyle =
      "w-full text-center py-2.5 rounded-xl text-sm font-medium transition-colors bg-neutral-900 text-white hover:bg-neutral-700";
  } else if (isDowngrade) {
    ctaLabel = "Downgrade";
    ctaStyle =
      "w-full text-center py-2.5 rounded-xl text-sm font-medium transition-colors border border-neutral-300 text-neutral-500 hover:bg-neutral-50";
  }

  return (
    <div className={`relative flex flex-col rounded-2xl border p-6 ${cardCls}`}>
      {/* Badges */}
      {isCurrent && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="bg-neutral-700 text-white text-xs font-semibold px-3 py-1 rounded-full tracking-wide">
            Your plan
          </span>
        </div>
      )}
      {isRecommended && !isCurrent && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="bg-blue-600 text-white text-xs font-semibold px-3 py-1 rounded-full tracking-wide">
            Recommended upgrade
          </span>
        </div>
      )}

      <div className="mb-4">
        <h3 className="text-base font-semibold text-neutral-900">{plan.name}</h3>
        <p className="text-xs text-neutral-500 mt-0.5">{plan.tagline}</p>
      </div>

      <div className="mb-5">
        <span className="text-3xl font-bold text-neutral-900">{plan.price}</span>
        <span className="text-neutral-500 ml-1 text-xs">GHS / month</span>
      </div>

      <ul className="space-y-2.5 mb-6 flex-1">
        {plan.highlights.map((h) => (
          <li key={h} className="flex items-start gap-2.5 text-xs text-neutral-600">
            <Check
              size={13}
              className={`mt-0.5 shrink-0 ${isCurrent ? "text-neutral-400" : "text-blue-600"}`}
              strokeWidth={2.5}
            />
            <span>{h}</span>
          </li>
        ))}
      </ul>

      {isCurrent ? (
        <span className={ctaStyle}>{ctaLabel}</span>
      ) : (
        <button
          onClick={() => onAction(plan.id)}
          disabled={isActing}
          className={`${ctaStyle} disabled:opacity-60 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2`}
        >
          {isActing ? (
            <Loader2 size={13} className="animate-spin" strokeWidth={2} />
          ) : null}
          {ctaLabel}
        </button>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PlansPage() {
  const { data: subscription, isLoading, isError: planLoadError } = usePlan();

  const currentPlanId = subscription?.plan.id ?? null;
  const currentFamily = subscription?.plan.family ?? "personal";
  const recommendedUpgradeIds = (subscription?.recommended_upgrades ?? []).map(
    (u) => u.id
  );

  const [manualTab, setManualTab] = useState<PlanFamily | null>(null);
  const tab = manualTab ?? currentFamily;
  const [actingPlanId, setActingPlanId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleAction(planId: string) {
    setActingPlanId(planId);
    setError(null);
    try {
      const callbackUrl = `${window.location.origin}/payment/callback`;
      const { authorization_url } = await paymentsApi.initiate(planId, callbackUrl);
      window.location.href = authorization_url;
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not start payment. Please try again."
      );
      setActingPlanId(null);
    }
  }

  const visiblePlans = PLANS.filter((p) => p.family === tab);

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          href="/profile"
          className="w-8 h-8 rounded-full border border-neutral-200 flex items-center justify-center hover:bg-neutral-50 transition-colors shrink-0"
        >
          <ArrowLeft size={14} className="text-neutral-500" strokeWidth={2} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Plans</h1>
          {!isLoading && currentPlanId && (
            <p className="text-sm text-neutral-500 mt-0.5">
              You&apos;re on <strong>{subscription?.plan.name}</strong>
            </p>
          )}
        </div>
      </div>

      {/* Tab toggle */}
      <div className="inline-flex bg-neutral-100 rounded-full p-1 gap-1 self-start">
        <button
          onClick={() => setManualTab("personal")}
          className={`px-5 py-1.5 rounded-full text-sm font-medium transition-all ${
            tab === "personal"
              ? "bg-white text-neutral-900 shadow-sm"
              : "text-neutral-500 hover:text-neutral-700"
          }`}
        >
          Personal
        </button>
        <button
          onClick={() => setManualTab("enterprise")}
          className={`px-5 py-1.5 rounded-full text-sm font-medium transition-all inline-flex items-center gap-1.5 ${
            tab === "enterprise"
              ? "bg-white text-neutral-900 shadow-sm"
              : "text-neutral-500 hover:text-neutral-700"
          }`}
        >
          <Users size={12} strokeWidth={2} />
          Enterprise
        </button>
      </div>

      {/* Plan cards */}
      {planLoadError && (
        <div className="rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 flex items-center gap-3 text-sm text-amber-700">
          <AlertCircle size={15} className="shrink-0" strokeWidth={2} />
          Could not load your current plan. Plans are shown below — your current plan badge may be missing.
        </div>
      )}
      {error && (
        <div className="rounded-xl bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="rounded-2xl border border-neutral-100 bg-neutral-50 h-72 animate-pulse"
            />
          ))}
        </div>
      ) : (
        <div
          className={`grid gap-5 ${
            tab === "personal"
              ? "grid-cols-1 md:grid-cols-3"
              : "grid-cols-1 md:grid-cols-2 max-w-2xl"
          }`}
        >
          {visiblePlans.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              currentPlanId={currentPlanId}
              recommendedUpgradeIds={recommendedUpgradeIds}
              onAction={handleAction}
              isActing={actingPlanId === plan.id}
            />
          ))}
        </div>
      )}

      {/* Footer note */}
      <div className="flex items-start gap-2 bg-neutral-50 rounded-xl px-4 py-3 border border-neutral-100">
        <ShieldCheck size={14} className="text-blue-600 mt-0.5 shrink-0" strokeWidth={2} />
        <p className="text-xs text-neutral-500 leading-relaxed">
          Plan changes take effect immediately. Need help choosing?{" "}
          <Link href="/how-it-works" className="text-blue-600 hover:underline font-medium">
            See how Kotoku works
          </Link>{" "}
          or contact support.
        </p>
      </div>
    </div>
  );
}
