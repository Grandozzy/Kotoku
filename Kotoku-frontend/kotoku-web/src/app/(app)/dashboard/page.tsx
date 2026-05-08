"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { agreementsApi } from "@/api/agreements";
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
  return (
    <Link
      href={`/agreements/${agreement.id}`}
      className="flex items-center justify-between px-4 py-3 rounded-xl border border-neutral-100 hover:border-neutral-200 hover:bg-neutral-50 transition-colors"
    >
      <div>
        <p className="font-medium text-sm">{agreement.title}</p>
        <p className="text-xs text-neutral-400 mt-0.5">
          {agreement.parties.length} party{agreement.parties.length !== 1 ? "ies" : ""} ·{" "}
          {new Date(agreement.created_at).toLocaleDateString("en-GB", {
            day: "numeric",
            month: "short",
            year: "numeric",
          })}
        </p>
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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Home</h1>
        <Link
          href="/agreements/new"
          className="px-4 py-2 rounded-full bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-700 transition-colors"
        >
          + New agreement
        </Link>
      </div>

      {isLoading && (
        <p className="text-sm text-neutral-400">Loading your agreements…</p>
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
        <div className="text-center py-20 text-neutral-400">
          <p className="text-4xl mb-4">🤝</p>
          <p className="font-medium text-neutral-600">No agreements yet.</p>
          <p className="text-sm mt-1">
            Good agreements make good friends.{" "}
            <Link href="/agreements/new" className="text-emerald-600 underline">
              Seal your first one.
            </Link>
          </p>
        </div>
      )}
    </div>
  );
}
