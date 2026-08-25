"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, CheckCircle2, Loader2, Mail, ScanFace, Upload, UserRound } from "lucide-react";

import { agreementsApi } from "@/api/agreements";
import { partiesApi } from "@/api/parties";
import { uploadEvidenceFile, type UploadPhase } from "@/components/evidence/evidenceUploadService";
import { SCENARIO_MAP, ROLE_LABEL, ID_TYPE_LABEL } from "@/constants/scenarios";
import { getApiErrorCode, getApiErrorMessage } from "@/lib/errorHandler";
import {
  buildIdentityStatusMessage,
  GHANA_CARD_PIN_REGEX,
  formatGhanaCardPin,
  identityEvidenceType,
  isPartyIdentityComplete,
  normalizeGhanaCardPin,
} from "@/lib/partyIdentity";
import { useSessionStore } from "@/store/sessionStore";
import type { Party } from "@/types/agreement";
import type { PartyInput, PartyRole } from "@/types/party";

const ROLES: PartyRole[] = ["buyer", "seller", "landlord", "tenant", "witness"];

const EMPTY_PARTY: PartyInput = {
  role: "buyer",
  full_name: "",
  phone: "",
  id_type: "ghana_card",
  id_number: "",
};

interface PartyFieldErrors {
  full_name?: string;
  phone?: string;
  id_number?: string;
}

interface UploadState {
  phase: UploadPhase | "done" | "error";
  error?: string;
}

function describeIdentityUploadError(error: unknown): string {
  const code = getApiErrorCode(error);
  if (code === "evidence_upload_not_pending") {
    return "The upload session expired or was replaced. Choose the file again and retry.";
  }
  if (code === "evidence_mime_mismatch") {
    return "The uploaded file type did not match the original request. Choose the image again.";
  }
  if (code === "evidence_checksum_mismatch") {
    return "The uploaded file changed before confirmation. Choose the image again.";
  }
  if (code === "evidence_file_size_mismatch") {
    return "The uploaded file size changed before confirmation. Choose the image again.";
  }
  if (code === "identity_role_mismatch") {
    return "This upload slot no longer matches the selected party. Refresh and try again.";
  }
  const message = getApiErrorMessage(error, "Could not upload Ghana Card image.");
  if (message.includes("could not be verified in storage")) {
    return "The file reached storage but could not be confirmed yet. Retry in a moment.";
  }
  return message;
}

function validateParty(party: PartyInput): PartyFieldErrors {
  const errors: PartyFieldErrors = {};
  if (party.full_name.trim().length > 0 && party.full_name.trim().length < 2) {
    errors.full_name = "At least 2 characters required";
  }
  if (party.phone.length > 0) {
    const normalizedPhone = party.phone.replace(/\s/g, "");
    if (!/^(\+\d{10,15}|\d{10,15})$/.test(normalizedPhone)) {
      errors.phone = "Enter a valid phone number (e.g. +233501234567 or 0501234567)";
    }
  }
  if (
    party.id_number.trim().length > 0 &&
    !GHANA_CARD_PIN_REGEX.test(normalizeGhanaCardPin(party.id_number))
  ) {
    errors.id_number = "Use the Ghana Card PIN format GHA-000000000-0";
  }
  return errors;
}

function isPartyComplete(party: PartyInput): boolean {
  const normalizedPhone = party.phone.replace(/\s/g, "");
  return (
    party.full_name.trim().length >= 2 &&
    /^(\+\d{10,15}|\d{10,15})$/.test(normalizedPhone) &&
    GHANA_CARD_PIN_REGEX.test(normalizeGhanaCardPin(party.id_number))
  );
}

function PartyCard({ party, onEdit }: { party: PartyInput; onEdit: () => void }) {
  return (
    <div className="flex items-start justify-between rounded-xl border border-neutral-100 bg-white p-4">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-neutral-100 text-sm font-bold text-neutral-600">
          {party.full_name.charAt(0).toUpperCase() || "?"}
        </div>
        <div>
          <p className="text-sm font-medium">{party.full_name || "Unnamed"}</p>
          <p className="mt-0.5 text-xs text-neutral-500">
            {ROLE_LABEL[party.role]} · {party.phone || "no phone"}
          </p>
          <p className="mt-0.5 text-xs text-neutral-500">
            {ID_TYPE_LABEL[party.id_type]} — {party.id_number || "no ID number"}
          </p>
        </div>
      </div>
      <button
        onClick={onEdit}
        className="rounded px-2 py-1 text-xs text-neutral-400 hover:text-neutral-700"
      >
        Edit
      </button>
    </div>
  );
}

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
  onSave: (party: PartyInput) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<PartyInput>(initial);
  const [attempted, setAttempted] = useState(false);

  function setField(key: keyof PartyInput, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  const fieldErrors = validateParty(form);
  const valid = isPartyComplete(form);

  function handleSave() {
    setAttempted(true);
    if (!valid) return;
    onSave({
      ...form,
      id_type: "ghana_card",
      id_number: normalizeGhanaCardPin(form.id_number),
    });
  }

  const showError = (key: keyof PartyFieldErrors) => (attempted ? fieldErrors[key] : undefined);

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-neutral-200 p-5">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label className="text-xs font-medium text-neutral-600">Role</label>
          <select
            value={form.role}
            onChange={(event) => setField("role", event.target.value)}
            className="form-control mt-1"
          >
            {ROLES.filter(
              (role) => allowedRoles.includes(role) || role === form.role || role === "witness",
            ).map((role) => (
              <option
                key={role}
                value={role}
                disabled={usedRoles.has(role) && role !== form.role}
              >
                {ROLE_LABEL[role]}
                {usedRoles.has(role) && role !== form.role ? " (taken)" : ""}
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
            placeholder="As on Ghana Card"
            value={form.full_name}
            onChange={(event) => setField("full_name", event.target.value)}
            className={`form-control mt-1 ${showError("full_name") ? "form-control-error" : ""}`}
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
            onChange={(event) => setField("phone", event.target.value)}
            className={`form-control mt-1 ${showError("phone") ? "form-control-error" : ""}`}
          />
          {showError("phone") ? (
            <p className="mt-1 text-xs text-red-500">{showError("phone")}</p>
          ) : (
            <p className="form-help-strong">E.164 or local format</p>
          )}
        </div>
        <div>
          <label className="text-xs font-medium text-neutral-600">ID type</label>
          <div className="mt-1 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-700">
            Ghana Card
          </div>
        </div>
        <div className="col-span-2">
          <label className="text-xs font-medium text-neutral-600">
            Ghana Card PIN <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            placeholder="e.g. GHA-123456789-0"
            value={form.id_number}
            onChange={(event) => setField("id_number", formatGhanaCardPin(event.target.value))}
            className={`form-control mt-1 ${showError("id_number") ? "form-control-error" : ""}`}
          />
          {showError("id_number") && (
            <p className="mt-1 text-xs text-red-500">{showError("id_number")}</p>
          )}
        </div>
      </div>
      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          onClick={handleSave}
          disabled={attempted && !valid}
          className="btn-primary px-4 py-2"
        >
          Save party
        </button>
        <button
          onClick={onCancel}
          className="rounded-full border border-neutral-200 px-4 py-2 text-sm font-medium hover:bg-neutral-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

function IdentityUploadButton({
  label,
  viewUrl,
  status,
  onSelect,
}: {
  label: string;
  viewUrl?: string | null;
  status?: UploadState;
  onSelect: (file: File) => void;
}) {
  const busy =
    status?.phase === "hashing" ||
    status?.phase === "uploading" ||
    status?.phase === "confirming";
  return (
    <label
      className={`flex cursor-pointer items-center justify-between rounded-xl border px-3 py-3 text-sm ${viewUrl ? "border-emerald-200 bg-emerald-50" : "border-neutral-200 bg-white"} ${busy ? "opacity-70" : ""}`}
    >
      <div className="flex flex-col gap-1">
        <span className="font-medium text-neutral-800">{label}</span>
        <span className="text-xs text-neutral-500">
          {status?.phase === "error"
            ? (status.error ?? "Upload failed")
            : viewUrl
              ? "Confirmed"
              : "Upload required"}
        </span>
      </div>
      <div className="flex items-center gap-2 text-xs font-medium text-neutral-700">
        {busy ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
        <span>{viewUrl ? "Replace" : "Upload"}</span>
      </div>
      <input
        type="file"
        accept="image/*"
        className="hidden"
        disabled={busy}
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.currentTarget.value = "";
          if (file) onSelect(file);
        }}
      />
    </label>
  );
}

function OwnIdentitySection({
  party,
  uploadStates,
  onUpload,
}: {
  party: Party;
  uploadStates: Record<string, UploadState>;
  onUpload: (party: Party, side: "front" | "back", file: File) => Promise<void>;
}) {
  const complete = isPartyIdentityComplete(party);

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-neutral-900">{party.display_name}</p>
          <p className="mt-0.5 text-xs text-neutral-500">
            {ROLE_LABEL[party.role as PartyRole]} · {party.id_number}
          </p>
          <p
            className={`mt-1 text-xs ${
              party.identity_verification_status === "verified"
                ? "text-emerald-700"
                : party.identity_verification_status === "failed" ||
                    party.identity_verification_status === "manual_review_required"
                  ? "text-red-600"
                  : "text-neutral-500"
            }`}
          >
            {buildIdentityStatusMessage(party)}
          </p>
        </div>
        {complete && <CheckCircle2 size={18} className="shrink-0 text-emerald-600" strokeWidth={2} />}
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        <IdentityUploadButton
          label="Ghana Card front"
          viewUrl={party.ghana_card_front_view_url}
          status={uploadStates[`${party.role}:front`]}
          onSelect={(file) => void onUpload(party, "front", file)}
        />
        <IdentityUploadButton
          label="Ghana Card back"
          viewUrl={party.ghana_card_back_view_url}
          status={uploadStates[`${party.role}:back`]}
          onSelect={(file) => void onUpload(party, "back", file)}
        />
        <div
          className={`flex items-center justify-between rounded-xl border px-3 py-3 text-sm ${party.liveness_status === "passed" ? "border-emerald-200 bg-emerald-50" : party.liveness_status === "failed" ? "border-red-200 bg-red-50" : "border-neutral-200 bg-neutral-50"}`}
        >
          <div className="flex items-center gap-2">
            <ScanFace size={15} className="shrink-0 text-neutral-400" strokeWidth={1.8} />
            <div className="flex flex-col gap-0.5">
              <span className="text-xs font-medium text-neutral-800">Face check</span>
              <span
                className={`text-xs ${party.liveness_status === "passed" ? "text-emerald-700" : party.liveness_status === "failed" ? "text-red-600" : "text-neutral-500"}`}
              >
                {party.liveness_status === "passed"
                  ? "Passed"
                  : party.liveness_status === "failed"
                    ? "Failed — retry on mobile"
                    : "Pending — complete on mobile"}
              </span>
            </div>
          </div>
          {party.liveness_status === "passed" && (
            <Check size={14} className="text-emerald-600 shrink-0" strokeWidth={2.5} />
          )}
        </div>
      </div>
    </div>
  );
}

function CounterpartyInviteSection({
  party,
  agreementId,
  onInviteSent,
}: {
  party: Party;
  agreementId: number;
  onInviteSent: () => void;
}) {
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [inviteSent, setInviteSent] = useState(false);
  const complete = isPartyIdentityComplete(party);

  async function handleSendInvite() {
    setSending(true);
    setSendError(null);
    try {
      await partiesApi.sendInvite(agreementId, party.role);
      setInviteSent(true);
      onInviteSent();
    } catch (err) {
      setSendError(getApiErrorMessage(err, "Could not send invite. Please try again."));
    } finally {
      setSending(false);
    }
  }

  const isProcessing =
    party.identity_verification_status === "processing" ||
    (party.identity_verification_status === "pending" && inviteSent);

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-neutral-900">{party.display_name}</p>
          <p className="mt-0.5 text-xs text-neutral-500">
            {ROLE_LABEL[party.role as PartyRole]} · {party.id_number}
          </p>
          <p
            className={`mt-1 text-xs ${
              complete
                ? "text-emerald-700"
                : party.identity_verification_status === "failed" ||
                    party.identity_verification_status === "manual_review_required"
                  ? "text-red-600"
                  : "text-neutral-500"
            }`}
          >
            {buildIdentityStatusMessage(party)}
          </p>
        </div>
        {complete && <CheckCircle2 size={18} className="shrink-0 text-emerald-600" strokeWidth={2} />}
      </div>

      {complete ? (
        <div className="mt-3 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5">
          <Check size={14} className="shrink-0 text-emerald-600" strokeWidth={2.5} />
          <p className="text-xs text-emerald-700">
            Identity verified. You can proceed once your own verification is also complete.
          </p>
        </div>
      ) : (
        <div className="mt-3 flex flex-col gap-3">
          <div className="rounded-lg border border-blue-100 bg-blue-50 px-3 py-2.5">
            <p className="text-xs text-blue-800">
              <strong>{party.display_name}</strong> needs to complete Ghana Card upload and face
              check on their own device using the Kotoku mobile app.
            </p>
          </div>

          {isProcessing && (
            <div className="flex items-center gap-2 text-xs text-neutral-500">
              <Loader2 size={12} className="animate-spin shrink-0" />
              <span>Waiting for verification to complete…</span>
            </div>
          )}

          {sendError && <p className="text-xs text-red-600">{sendError}</p>}

          <button
            onClick={() => void handleSendInvite()}
            disabled={sending}
            className="inline-flex items-center gap-2 self-start rounded-full border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-800 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:border-neutral-200 disabled:bg-neutral-100 disabled:text-neutral-500"
          >
            {sending ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <Mail size={13} strokeWidth={1.8} />
            )}
            <span>{inviteSent ? "Resend invite SMS" : "Send invite SMS"}</span>
          </button>

          {inviteSent && !sendError && (
            <p className="form-help-strong">
              An SMS was sent to {party.phone}. They can open the link on their device to verify.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function PartiesPage() {
  const { id } = useParams<{ id: string }>();
  const agreementId = Number(id);
  const router = useRouter();
  const queryClient = useQueryClient();
  const creatorPhone = useSessionStore((s) => s.phone);

  const { data: agreement } = useQuery({
    queryKey: ["agreements", agreementId],
    queryFn: () => agreementsApi.get(agreementId),
  });

  const [draftParties, setDraftParties] = useState<PartyInput[] | null>(null);
  const [addingNew, setAddingNew] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [uploadStates, setUploadStates] = useState<Record<string, UploadState>>({});
  const [counterpartyInviteSent, setCounterpartyInviteSent] = useState(false);

  const parties: PartyInput[] =
    draftParties ??
    (agreement?.parties.map((party) => ({
      role: party.role as PartyRole,
      full_name: party.display_name,
      phone: party.phone,
      id_type: "ghana_card",
      id_number: party.id_number ?? "",
    })) ?? []);

  const savedParties = useMemo(() => agreement?.parties ?? [], [agreement?.parties]);

  const myParty = savedParties.find((p) => p.phone === creatorPhone) ?? null;
  const counterParties = savedParties.filter(
    (p) => p.phone !== creatorPhone && p.role !== "witness",
  );

  const saveMutation = useMutation({
    mutationFn: () =>
      partiesApi.set(
        agreementId,
        parties.map((party) => ({
          ...party,
          id_type: "ghana_card",
          id_number: normalizeGhanaCardPin(party.id_number),
        })),
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["agreements", agreementId] });
      setDraftParties(null);
    },
  });

  const isEditable = agreement ? ["draft", "active"].includes(agreement.status) : false;
  const scenario = agreement?.scenario_template ? SCENARIO_MAP[agreement.scenario_template] : null;
  const allowedRoles: PartyRole[] = scenario
    ? (scenario.roles as PartyRole[]).concat(["witness"])
    : ROLES;
  const usedRoles = new Set<PartyRole>(parties.map((party) => party.role));
  const isDirty = draftParties !== null;
  const allPartiesComplete = parties.length >= 2 && parties.every(isPartyComplete);

  const myPartyIdentityComplete = myParty ? isPartyIdentityComplete(myParty) : false;
  const allCounterpartiesComplete =
    counterParties.length > 0 && counterParties.every(isPartyIdentityComplete);
  const identityComplete = myPartyIdentityComplete && allCounterpartiesComplete;

  // Poll while own identity or any counterparty identity is in progress.
  useEffect(() => {
    const needsRefresh = savedParties.some((party) => {
      const livenessOrSelfie =
        party.liveness_status === "passed" || party.identity_selfie_uploaded;
      return (
        party.ghana_card_front_uploaded &&
        party.ghana_card_back_uploaded &&
        livenessOrSelfie &&
        (party.identity_verification_status === "pending" ||
          party.identity_verification_status === "processing")
      );
    });

    // Also poll for counterparty while invite was sent and they are still pending.
    const counterpartyPending =
      counterpartyInviteSent &&
      counterParties.some((p) => p.identity_verification_status === "pending");

    if (!needsRefresh && !counterpartyPending) return;
    const timer = window.setInterval(() => {
      void queryClient.invalidateQueries({ queryKey: ["agreements", agreementId] });
    }, 5000);
    return () => window.clearInterval(timer);
  }, [agreementId, queryClient, savedParties, counterParties, counterpartyInviteSent]);

  function addParty(party: PartyInput) {
    setDraftParties([...parties, party]);
    setAddingNew(false);
  }

  function updateParty(index: number, party: PartyInput) {
    const next = [...parties];
    next[index] = party;
    setDraftParties(next);
    setEditingIndex(null);
  }

  function removeParty(index: number) {
    setDraftParties(parties.filter((_, i) => i !== index));
  }

  async function handleIdentityUpload(party: Party, side: "front" | "back", file: File) {
    const stateKey = `${party.role}:${side}`;
    try {
      await uploadEvidenceFile({
        agreementId,
        evidenceType: identityEvidenceType(party.role, side),
        file,
        onPhaseChange: (phase) => {
          setUploadStates((prev) => ({ ...prev, [stateKey]: { phase } }));
        },
      });
      setUploadStates((prev) => ({ ...prev, [stateKey]: { phase: "done" } }));
      await queryClient.invalidateQueries({ queryKey: ["agreements", agreementId] });
    } catch (error) {
      setUploadStates((prev) => ({
        ...prev,
        [stateKey]: { phase: "error", error: describeIdentityUploadError(error) },
      }));
    }
  }

  async function handlePrimaryAction() {
    if (isDirty) {
      await saveMutation.mutateAsync();
      return;
    }
    if (identityComplete) {
      router.push(`/agreements/${agreementId}`);
    }
  }

  const showIdentitySection = !isDirty && savedParties.length >= 2;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-xl font-bold tracking-tight">Parties</h1>
        {scenario && (
          <p className="text-xs text-neutral-500">
            Required: {scenario.roles.map((r) => ROLE_LABEL[r]).join(" + ")}
          </p>
        )}
      </div>

      <p className="text-sm text-neutral-500">
        Add at least 2 parties. Once saved, each non-witness party completes their own identity
        verification on the Kotoku mobile app — you can send them an SMS invite from this page.
      </p>

      {parties.length === 0 && !addingNew && (
        <div className="rounded-2xl border border-dashed border-neutral-200 p-8 text-center text-neutral-400">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-neutral-100">
            <UserRound size={22} className="text-neutral-400" strokeWidth={1.5} />
          </div>
          <p className="font-medium text-neutral-600">No parties yet</p>
          <p className="mt-1 text-sm">Add at least 2 parties before sealing.</p>
        </div>
      )}

      <div className="flex flex-col gap-2">
        {parties.map((party, index) =>
          editingIndex === index ? (
            <PartyForm
              key={index}
              initial={party}
              allowedRoles={allowedRoles}
              usedRoles={usedRoles}
              onSave={(updated) => updateParty(index, updated)}
              onCancel={() => setEditingIndex(null)}
            />
          ) : (
            <div key={index} className="group relative">
              <PartyCard
                party={party}
                onEdit={() => {
                  if (isEditable) setEditingIndex(index);
                }}
              />
              {isEditable && editingIndex === null && (
                <button
                  onClick={() => removeParty(index)}
                  className="absolute right-12 top-3 text-xs text-neutral-300 opacity-100 transition-opacity hover:text-red-500 sm:opacity-0 sm:group-hover:opacity-100"
                >
                  Remove
                </button>
              )}
            </div>
          ),
        )}
      </div>

      {addingNew && (
        <PartyForm
          initial={{
            ...EMPTY_PARTY,
            role: allowedRoles.find((r) => !usedRoles.has(r)) ?? "witness",
          }}
          allowedRoles={allowedRoles}
          usedRoles={usedRoles}
          onSave={addParty}
          onCancel={() => setAddingNew(false)}
        />
      )}

      {isEditable && !addingNew && editingIndex === null && (
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setAddingNew(true)}
            className="rounded-full border border-neutral-200 px-4 py-2 text-sm font-medium hover:bg-neutral-50"
          >
            + Add party
          </button>
          {isDirty && (
            <button
              onClick={() => setDraftParties(null)}
              className="text-sm text-neutral-500 hover:text-neutral-700"
            >
              Discard changes
            </button>
          )}
        </div>
      )}

      {saveMutation.isError && (
        <p className="text-sm text-red-600">
          {getApiErrorMessage(
            saveMutation.error,
            "Could not save parties. Check phone format and Ghana Card PINs.",
          )}
        </p>
      )}

      {showIdentitySection && (
        <div className="flex flex-col gap-4">
          <div>
            <p className="text-sm font-semibold text-neutral-900">Identity verification</p>
            <p className="mt-1 text-xs text-neutral-500">
              Each non-witness party must upload their Ghana Card and pass a face check on the
              Kotoku mobile app. Send an invite SMS to counterparties so they can complete this on
              their own device.
            </p>
          </div>

          {myParty && (
            <OwnIdentitySection
              party={myParty}
              uploadStates={uploadStates}
              onUpload={handleIdentityUpload}
            />
          )}

          {counterParties.map((party) => (
            <CounterpartyInviteSection
              key={party.id}
              party={party}
              agreementId={agreementId}
              onInviteSent={() => setCounterpartyInviteSent(true)}
            />
          ))}
        </div>
      )}

      {parties.length >= 2 && allPartiesComplete && !addingNew && editingIndex === null && (
        <div className="flex flex-col gap-3 rounded-xl bg-emerald-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-1.5 text-sm text-emerald-700">
            <Check size={14} className="shrink-0" strokeWidth={2.5} />
            {isDirty
              ? `${parties.length} parties ready to save`
              : identityComplete
                ? `All parties saved and identity verified`
                : `${savedParties.length} parties saved — complete identity verification to continue`}
          </div>
          <button
            onClick={() => void handlePrimaryAction()}
            disabled={saveMutation.isPending || (!isDirty && !identityComplete)}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-neutral-900 px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-neutral-700 disabled:cursor-not-allowed disabled:bg-neutral-300 disabled:text-neutral-700 disabled:opacity-100"
          >
            {saveMutation.isPending ? (
              "Saving…"
            ) : (
              <>
                <span>{isDirty ? "Save party details" : "Proceed to Details"}</span>
                <ArrowRight size={12} />
              </>
            )}
          </button>
        </div>
      )}

      {parties.length >= 2 && !allPartiesComplete && (
        <p className="text-xs text-amber-600">
          Some party entries are incomplete. Fill in all required fields and valid Ghana Card PINs
          for every party before proceeding.
        </p>
      )}
    </div>
  );
}
