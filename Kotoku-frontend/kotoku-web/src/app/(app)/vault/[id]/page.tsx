"use client";

import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { vaultApi } from "@/api/vault";

export default function VaultEntryPage() {
  const { id } = useParams<{ id: string }>();
  const agreementId = Number(id);
  const queryClient = useQueryClient();

  const { data: entry, isLoading } = useQuery({
    queryKey: ["vault", agreementId],
    queryFn: () => vaultApi.get(agreementId),
  });

  const retryMutation = useMutation({
    mutationFn: () => vaultApi.retryExport(agreementId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vault", agreementId] }),
  });

  if (isLoading) {
    return <p className="text-sm text-neutral-400">Loading…</p>;
  }

  if (!entry) return null;

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div>
        <p className="text-xs text-neutral-400 uppercase tracking-widest mb-1">Vault Entry</p>
        <h1 className="text-2xl font-bold tracking-tight">{entry.title}</h1>
        <p className="text-sm text-neutral-500 mt-1">
          Tamper-proof sealed agreement stored in your vault.
        </p>
      </div>

      <div className="grid gap-3 rounded-2xl border border-neutral-100 bg-white p-5">
        <DetailRow label="Status" value={entry.status.replaceAll("_", " ")} />
        <DetailRow
          label="Sealed"
          value={new Date(entry.sealed_at).toLocaleString("en-GB", {
            day: "numeric",
            month: "long",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })}
        />
        {entry.retain_until && (
          <DetailRow
            label="Retention"
            value={new Date(entry.retain_until).toLocaleDateString("en-GB", {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          />
        )}
        <div className="pt-3 border-t border-neutral-100">
          <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
            Seal hash (SHA-256)
          </p>
          <p className="font-mono text-xs break-all text-neutral-700">{entry.seal_hash}</p>
        </div>
      </div>

      {/* PDF */}
      <div>
        {entry.pdf_status === "ready" && entry.pdf_url ? (
          <div className="flex flex-col gap-3">
            <a
              href={entry.pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-700 transition-colors w-fit"
            >
              Download PDF
            </a>
            <iframe
              src={entry.pdf_url}
              className="w-full rounded-xl border border-neutral-200"
              style={{ height: 600 }}
              title="Sealed agreement PDF"
            />
          </div>
        ) : entry.pdf_status === "generating" ? (
          <div className="flex items-center gap-2 text-sm text-blue-600">
            <span className="animate-spin">⏳</span>
            <span>Generating PDF… refresh in a moment.</span>
          </div>
        ) : entry.pdf_status === "failed" ? (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-red-600">PDF export failed.</p>
            <button
              onClick={() => retryMutation.mutate()}
              disabled={retryMutation.isPending}
              className="px-4 py-2 rounded-full border border-red-200 text-red-600 text-sm font-medium hover:bg-red-50 transition-colors w-fit"
            >
              {retryMutation.isPending ? "Retrying…" : "Retry export"}
            </button>
          </div>
        ) : (
          <p className="text-sm text-neutral-400">PDF pending.</p>
        )}
      </div>

    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <p className="text-sm text-neutral-500">{label}</p>
      <p className="text-sm font-medium text-neutral-800 text-right capitalize">{value}</p>
    </div>
  );
}
