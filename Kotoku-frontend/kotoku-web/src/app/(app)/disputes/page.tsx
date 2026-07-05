"use client";

import Link from "next/link";
import { useState } from "react";
import { ChevronDown, ChevronRight, ChevronUp, Scale } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { disputesApi } from "@/api/disputes";
import type { Dispute } from "@/types/dispute";
import { SCENARIO_MAP } from "@/constants/scenarios";

const STATUS_STYLES: Record<string, string> = {
  open: "bg-red-50 text-red-700",
  under_review: "bg-amber-50 text-amber-700",
  resolved: "bg-emerald-50 text-emerald-700",
  closed: "bg-neutral-100 text-neutral-500",
};

const STATUS_LABEL: Record<string, string> = {
  open: "Open",
  under_review: "Under review",
  resolved: "Resolved",
  closed: "Closed",
};

function DisputeRow({ dispute }: { dispute: Dispute }) {
  const [expanded, setExpanded] = useState(false);
  const scenarioLabel = dispute.agreement_type
    ? (SCENARIO_MAP[dispute.agreement_type]?.label ?? dispute.agreement_type)
    : "Agreement";

  return (
    <div className="rounded-xl border border-neutral-100 overflow-hidden">
      <button
        onClick={() => setExpanded((p) => !p)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-neutral-50 text-left"
      >
        <div className="min-w-0">
          <p className="text-sm font-medium text-neutral-800 truncate">
            {scenarioLabel}
          </p>
          <p className="text-xs text-neutral-400 mt-0.5">
            Raised by {dispute.raised_by_display_name} ·{" "}
            {new Date(dispute.created_at).toLocaleDateString("en-GB", {
              day: "numeric",
              month: "short",
              year: "numeric",
            })}
          </p>
        </div>
        <div className="flex items-center gap-2 ml-3 shrink-0">
          <span
            className={`text-xs font-medium px-2.5 py-1 rounded-full ${STATUS_STYLES[dispute.status]}`}
          >
            {STATUS_LABEL[dispute.status]}
          </span>
          {expanded
            ? <ChevronUp size={14} className="text-neutral-300" strokeWidth={2} />
            : <ChevronDown size={14} className="text-neutral-300" strokeWidth={2} />
          }
        </div>
      </button>
      {expanded && (
        <div className="px-4 pb-4 border-t border-neutral-50">
          <p className="text-sm text-neutral-700 mt-3 whitespace-pre-wrap leading-relaxed">
            {dispute.reason}
          </p>
          {dispute.resolution && (
            <div className="mt-3 rounded-lg bg-emerald-50 px-3 py-2">
              <p className="text-xs font-semibold text-emerald-700 mb-1">Resolution</p>
              <p className="text-sm text-emerald-700">{dispute.resolution}</p>
            </div>
          )}
          <div className="mt-3 flex items-center gap-3">
            <Link
              href={`/agreements/${dispute.agreement_id}/dispute`}
              className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline font-medium"
            >
              View agreement <ChevronRight size={12} strokeWidth={2} />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

export default function DisputesPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["disputes"],
    queryFn: () => disputesApi.listAll(),
  });

  const disputes = data ?? [];
  const open = disputes.filter((d) => d.status === "open" || d.status === "under_review");
  const resolved = disputes.filter((d) => d.status === "resolved" || d.status === "closed");

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <h1 className="text-2xl font-bold tracking-tight">Disputes</h1>

      {isLoading && (
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 rounded-xl bg-neutral-100 animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 flex items-center justify-between gap-4 text-sm text-red-700">
          <span>Could not load disputes.</span>
          <button onClick={() => refetch()} className="font-medium hover:underline shrink-0">
            Try again
          </button>
        </div>
      )}

      {!isLoading && !isError && disputes.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <div className="w-14 h-14 rounded-2xl bg-neutral-100 flex items-center justify-center">
            <Scale size={26} className="text-neutral-400" strokeWidth={1.6} />
          </div>
          <div className="text-center">
            <p className="font-semibold text-neutral-800">No disputes</p>
            <p className="text-sm text-neutral-500 mt-1 max-w-sm">
              Disputes raised against sealed agreements will appear here.
            </p>
          </div>
        </div>
      )}

      {open.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-semibold uppercase tracking-widest text-neutral-400">
            Active ({open.length})
          </p>
          {open.map((d) => <DisputeRow key={d.id} dispute={d} />)}
        </div>
      )}

      {resolved.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-semibold uppercase tracking-widest text-neutral-400">
            Resolved ({resolved.length})
          </p>
          {resolved.map((d) => <DisputeRow key={d.id} dispute={d} />)}
        </div>
      )}
    </div>
  );
}
