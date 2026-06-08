"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { agreementsApi } from "@/api/agreements";
import { StepNav } from "@/components/agreement/StepNav";
import { StatusBadge } from "@/components/ui/StatusBadge";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";

export default function AgreementLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { id } = useParams<{ id: string }>();
  const agreementId = Number(id);

  const { data: agreement, isLoading } = useQuery({
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

  if (!agreement) {
    return (
      <div className="py-24 text-center text-neutral-400">
        <p>Agreement not found.</p>
        <Link href="/dashboard" className="mt-2 text-sm text-emerald-600 underline">
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
        <div className="mt-6 pt-4 border-t border-neutral-100">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1 text-xs text-neutral-400 hover:text-neutral-600"
          >
            <ChevronLeft size={14} strokeWidth={2} /> All agreements
          </Link>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  );
}
