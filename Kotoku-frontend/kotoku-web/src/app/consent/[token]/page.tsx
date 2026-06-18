import { ShieldCheck } from "lucide-react";

import { getPublicConsent } from "@/api/publicConsent";
import { KotokuLogo } from "@/components/brand/KotokuLogo";
import { ConsentConfirmForm } from "./ConsentConfirmForm";

function formatLabel(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export default async function PublicConsentPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;

  let context: Awaited<ReturnType<typeof getPublicConsent>> | null = null;
  let error: string | null = null;
  try {
    context = await getPublicConsent(token);
  } catch (err) {
    error = err instanceof Error ? err.message : "This consent link is invalid or expired.";
  }

  if (!context) {
    return (
      <main className="min-h-screen bg-neutral-50 px-5 py-10">
        <div className="mx-auto max-w-xl rounded-3xl border border-red-100 bg-white p-6 shadow-sm">
          <KotokuLogo />
          <h1 className="mt-8 text-2xl font-bold text-neutral-900">Consent link unavailable</h1>
          <p className="mt-3 text-sm leading-6 text-neutral-600">
            {error ?? "This consent link is invalid or expired. Ask the agreement creator to request new consent codes."}
          </p>
        </div>
      </main>
    );
  }

  const { agreement, party, parties, consent_record: record } = context;
  const details = Object.entries(agreement.field_data ?? {}).filter(
    ([, value]) => value !== null && value !== undefined && value !== "",
  );

  return (
    <main className="min-h-screen bg-neutral-50 px-5 py-8">
      <div className="mx-auto max-w-2xl space-y-5">
        <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <KotokuLogo />
          <div className="mt-8 inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-blue-700">
            <ShieldCheck size={13} />
            View-only consent
          </div>
          <h1 className="mt-4 text-3xl font-bold tracking-tight text-neutral-900">
            Review before you consent
          </h1>
          <p className="mt-3 text-sm leading-6 text-neutral-600">
            You are confirming as <strong>{party.display_name}</strong>. Enter only the OTP sent to
            <strong> {party.phone}</strong>. This page cannot edit or seal the agreement.
          </p>
        </div>

        <section className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-neutral-900">{agreement.title}</h2>
          <p className="mt-1 text-sm text-neutral-500">{formatLabel(agreement.scenario_template)}</p>
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

        <section className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-neutral-900">Agreement details</h2>
          {details.length > 0 ? (
            <dl className="mt-4 divide-y divide-neutral-100">
              {details.map(([key, value]) => (
                <div key={key} className="grid gap-1 py-3 sm:grid-cols-2">
                  <dt className="text-sm font-medium text-neutral-500">{formatLabel(key)}</dt>
                  <dd className="text-sm text-neutral-900">{String(value)}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="mt-3 text-sm text-neutral-500">No extra details were provided.</p>
          )}
        </section>

        <ConsentConfirmForm
          alreadyGranted={Boolean(record?.granted)}
          token={token}
        />
      </div>
    </main>
  );
}
