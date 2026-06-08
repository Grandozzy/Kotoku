"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check } from "lucide-react";
import { agreementsApi } from "@/api/agreements";
import { SCENARIO_MAP } from "@/constants/scenarios";
import type { FieldDef } from "@/constants/scenarios";

function groupBySection(fields: FieldDef[]) {
  const map: Record<string, FieldDef[]> = {};
  for (const f of fields) {
    (map[f.section] ??= []).push(f);
  }
  return map;
}

export default function AgreementDetailPage() {
  const { id } = useParams<{ id: string }>();
  const agreementId = Number(id);
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: agreement } = useQuery({
    queryKey: ["agreements", agreementId],
    queryFn: () => agreementsApi.get(agreementId),
  });

  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Record<string, unknown>>({});

  const updateMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      agreementsApi.update(agreementId, {
        field_data: data,
        scenario_template: agreement?.scenario_template ?? undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agreements", agreementId] });
      setEditing(false);
    },
  });

  if (!agreement) return null;

  const isEditable = ["draft", "active"].includes(agreement.status);
  const scenario = agreement.scenario_template
    ? SCENARIO_MAP[agreement.scenario_template]
    : null;
  const fieldData = agreement.field_data ?? {};
  const sections = scenario ? groupBySection(scenario.fields) : null;

  const requiredFields = scenario?.fields.filter((f) => f.required) ?? [];
  const missingRequired = requiredFields.filter((f) => {
    const v = fieldData[f.key];
    return v === undefined || v === null || v === "";
  });
  const detailsComplete = missingRequired.length === 0;

  function startEdit() {
    setForm({ ...fieldData });
    setEditing(true);
  }

  function handleFieldChange(key: string, value: unknown) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function renderFieldValue(f: FieldDef, value: unknown) {
    if (value === undefined || value === null || value === "") return <span className="text-neutral-300">—</span>;
    if (f.type === "boolean") return <span>{value ? "Yes" : "No"}</span>;
    if (f.type === "select") {
      const opt = f.options?.find((o) => o.value === value);
      return <span>{opt?.label ?? String(value)}</span>;
    }
    return <span>{String(value)}</span>;
  }

  function renderEditField(f: FieldDef) {
    const val = form[f.key];
    if (f.type === "boolean") {
      return (
        <select
          value={val === true ? "true" : val === false ? "false" : ""}
          onChange={(e) =>
            handleFieldChange(f.key, e.target.value === "true" ? true : e.target.value === "false" ? false : undefined)
          }
          className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          <option value="">—</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      );
    }
    if (f.type === "select") {
      return (
        <select
          value={String(val ?? "")}
          onChange={(e) => handleFieldChange(f.key, e.target.value)}
          className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          <option value="">Select…</option>
          {f.options?.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      );
    }
    return (
      <input
        type={f.type === "number" ? "number" : f.type === "date" ? "date" : "text"}
        value={String(val ?? "")}
        placeholder={f.placeholder}
        onChange={(e) =>
          handleFieldChange(
            f.key,
            f.type === "number" ? (e.target.value === "" ? "" : Number(e.target.value)) : e.target.value
          )
        }
        className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">{agreement.title}</h1>
          {agreement.description && (
            <p className="text-sm text-neutral-500 mt-1">{agreement.description}</p>
          )}
        </div>
        {isEditable && !editing && (
          <button
            onClick={startEdit}
            className="text-sm text-neutral-500 hover:text-neutral-800 px-3 py-1.5 rounded-lg hover:bg-neutral-50 border border-neutral-200"
          >
            Edit
          </button>
        )}
      </div>

      {/* No scenario set */}
      {!scenario && (
        <div className="rounded-2xl border border-dashed border-neutral-200 p-8 text-center text-neutral-400">
          <p className="font-medium text-neutral-600">No scenario selected</p>
          <p className="text-sm mt-1">
            To fill in template fields, edit the agreement and choose a scenario.
          </p>
        </div>
      )}

      {/* Scenario fields */}
      {scenario && !editing && sections && (
        <div className="flex flex-col gap-5">
          {Object.entries(sections).map(([section, fields]) => (
            <div key={section} className="rounded-2xl border border-neutral-100 overflow-hidden">
              <div className="px-4 py-3 bg-neutral-50 border-b border-neutral-100">
                <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                  {section}
                </p>
              </div>
              <div className="divide-y divide-neutral-50">
                {fields.map((f) => (
                  <div key={f.key} className="flex justify-between items-start px-4 py-3 gap-4">
                    <span className="text-sm text-neutral-500 shrink-0 w-48">{f.label}</span>
                    <span className="text-sm font-medium text-right">
                      {renderFieldValue(f, fieldData[f.key])}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Editing mode */}
      {editing && scenario && sections && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            updateMutation.mutate(form);
          }}
          className="flex flex-col gap-5"
        >
          {Object.entries(sections).map(([section, fields]) => (
            <div key={section} className="rounded-2xl border border-neutral-200 overflow-hidden">
              <div className="px-4 py-3 bg-neutral-50 border-b border-neutral-100">
                <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                  {section}
                </p>
              </div>
              <div className="divide-y divide-neutral-50">
                {fields.map((f) => (
                  <div key={f.key} className="flex items-center gap-4 px-4 py-3">
                    <label className="text-sm text-neutral-600 w-48 shrink-0">
                      {f.label}
                      {f.required && <span className="text-red-400 ml-0.5">*</span>}
                    </label>
                    <div className="flex-1">{renderEditField(f)}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={updateMutation.isPending}
              className="px-5 py-2.5 rounded-full bg-neutral-900 text-white text-sm font-medium disabled:opacity-50 hover:bg-neutral-700 transition-colors"
            >
              {updateMutation.isPending ? "Saving…" : "Save changes"}
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="px-5 py-2.5 rounded-full border border-neutral-200 text-sm font-medium hover:bg-neutral-50"
            >
              Cancel
            </button>
          </div>
          {updateMutation.isError && (
            <p className="text-sm text-red-600">Could not save. Please try again.</p>
          )}
        </form>
      )}

      {/* Proceed to Evidence CTA */}
      {!editing && (
        <>
          {agreement.status !== "sealed" && (
            <div>
              {missingRequired.length > 0 && (
                <p className="text-xs text-amber-600 mb-3">
                  Required before proceeding:{" "}
                  {missingRequired.map((f) => f.label).join(", ")}
                </p>
              )}
              {detailsComplete ? (
                <div className="rounded-xl bg-emerald-50 px-4 py-3 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-1.5 text-sm text-emerald-700">
                    <Check size={14} className="shrink-0" strokeWidth={2.5} />
                    Details complete
                  </div>
                  <button
                    onClick={() => router.push(`/agreements/${agreementId}/evidence`)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-neutral-900 text-white text-xs font-medium hover:bg-neutral-700 transition-colors shrink-0"
                  >
                    <span>Proceed to Evidence</span>
                    <ArrowRight size={12} />
                  </button>
                </div>
              ) : (
                requiredFields.length > 0 && (
                  <button
                    disabled
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-neutral-900 text-white text-xs font-medium opacity-40 cursor-not-allowed"
                  >
                    <span>Proceed to Evidence</span>
                    <ArrowRight size={12} />
                  </button>
                )
              )}
            </div>
          )}
          {agreement.status === "sealed" && (
            <div className="rounded-xl bg-emerald-50 px-4 py-3">
              <span className="inline-flex items-center gap-1.5 text-sm text-emerald-700 font-medium">
                <Check size={14} className="shrink-0" strokeWidth={2.5} />
                This agreement is sealed and stored in the vault.
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
