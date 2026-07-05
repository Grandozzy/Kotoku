"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { agreementsApi } from "@/api/agreements";
import { StepNav } from "@/components/agreement/StepNav";
import { StatusBadge } from "@/components/ui/StatusBadge";
import Link from "next/link";
import { AlertCircle, ChevronLeft } from "lucide-react";

export default function AgreementLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { id } = useParams<{ id: string }>();
  const agreementId = Number(id);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => agreementsApi.deleteDraft(agreementId),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["agreements", agreementId] });
      queryClient.invalidateQueries({ queryKey: ["agreements"] });
      router.replace("/dashboard");
    },
  });

  const { data: agreement, isLoading, isError } = useQuery({
    queryKey: ["agreements", agreementId],
    queryFn: () => agreementsApi.get(agreementId),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-sm text-neutral-400">
        Loading…
      </div>
    );
  }

  if (isError) {
    return (
      <div className="py-24 flex flex-col items-center gap-4 text-center">
        <div className="w-12 h-12 rounded-xl bg-red-50 flex items-center justify-center">
          <AlertCircle size={22} className="text-red-500" strokeWidth={1.6} />
        </div>
        <div>
          <p className="font-semibold text-neutral-800">Could not load agreement</p>
          <p className="text-sm text-neutral-500 mt-1">Check your connection and try again.</p>
        </div>
        <Link href="/dashboard" className="text-sm text-blue-600 hover:underline">
          Back to home
        </Link>
      </div>
    );
  }

  if (!agreement) {
    return (
      <div className="py-24 text-center text-neutral-400">
        <p>Agreement not found.</p>
        <Link href="/dashboard" className="mt-2 text-sm text-blue-600 hover:underline">
          Back to home
        </Link>
      </div>
    );
  }

  return (
    <div className="flex gap-8 max-w-5xl mx-auto">
      {/* Sidebar */}
      <aside className="w-48 shrink-0 pt-1">
        <div className="mb-4">
          <p className="text-xs text-neutral-400 uppercase tracking-widest mb-1">Agreement</p>
          <p className="font-semibold text-sm leading-snug line-clamp-2">{agreement.title}</p>
          <div className="mt-2">
            <StatusBadge status={agreement.status} />
          </div>
        </div>
        <StepNav agreement={agreement} />
        <div className="mt-6 pt-4 border-t border-neutral-100 flex flex-col gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1 text-xs text-neutral-400 hover:text-neutral-600"
          >
            <ChevronLeft size={14} strokeWidth={2} /> All agreements
          </Link>
          {agreement.status === "draft" && (
            confirmDelete ? (
              <div className="flex flex-col gap-1">
                <p className="text-xs text-neutral-500">Delete this draft?</p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => deleteMutation.mutate()}
                    disabled={deleteMutation.isPending}
                    className="text-xs font-medium text-red-600 hover:text-red-700 disabled:opacity-50"
                  >
                    {deleteMutation.isPending ? "Deleting…" : "Yes, delete"}
                  </button>
                  <button
                    onClick={() => setConfirmDelete(false)}
                    className="text-xs text-neutral-400 hover:text-neutral-600"
                  >
                    Cancel
                  </button>
                </div>
                {deleteMutation.isError && (
                  <p className="text-xs text-red-500">Could not delete. Try again.</p>
                )}
              </div>
            ) : (
              <button
                onClick={() => setConfirmDelete(true)}
                className="text-xs text-neutral-400 hover:text-red-500 text-left transition-colors"
              >
                Delete draft
              </button>
            )
          )}
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  );
}
