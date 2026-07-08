"use client";

import Link from "next/link";
import { ArrowRight, Handshake } from "lucide-react";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { agreementsApi } from "@/api/agreements";
import { PlanBanner } from "@/components/billing/PlanBanner";
import { usePlan } from "@/hooks/usePlan";
import type { Agreement } from "@/types/agreement";

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-neutral-100 text-neutral-600",
  active: "bg-blue-50 text-blue-700",
  sealed: "bg-emerald-50 text-emerald-700",
  reopen_requested: "bg-amber-50 text-amber-700",
  archived: "bg-neutral-100 text-neutral-500",
  expired: "bg-neutral-100 text-neutral-500",
  closed: "bg-neutral-100 text-neutral-500",
};

function AgreementRow({ agreement }: { agreement: Agreement }) {
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => agreementsApi.deleteDraft(agreement.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agreements"] });
    },
  });

  const meta = (
    <p className="text-xs text-neutral-400 mt-0.5">
      {agreement.parties.length} part{agreement.parties.length !== 1 ? "ies" : "y"} ·{" "}
      {new Date(agreement.created_at).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })}
    </p>
  );

  if (agreement.status === "draft") {
    return (
      <div className="group flex flex-col gap-3 rounded-xl border border-neutral-100 px-4 py-3 transition-colors hover:border-neutral-200 sm:flex-row sm:items-center sm:justify-between">
        <Link href={`/agreements/${agreement.id}`} className="flex-1 min-w-0">
          <p className="font-medium text-sm">{agreement.title}</p>
          {meta}
        </Link>
        <div className="ml-0 flex flex-wrap items-center gap-2 shrink-0 sm:ml-3">
          <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${STATUS_STYLES.draft}`}>
            draft
          </span>
          {confirming ? (
            <>
              <span className="text-xs text-neutral-500">Delete?</span>
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="text-xs font-medium text-red-600 hover:text-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending ? "Deleting…" : "Yes"}
              </button>
              <button
                onClick={() => setConfirming(false)}
                className="text-xs text-neutral-400 hover:text-neutral-600"
              >
                Cancel
              </button>
            </>
          ) : (
            <button
              onClick={() => setConfirming(true)}
              className="text-xs text-neutral-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              Delete
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <Link
      href={`/agreements/${agreement.id}`}
      className="flex flex-col gap-3 rounded-xl border border-neutral-100 px-4 py-3 transition-colors hover:border-neutral-200 hover:bg-neutral-50 sm:flex-row sm:items-center sm:justify-between"
    >
      <div>
        <p className="font-medium text-sm">{agreement.title}</p>
        {meta}
      </div>
      <span
        className={`text-xs font-medium px-2.5 py-1 rounded-full ${
          STATUS_STYLES[agreement.status] ?? "bg-neutral-100 text-neutral-600"
        }`}
      >
        {agreement.status.replace("_", " ")}
      </span>
    </Link>
  );
}

function UsagePill() {
  const { data: plan } = usePlan();
  if (!plan || plan.flags.is_enterprise) return null;

  const { usage } = plan;
  const capReached = usage.is_cap_reached;
  const nearCap = usage.is_near_cap;

  const pillClass = capReached
    ? "bg-red-50 text-red-700 border-red-200"
    : nearCap
    ? "bg-amber-50 text-amber-700 border-amber-200"
    : "bg-neutral-100 text-neutral-500 border-transparent";

  return (
    <span className={`text-xs font-medium px-3 py-1 rounded-full border ${pillClass}`}>
      {capReached
        ? `Limit reached — ${plan.plan.name}`
        : `${usage.sealed_agreements_this_period} / ${plan.plan.max_agreements_per_month} seals this month`}
    </span>
  );
}

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["agreements"],
    queryFn: () => agreementsApi.list(),
  });

  const agreements = data?.results ?? [];
  const pending = agreements.filter((a) =>
    ["draft", "active", "reopen_requested"].includes(a.status)
  );
  const recent = agreements.filter((a) => a.status === "sealed").slice(0, 5);

  return (
    <div className="flex flex-col gap-8">
      <PlanBanner />

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <h1 className="text-2xl font-bold tracking-tight">Home</h1>
          <UsagePill />
        </div>
        <Link
          href="/agreements/new"
          className="inline-flex shrink-0 items-center justify-center rounded-full bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-neutral-700"
        >
          + New agreement
        </Link>
      </div>

      {isLoading && (
        <div className="flex flex-col gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 rounded-xl bg-neutral-100 animate-pulse" />
          ))}
        </div>
      )}
      {error && (
        <p className="text-sm text-red-600">Could not load agreements.</p>
      )}

      {pending.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-neutral-500 uppercase tracking-wide mb-3">
            Pending action
          </h2>
          <div className="flex flex-col gap-2">
            {pending.map((a) => (
              <AgreementRow key={a.id} agreement={a} />
            ))}
          </div>
        </section>
      )}

      {recent.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-neutral-500 uppercase tracking-wide mb-3">
            Recently sealed
          </h2>
          <div className="flex flex-col gap-2">
            {recent.map((a) => (
              <AgreementRow key={a.id} agreement={a} />
            ))}
          </div>
        </section>
      )}

      {!isLoading && agreements.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <div className="w-14 h-14 rounded-2xl bg-blue-50 flex items-center justify-center">
            <Handshake size={26} className="text-blue-600" strokeWidth={1.6} />
          </div>
          <div className="text-center">
            <p className="font-semibold text-neutral-800">Your first agreement is one tap away</p>
            <p className="text-sm text-neutral-500 mt-1 max-w-sm">
              Seal a deal with anyone — record evidence, collect consent via SMS,
              and create a tamper-proof vault entry in under five minutes.
            </p>
          </div>
          <Link
            href="/agreements/new"
            className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-700 transition-colors"
          >
            New agreement <ArrowRight size={14} />
          </Link>
        </div>
      )}
    </div>
  );
}
