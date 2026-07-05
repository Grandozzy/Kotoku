"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, FileText, ImageIcon } from "lucide-react";
import { agreementsApi } from "@/api/agreements";
import { SCENARIO_MAP } from "@/constants/scenarios";

const ID_TYPE_LABEL: Record<string, string> = {
  ghana_card: "Ghana Card",
  passport: "Passport",
  national_id: "National ID Card",
};

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const agreementId = Number(id);
  const router = useRouter();

  const { data: agreement } = useQuery({
    queryKey: ["agreements", agreementId],
    queryFn: () => agreementsApi.get(agreementId),
  });

  if (!agreement) return null;

  const scenario = agreement.scenario_template
    ? SCENARIO_MAP[agreement.scenario_template]
    : null;

  const confirmedEvidence =
    agreement.evidence_items?.filter((e) => e.upload_status === "confirmed") ?? [];

  const fieldData = agreement.field_data ?? {};

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div>
        <p className="text-xs text-neutral-400 uppercase tracking-widest mb-1">Step 4 of 6</p>
        <h1 className="text-2xl font-bold tracking-tight">Review agreement</h1>
        <p className="text-sm text-neutral-500 mt-1">
          Confirm everything is correct before requesting consent from all parties.
        </p>
      </div>

      {/* Agreement title */}
      <Section title="Agreement">
        <Row label="Title" value={agreement.title} />
        {scenario && <Row label="Type" value={scenario.label} />}
        {agreement.description && <Row label="Description" value={agreement.description} />}
      </Section>

      {/* Parties */}
      <Section title="Parties">
        {agreement.parties.length === 0 ? (
          <p className="text-sm text-neutral-400 px-1">No parties added.</p>
        ) : (
          agreement.parties.map((p) => (
            <div key={p.id} className="flex flex-col gap-1 py-2 first:pt-0 last:pb-0 border-b border-neutral-50 last:border-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-neutral-800">{p.display_name}</span>
                <span className="text-xs bg-neutral-100 text-neutral-500 px-2 py-0.5 rounded-full capitalize">
                  {p.role}
                </span>
              </div>
              <p className="text-xs text-neutral-400">{p.phone}</p>
              {p.id_type && (
                <p className="text-xs text-neutral-400">
                  {ID_TYPE_LABEL[p.id_type] ?? p.id_type}
                  {p.id_number ? ` · ${p.id_number}` : ""}
                </p>
              )}
            </div>
          ))
        )}
      </Section>

      {/* Details */}
      {scenario && scenario.fields.length > 0 && (
        <Section title="Details">
          {scenario.fields.map((f) => {
            const raw = fieldData[f.key];
            if (raw === undefined || raw === null || raw === "") return null;
            let display = String(raw);
            if (f.type === "boolean") display = raw ? "Yes" : "No";
            if (f.options) {
              display = f.options.find((o) => o.value === raw)?.label ?? display;
            }
            return <Row key={f.key} label={f.label} value={display} />;
          })}
        </Section>
      )}

      {/* Evidence */}
      <Section title={`Evidence (${confirmedEvidence.length} confirmed)`}>
        {confirmedEvidence.length === 0 ? (
          <p className="text-sm text-neutral-400 px-1">No confirmed evidence.</p>
        ) : (
          confirmedEvidence.map((e) => (
            <div key={e.id} className="flex items-center gap-2 py-1.5">
              {e.file_type === "photo" || e.file_type === "image" ? (
                <ImageIcon size={14} className="text-neutral-400 shrink-0" strokeWidth={1.8} />
              ) : (
                <FileText size={14} className="text-neutral-400 shrink-0" strokeWidth={1.8} />
              )}
              <span className="text-sm text-neutral-700 capitalize">
                {e.evidence_type.replaceAll("_", " ")}
              </span>
              <CheckCircle2 size={13} className="text-emerald-500 ml-auto shrink-0" strokeWidth={2} />
            </div>
          ))
        )}
      </Section>

      {/* CTA */}
      <div className="flex items-center gap-4 pt-2">
        <button
          onClick={() => router.push(`/agreements/${agreementId}/consent`)}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-700 transition-colors"
        >
          Looks good — request consent
          <ArrowRight size={15} strokeWidth={2} />
        </button>
        <Link
          href={`/agreements/${agreementId}/evidence`}
          className="text-sm text-neutral-400 hover:text-neutral-600 transition-colors"
        >
          Edit evidence
        </Link>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-neutral-100 overflow-hidden">
      <div className="px-4 py-3 bg-neutral-50 border-b border-neutral-100">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</p>
      </div>
      <div className="px-4 py-3 flex flex-col gap-1">{children}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 py-1.5 border-b border-neutral-50 last:border-0">
      <p className="text-sm text-neutral-500 shrink-0">{label}</p>
      <p className="text-sm font-medium text-neutral-800 text-right">{value}</p>
    </div>
  );
}
