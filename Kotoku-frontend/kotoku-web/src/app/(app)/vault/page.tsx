"use client";

import Link from "next/link";
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
        <p className="text-sm text-neutral-400">Loading vault…</p>
      )}

      {!isLoading && entries.length === 0 && (
        <div className="text-center py-20 text-neutral-400">
          <p className="text-4xl mb-4">🔒</p>
          <p className="font-medium text-neutral-600">No sealed agreements yet.</p>
          <p className="text-sm mt-1">
            Sealed records will appear here.{" "}
            <Link href="/agreements/new" className="text-emerald-600 underline">
              Create one.
            </Link>
          </p>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {entries.map((entry) => (
          <Link
            key={entry.id}
            href={`/vault/${entry.id}`}
            className="flex items-center justify-between px-4 py-3 rounded-xl border border-neutral-100 hover:border-emerald-100 transition-colors"
          >
            <div>
              <p className="text-sm font-medium font-mono text-neutral-700">
                {entry.seal_hash.slice(0, 16)}…
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
              <span className="text-neutral-300 text-sm">→</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
