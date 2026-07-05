"use client";

import Link from "next/link";
import { AlertCircle, ChevronRight, Lock } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { vaultApi } from "@/api/vault";
import type { VaultEntry } from "@/types/vault";

function pdfStatusLabel(status: VaultEntry["pdf_status"]): {
  label: string;
  className: string;
} | null {
  if (status === "ready") {
    return { label: "PDF ready", className: "bg-emerald-50 text-emerald-700" };
  }
  if (status === "generating") {
    return { label: "Generating…", className: "bg-blue-50 text-blue-700" };
  }
  if (status === "failed") {
    return { label: "Export failed", className: "bg-red-50 text-red-700" };
  }
  return { label: "PDF pending", className: "bg-neutral-100 text-neutral-500" };
}

export default function VaultPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["vault"],
    queryFn: () => vaultApi.list(),
  });

  const entries = data?.results ?? [];

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold tracking-tight">Vault</h1>

      {isLoading && (
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 rounded-xl bg-neutral-100 animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <div className="w-14 h-14 rounded-2xl bg-red-50 flex items-center justify-center">
            <AlertCircle size={26} className="text-red-500" strokeWidth={1.6} />
          </div>
          <div className="text-center">
            <p className="font-semibold text-neutral-800">Could not load vault</p>
            <p className="text-sm text-neutral-500 mt-1 max-w-sm">
              There was a problem fetching your sealed agreements.
            </p>
          </div>
          <button
            onClick={() => refetch()}
            className="px-5 py-2 rounded-full border border-neutral-200 text-sm font-medium hover:bg-neutral-50 transition-colors"
          >
            Try again
          </button>
        </div>
      )}

      {!isLoading && !isError && entries.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <div className="w-14 h-14 rounded-2xl bg-blue-50 flex items-center justify-center">
            <Lock size={26} className="text-blue-600" strokeWidth={1.6} />
          </div>
          <div className="text-center">
            <p className="font-semibold text-neutral-800">Your vault is empty</p>
            <p className="text-sm text-neutral-500 mt-1 max-w-sm">
              Sealed agreements are stored here — tamper-proof, hashed, and
              retrievable any time.{" "}
              <Link href="/agreements/new" className="text-blue-600 hover:underline">
                Seal your first agreement.
              </Link>
            </p>
          </div>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {entries.map((entry) => (
          <VaultListItem key={entry.id} entry={entry} />
        ))}
      </div>
    </div>
  );
}

function VaultListItem({ entry }: { entry: VaultEntry }) {
  const pdf = pdfStatusLabel(entry.pdf_status);

  return (
    <Link
      href={`/vault/${entry.agreement}`}
      className="flex items-center justify-between gap-4 px-4 py-3 rounded-xl border border-neutral-100 hover:border-emerald-100 transition-colors"
    >
      <div className="min-w-0">
        <p className="text-sm font-semibold text-neutral-800 truncate">
          {entry.title}
        </p>
        <p className="text-xs text-neutral-500 mt-0.5">
          Sealed{" "}
          {new Date(entry.sealed_at).toLocaleDateString("en-GB", {
            day: "numeric",
            month: "short",
            year: "numeric",
          })}
          {entry.retain_until && (
            <> · Retention{" "}
              {new Date(entry.retain_until).toLocaleDateString("en-GB", {
                month: "short",
                year: "numeric",
              })}
            </>
          )}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {pdf && (
          <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${pdf.className}`}>
            {pdf.label}
          </span>
        )}
        <ChevronRight size={16} className="text-neutral-300" strokeWidth={2} />
      </div>
    </Link>
  );
}
