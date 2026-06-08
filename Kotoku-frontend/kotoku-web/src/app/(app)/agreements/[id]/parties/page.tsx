"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, UserRound } from "lucide-react";
import { agreementsApi } from "@/api/agreements";
import { partiesApi } from "@/api/parties";
import { SCENARIO_MAP, ROLE_LABEL, ID_TYPE_LABEL } from "@/constants/scenarios";
import type { PartyInput, PartyRole, IdType } from "@/types/party";

const ROLES: PartyRole[] = ["buyer", "seller", "landlord", "tenant", "witness"];
const ID_TYPES: IdType[] = ["ghana_card", "passport", "national_id"];

const EMPTY_PARTY: PartyInput = {
  role: "buyer",
  full_name: "",
  phone: "",
  id_type: "ghana_card",
  id_number: "",
};

// ── Validation ─────────────────────────────────────────────────────────────

interface PartyFieldErrors {
  full_name?: string;
  phone?: string;
  id_number?: string;
}

function validateParty(p: PartyInput): PartyFieldErrors {
  const errors: PartyFieldErrors = {};
  if (p.full_name.trim().length > 0 && p.full_name.trim().length < 2) {
    errors.full_name = "At least 2 characters required";
  }
  if (p.phone.length > 0) {
    const norm = p.phone.replace(/\s/g, "");
    if (!/^(\+\d{10,15}|\d{10,15})$/.test(norm)) {
      errors.phone = "Enter a valid phone number (e.g. +233501234567 or 0501234567)";
    }
  }
  if (p.id_number.trim().length > 0 && p.id_number.trim().length < 3) {
    errors.id_number = "ID number too short (min 3 characters)";
  }
  return errors;
}

function isPartyComplete(p: PartyInput): boolean {
  const norm = p.phone.replace(/\s/g, "");
  return (
    p.full_name.trim().length >= 2 &&
    /^(\+\d{10,15}|\d{10,15})$/.test(norm) &&
    p.id_number.trim().length >= 3
  );
}

// ── PartyCard ───────────────────────────────────────────────────────────────

function PartyCard({
  party,
  onEdit,
}: {
  party: PartyInput & { id?: number };
  onEdit: () => void;
}) {
  return (
    <div className="flex items-start justify-between p-4 rounded-xl border border-neutral-100 bg-white">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-full bg-neutral-100 flex items-center justify-center text-sm font-bold text-neutral-600 shrink-0 mt-0.5">
          {party.full_name.charAt(0).toUpperCase() || "?"}
        </div>
        <div>
          <p className="font-medium text-sm">{party.full_name || "Unnamed"}</p>
          <p className="text-xs text-neutral-500 mt-0.5">
            {ROLE_LABEL[party.role]} · {party.phone || "no phone"}
          </p>
          <p className="text-xs text-neutral-400 mt-0.5">
            {ID_TYPE_LABEL[party.id_type]} — {party.id_number || "no ID number"}
          </p>
        </div>
      </div>
      <button
        onClick={onEdit}
        className="text-xs text-neutral-400 hover:text-neutral-700 px-2 py-1 rounded"
      >
        Edit
      </button>
    </div>
  );
}

// ── PartyForm ───────────────────────────────────────────────────────────────

function PartyForm({
  initial,
  allowedRoles,
  usedRoles,
  onSave,
  onCancel,
}: {
  initial: PartyInput;
  allowedRoles: PartyRole[];
  usedRoles: Set<PartyRole>;
  onSave: (p: PartyInput) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<PartyInput>(initial);
  const [attempted, setAttempted] = useState(false);

  function set(key: keyof PartyInput, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  const fieldErrors = validateParty(form);
  const valid = isPartyComplete(form);

  function handleSave() {
    setAttempted(true);
    if (!valid) return;
    onSave(form);
  }

  const showError = (key: keyof PartyFieldErrors) =>
    attempted ? fieldErrors[key] : undefined;

  return (
    <div className="rounded-2xl border border-neutral-200 p-5 flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-xs font-medium text-neutral-600">Role</label>
          <select
            value={form.role}
            onChange={(e) => set("role", e.target.value)}
            className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            {ROLES.filter((r) => allowedRoles.includes(r) || r === form.role || r === "witness").map((r) => (
              <option key={r} value={r} disabled={usedRoles.has(r) && r !== form.role}>
                {ROLE_LABEL[r]}
                {usedRoles.has(r) && r !== form.role ? " (taken)" : ""}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs font-medium text-neutral-600">
            Full name <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            placeholder="As on ID document"
            value={form.full_name}
            onChange={(e) => set("full_name", e.target.value)}
            className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 ${
              showError("full_name") ? "border-red-400" : "border-neutral-200"
            }`}
          />
          {showError("full_name") && (
            <p className="mt-1 text-xs text-red-500">{showError("full_name")}</p>
          )}
        </div>
        <div>
          <label className="text-xs font-medium text-neutral-600">
            Phone number <span className="text-red-400">*</span>
          </label>
          <input
            type="tel"
            placeholder="+233XXXXXXXXX or 0XXXXXXXXX"
            value={form.phone}
            onChange={(e) => set("phone", e.target.value)}
            className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 ${
              showError("phone") ? "border-red-400" : "border-neutral-200"
            }`}
          />
          {showError("phone") ? (
            <p className="mt-1 text-xs text-red-500">{showError("phone")}</p>
          ) : (
            <p className="mt-1 text-xs text-neutral-400">E.164 or local format</p>
          )}
        </div>
        <div>
          <label className="text-xs font-medium text-neutral-600">
            ID type <span className="text-red-400">*</span>
          </label>
          <select
            value={form.id_type}
            onChange={(e) => set("id_type", e.target.value)}
            className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            {ID_TYPES.map((t) => (
              <option key={t} value={t}>
                {ID_TYPE_LABEL[t]}
              </option>
            ))}
          </select>
        </div>
        <div className="col-span-2">
          <label className="text-xs font-medium text-neutral-600">
            ID number <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            placeholder="e.g. GHA-123456789-0"
            value={form.id_number}
            onChange={(e) => set("id_number", e.target.value)}
            className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 ${
              showError("id_number") ? "border-red-400" : "border-neutral-200"
            }`}
          />
          {showError("id_number") && (
            <p className="mt-1 text-xs text-red-500">{showError("id_number")}</p>
          )}
        </div>
      </div>
      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={attempted && !valid}
          className="px-4 py-2 rounded-full bg-neutral-900 text-white text-sm font-medium disabled:opacity-40 hover:bg-neutral-700 transition-colors"
        >
          Save party
        </button>
        <button
          onClick={onCancel}
          className="px-4 py-2 rounded-full border border-neutral-200 text-sm font-medium hover:bg-neutral-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ── Page ────────────────────────────────────────────────────────────────────

export default function PartiesPage() {
  const { id } = useParams<{ id: string }>();
  const agreementId = Number(id);
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: agreement } = useQuery({
    queryKey: ["agreements", agreementId],
    queryFn: () => agreementsApi.get(agreementId),
  });

  const [draftParties, setDraftParties] = useState<PartyInput[] | null>(null);
  const [addingNew, setAddingNew] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  const parties: PartyInput[] =
    draftParties ??
    (agreement?.parties.map((p) => ({
      role: p.role as PartyRole,
      full_name: p.display_name,
      phone: p.phone,
      id_type: (p.id_type ?? "ghana_card") as IdType,
      id_number: p.id_number ?? "",
    })) ?? []);

  const saveMutation = useMutation({
    mutationFn: () => partiesApi.set(agreementId, parties),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agreements", agreementId] });
      setDraftParties(null);
      // Proceed to Details step
      router.push(`/agreements/${agreementId}`);
    },
  });

  const isEditable = agreement
    ? ["draft", "active"].includes(agreement.status)
    : false;

  const scenario = agreement?.scenario_template
    ? SCENARIO_MAP[agreement.scenario_template]
    : null;

  const allowedRoles: PartyRole[] = scenario
    ? (scenario.roles as PartyRole[]).concat(["witness"])
    : ROLES;

  const usedRoles = new Set<PartyRole>(parties.map((p) => p.role));
  const isDirty = draftParties !== null;

  // All parties must be complete (no incomplete entries allowed to save)
  const allPartiesComplete = parties.length >= 2 && parties.every(isPartyComplete);

  function addParty(p: PartyInput) {
    setDraftParties([...parties, p]);
    setAddingNew(false);
  }

  function updateParty(index: number, p: PartyInput) {
    const next = [...parties];
    next[index] = p;
    setDraftParties(next);
    setEditingIndex(null);
  }

  function removeParty(index: number) {
    setDraftParties(parties.filter((_, i) => i !== index));
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold tracking-tight">Parties</h1>
        {scenario && (
          <p className="text-xs text-neutral-400">
            Required: {scenario.roles.map((r) => ROLE_LABEL[r]).join(" + ")}
          </p>
        )}
      </div>

      <p className="text-sm text-neutral-500">
        Add at least 2 parties. Each non-witness party must have a full name,
        phone number, ID type, and ID number before you can proceed.
      </p>

      {parties.length === 0 && !addingNew && (
        <div className="rounded-2xl border border-dashed border-neutral-200 p-8 text-center text-neutral-400">
          <div className="w-12 h-12 rounded-full bg-neutral-100 flex items-center justify-center mb-2 mx-auto">
            <UserRound size={22} className="text-neutral-400" strokeWidth={1.5} />
          </div>
          <p className="font-medium text-neutral-600">No parties yet</p>
          <p className="text-sm mt-1">Add at least 2 parties before sealing.</p>
        </div>
      )}

      {/* Party list */}
      <div className="flex flex-col gap-2">
        {parties.map((p, i) =>
          editingIndex === i ? (
            <PartyForm
              key={i}
              initial={p}
              allowedRoles={allowedRoles}
              usedRoles={usedRoles}
              onSave={(updated) => updateParty(i, updated)}
              onCancel={() => setEditingIndex(null)}
            />
          ) : (
            <div key={i} className="relative group">
              <PartyCard
                party={p}
                onEdit={() => isEditable ? setEditingIndex(i) : undefined}
              />
              {isEditable && editingIndex === null && (
                <button
                  onClick={() => removeParty(i)}
                  className="absolute top-3 right-12 text-xs text-neutral-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  Remove
                </button>
              )}
            </div>
          )
        )}
      </div>

      {/* Add new party form */}
      {addingNew && (
        <PartyForm
          initial={{ ...EMPTY_PARTY, role: allowedRoles.find((r) => !usedRoles.has(r)) ?? "witness" }}
          allowedRoles={allowedRoles}
          usedRoles={usedRoles}
          onSave={addParty}
          onCancel={() => setAddingNew(false)}
        />
      )}

      {/* Actions */}
      {isEditable && !addingNew && editingIndex === null && (
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => setAddingNew(true)}
            className="px-4 py-2 rounded-full border border-neutral-200 text-sm font-medium hover:bg-neutral-50"
          >
            + Add party
          </button>

          {isDirty && (
            <button
              onClick={() => setDraftParties(null)}
              className="text-sm text-neutral-400 hover:text-neutral-600"
            >
              Discard changes
            </button>
          )}
        </div>
      )}

      {saveMutation.isError && (
        <p className="text-sm text-red-600">
          Could not save parties. Check phone format and try again.
        </p>
      )}

      {/* Proceed CTA — shown when we have ≥2 complete parties and there are unsaved changes or it's the initial state */}
      {parties.length >= 2 && allPartiesComplete && !addingNew && editingIndex === null && (
        <div className="rounded-xl bg-emerald-50 px-4 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-1.5 text-sm text-emerald-700">
            <Check size={14} className="shrink-0" strokeWidth={2.5} />
            {parties.length} parties recorded
          </div>
          <button
            onClick={() => {
              if (isDirty) {
                saveMutation.mutate();
              } else {
                router.push(`/agreements/${agreementId}`);
              }
            }}
            disabled={saveMutation.isPending}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-neutral-900 text-white text-xs font-medium disabled:opacity-50 hover:bg-neutral-700 transition-colors shrink-0"
          >
            {saveMutation.isPending ? "Saving…" : (
              <><span>Proceed to Details</span><ArrowRight size={12} /></>
            )}
          </button>
        </div>
      )}

      {parties.length >= 2 && !allPartiesComplete && (
        <p className="text-xs text-amber-600">
          Some party entries are incomplete. Fill in all required fields for every party before proceeding.
        </p>
      )}
    </div>
  );
}
