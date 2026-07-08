"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { ChevronDown, ChevronUp, Scale } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { agreementsApi } from "@/api/agreements";
import { disputesApi } from "@/api/disputes";
import { useSessionStore } from "@/store/sessionStore";
import type { Dispute } from "@/types/dispute";

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

function DisputeCard({ dispute }: { dispute: Dispute }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="rounded-xl border border-neutral-100 overflow-hidden">
      <button
        onClick={() => setExpanded((p) => !p)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-neutral-50 text-left"
      >
        <div>
          <p className="text-sm font-medium">
            Raised by {dispute.raised_by_display_name}
          </p>
          <p className="text-xs text-neutral-400 mt-0.5">
            {new Date(dispute.created_at).toLocaleDateString("en-GB", {
              day: "numeric",
              month: "short",
              year: "numeric",
            })}
          </p>
        </div>
        <div className="flex items-center gap-2">
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
          {dispute.resolved_at && (
            <p className="mt-2 text-xs text-neutral-400">
              Resolved{" "}
              {new Date(dispute.resolved_at).toLocaleDateString("en-GB", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function DisputePage() {
  const { id } = useParams<{ id: string }>();
  const agreementId = Number(id);
  const queryClient = useQueryClient();
  const authenticatedPhone = useSessionStore((s) => s.phone);

  const { data: agreement } = useQuery({
    queryKey: ["agreements", agreementId],
    queryFn: () => agreementsApi.get(agreementId),
  });

  const { data: disputeData } = useQuery({
    queryKey: ["disputes", agreementId],
    queryFn: () => disputesApi.list(agreementId),
    enabled: !!agreement?.sealed_at,
  });

  const disputes = disputeData ?? [];

  const [reason, setReason] = useState("");
  const [showForm, setShowForm] = useState(false);

  const raiseMutation = useMutation({
    mutationFn: () =>
      disputesApi.create(agreementId, {
        reason,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["disputes", agreementId] });
      setReason("");
      setShowForm(false);
    },
  });

  if (!agreement) return null;

  const canRaiseDispute = ["sealed", "reopen_requested", "closed", "archived", "expired"].includes(
    agreement.status
  );
  const ownParty = agreement.parties.find((p) => p.phone === authenticatedPhone);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-xl font-bold tracking-tight">Disputes</h1>
        {canRaiseDispute && !showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 rounded-full border border-red-200 text-red-600 text-sm font-medium hover:bg-red-50"
          >
            Raise dispute
          </button>
        )}
      </div>

      {!canRaiseDispute && (
        <div className="rounded-2xl border border-neutral-100 bg-neutral-50 px-4 py-4 text-sm text-neutral-500">
          Disputes can only be raised against a sealed agreement. Complete the
          consent step first.
        </div>
      )}

      {/* Raise dispute form */}
      {showForm && (
        <div className="rounded-2xl border border-red-100 p-5 flex flex-col gap-4">
          <p className="text-sm font-semibold text-red-700">Raise a dispute</p>
          <p className="text-xs text-neutral-500">
            Provide a clear, factual account of the issue. This will be stored
            permanently alongside the sealed agreement as part of the evidence pack.
          </p>

          {ownParty ? (
            <div className="rounded-xl bg-neutral-50 px-3 py-2 text-xs text-neutral-600">
              Raising as {ownParty.display_name} ({ownParty.role}) from the
              signed-in phone {authenticatedPhone}.
            </div>
          ) : (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
              Sign in with a phone number listed on this agreement before raising
              a dispute. Kotoku will reject disputes opened for another party.
            </div>
          )}

          <div>
            <label className="text-xs font-medium text-neutral-600">
              Reason{" "}
              <span className="font-normal text-neutral-400">
                (min 10 characters)
              </span>
            </label>
            <textarea
              rows={5}
              placeholder="Describe the issue clearly and factually…"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-neutral-400 mt-1">
              {reason.length} / 2000 characters
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              onClick={() => raiseMutation.mutate()}
              disabled={
                raiseMutation.isPending ||
                !ownParty ||
                reason.trim().length < 10
              }
              className="px-5 py-2.5 rounded-full bg-red-600 text-white text-sm font-medium disabled:opacity-50 hover:bg-red-700"
            >
              {raiseMutation.isPending ? "Submitting…" : "Submit dispute"}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-5 py-2.5 rounded-full border border-neutral-200 text-sm font-medium hover:bg-neutral-50"
            >
              Cancel
            </button>
          </div>
          {raiseMutation.isError && (
            <p className="text-sm text-red-600">
              {raiseMutation.error instanceof Error
                ? raiseMutation.error.message
                : "Could not raise dispute. Check the signed-in party and try again."}
            </p>
          )}
        </div>
      )}

      {/* Existing disputes */}
      {disputes.length === 0 && !showForm && canRaiseDispute && (
        <div className="rounded-2xl border border-dashed border-neutral-200 p-8 flex flex-col items-center gap-3 text-center">
          <div className="w-12 h-12 rounded-xl bg-neutral-100 flex items-center justify-center">
            <Scale size={22} className="text-neutral-400" strokeWidth={1.6} />
          </div>
          <div>
            <p className="font-medium text-neutral-700">No disputes raised</p>
            <p className="text-sm text-neutral-400 mt-1">
              If you have a concern about this agreement, raise a dispute and it
              will be stored permanently with the sealed record.
            </p>
          </div>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {disputes.map((d) => (
          <DisputeCard key={d.id} dispute={d} />
        ))}
      </div>
    </div>
  );
}
