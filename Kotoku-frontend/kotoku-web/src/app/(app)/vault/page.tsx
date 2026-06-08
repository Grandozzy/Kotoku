"use client";

import Link from "next/link";
import { ChevronRight, Lock } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { vaultApi } from "@/api/vault";

export default function VaultPage() {
  const { data, isLoading } = useQuery({
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

      {!isLoading && entries.length === 0 && (
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
          <Link
            key={entry.id}
            href={`/vault/${entry.agreement}`}
            className="flex items-center justify-between px-4 py-3 rounded-xl border border-neutral-100 hover:border-emerald-100 transition-colors"
          >
            <div>
              <p className="text-sm font-medium text-neutral-700">
                {entry.title}
              </p>
              <p className="text-xs font-mono text-neutral-400 mt-0.5">
                {entry.seal_hash.slice(0, 16)}...
              </p>
              <p className="text-xs text-neutral-400 mt-0.5">
                Sealed{" "}
                {new Date(entry.sealed_at).toLocaleDateString("en-GB", {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                })}
                {entry.retain_until && (
                  <> · Retained until{" "}
                    {new Date(entry.retain_until).toLocaleDateString("en-GB", {
                      month: "short",
                      year: "numeric",
                    })}
                  </>
                )}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {entry.pdf_status === "ready" ? (
                <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700">
                  PDF ready
                </span>
              ) : entry.pdf_status === "generating" ? (
                <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-blue-50 text-blue-700">
                  Generating…
                </span>
              ) : entry.pdf_status === "failed" ? (
                <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-red-50 text-red-700">
                  Export failed
                </span>
              ) : null}
              <ChevronRight size={16} className="text-neutral-300" strokeWidth={2} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
