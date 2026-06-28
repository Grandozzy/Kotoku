import Link from "next/link";
import { Download, FileText, ShieldCheck } from "lucide-react";

import { getPublicVaultReceipt } from "@/api/publicVaultReceipt";
import { KotokuLogo } from "@/components/brand/KotokuLogo";

function formatLabel(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatBytes(value: number | null) {
  if (!value) return "Size unavailable";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export default async function PublicVaultReceiptPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;

  let context: Awaited<ReturnType<typeof getPublicVaultReceipt>> | null = null;
  let error: string | null = null;
  try {
    context = await getPublicVaultReceipt(token);
  } catch (err) {
    error = err instanceof Error ? err.message : "This sealed receipt link is invalid or expired.";
  }

  if (!context) {
    return (
      <main className="min-h-screen bg-neutral-50 px-5 py-10">
        <div className="mx-auto max-w-xl rounded-3xl border border-red-100 bg-white p-6 shadow-sm">
          <KotokuLogo />
          <h1 className="mt-8 text-2xl font-bold text-neutral-900">Receipt unavailable</h1>
          <p className="mt-3 text-sm leading-6 text-neutral-600">
            {error ?? "This sealed receipt link is invalid or expired."}
          </p>
        </div>
      </main>
    );
  }

  const { agreement, party, parties, evidence, vault_entry: vaultEntry } = context;
  const details = Object.entries(agreement.field_data ?? {}).filter(
    ([, value]) => value !== null && value !== undefined && value !== "",
  );

  return (
    <main className="min-h-screen bg-neutral-50 px-5 py-8">
      <div className="mx-auto max-w-3xl space-y-5">
        <section className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <KotokuLogo />
          <div className="mt-8 inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-emerald-700">
            <ShieldCheck size={13} />
            Sealed receipt
          </div>
          <h1 className="mt-4 text-3xl font-bold tracking-tight text-neutral-900">
            {agreement.title}
          </h1>
          <p className="mt-3 text-sm leading-6 text-neutral-600">
            This is a view-only receipt for <strong>{party.display_name}</strong>. To download the PDF,
            raise a dispute, or keep this agreement in your Vault, sign in with <strong>{party.phone}</strong>.
          </p>
          <div className="mt-5 flex flex-col gap-3 sm:flex-row">
            <Link
              className="inline-flex items-center justify-center rounded-full bg-neutral-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-neutral-700"
              href="/login"
            >
              Sign in to access Vault
            </Link>
            <Link
              className="inline-flex items-center justify-center rounded-full border border-neutral-200 px-5 py-3 text-sm font-semibold text-neutral-700 transition hover:bg-neutral-50"
              href="/"
            >
              Download app or continue on web
            </Link>
          </div>
        </section>

        <section className="grid gap-4 rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm sm:grid-cols-2">
          <ReceiptMetric label="Agreement ID" value={`#${agreement.id}`} />
          <ReceiptMetric label="Sealed" value={formatDate(agreement.sealed_at)} />
          <ReceiptMetric label="PDF status" value={formatLabel(vaultEntry.pdf_status)} />
          <ReceiptMetric label="Retained until" value={formatDate(vaultEntry.retain_until)} />
          <div className="sm:col-span-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-400">
              Seal hash
            </p>
            <p className="mt-1 break-all font-mono text-xs text-neutral-800">
              {agreement.seal_hash}
            </p>
          </div>
        </section>

        <section className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-neutral-900">Parties</h2>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {parties.map((item) => (
              <div key={item.id} className="rounded-2xl border border-neutral-100 bg-neutral-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-neutral-400">
                  {formatLabel(item.role)}
                </p>
                <p className="mt-1 font-semibold text-neutral-900">{item.display_name}</p>
                <p className="text-sm text-neutral-500">{item.phone}</p>
              </div>
            ))}
          </div>
        </section>

        {details.length > 0 && (
          <section className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-neutral-900">Agreement details</h2>
            <dl className="mt-4 divide-y divide-neutral-100">
              {details.map(([key, value]) => (
                <div key={key} className="grid gap-1 py-3 sm:grid-cols-2">
                  <dt className="text-sm font-medium text-neutral-500">{formatLabel(key)}</dt>
                  <dd className="text-sm text-neutral-900">{String(value)}</dd>
                </div>
              ))}
            </dl>
          </section>
        )}

        <section className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-neutral-900">Confirmed evidence</h2>
          {evidence.length > 0 ? (
            <div className="mt-5 grid gap-4">
              {evidence.map((item) => {
                const isImage = item.mime_type.startsWith("image/");
                return (
                  <div
                    key={item.id}
                    className="grid gap-4 rounded-2xl border border-neutral-100 bg-neutral-50 p-4 sm:grid-cols-[120px_1fr]"
                  >
                    <div className="flex h-28 items-center justify-center overflow-hidden rounded-xl bg-white text-xs font-semibold uppercase tracking-wide text-neutral-400">
                      {isImage && item.view_url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          alt={formatLabel(item.evidence_type)}
                          className="h-full w-full object-cover"
                          src={item.view_url}
                        />
                      ) : (
                        <FileText size={24} />
                      )}
                    </div>
                    <div>
                      <p className="font-semibold text-neutral-900">
                        {formatLabel(item.evidence_type)}
                      </p>
                      <p className="mt-1 text-sm text-neutral-500">
                        {item.original_name || formatLabel(item.file_type)} · {formatBytes(item.size_bytes)}
                      </p>
                      <p className="mt-1 text-xs text-neutral-400">
                        Added {formatDate(item.created_at)}
                      </p>
                      {item.view_url && (
                        <a
                          className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-blue-700 hover:text-blue-900"
                          href={item.view_url}
                          rel="noreferrer"
                          target="_blank"
                        >
                          <Download size={14} />
                          Open evidence
                        </a>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="mt-3 text-sm text-neutral-500">No confirmed evidence is attached.</p>
          )}
        </section>
      </div>
    </main>
  );
}

function ReceiptMetric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-400">
        {label}
      </p>
      <p className="mt-1 text-sm font-semibold text-neutral-900">{value}</p>
    </div>
  );
}
