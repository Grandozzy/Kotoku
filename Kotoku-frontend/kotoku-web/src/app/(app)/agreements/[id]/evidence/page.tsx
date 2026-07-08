"use client";

import { useCallback, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Check,
  CheckCircle2,
  FileText,
  Loader2,
  Paperclip,
  RefreshCw,
  Trash2,
  Upload,
  XCircle,
} from "lucide-react";
import { agreementsApi } from "@/api/agreements";
import type { EvidenceItemResponse } from "@/api/evidence";
import type { Agreement, EvidenceItem } from "@/types/agreement";
import {
  uploadEvidenceFile,
  type UploadPhase,
} from "@/components/evidence/evidenceUploadService";

const EVIDENCE_TYPES = [
  { value: "vehicle_photo", label: "Vehicle photo" },
  { value: "property_photo", label: "Property photo" },
  { value: "condition_photo", label: "Condition / defect photo" },
  { value: "signature", label: "Signature" },
  { value: "document", label: "Supporting document" },
];

interface UploadItem {
  id: string;
  file: File;
  evidenceType: string;
  status: "idle" | UploadPhase | "done" | "error";
  remoteId?: number;
  errorMsg?: string;
}

function createUploadId(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function toAgreementEvidence(item: EvidenceItemResponse): EvidenceItem {
  return {
    id: item.id,
    evidence_type: item.evidence_type,
    file_type: item.file_type,
    upload_status: item.upload_status,
    created_at: item.created_at,
  };
}

export default function EvidencePage() {
  const { id } = useParams<{ id: string }>();
  const agreementId = Number(id);
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: agreement } = useQuery({
    queryKey: ["agreements", agreementId],
    queryFn: () => agreementsApi.get(agreementId),
  });

  const confirmedCount =
    agreement?.evidence_items?.filter((e) => e.upload_status === "confirmed").length ?? 0;
  const confirmedIds = new Set(
    agreement?.evidence_items
      ?.filter((e) => e.upload_status === "confirmed")
      .map((e) => e.id) ?? []
  );

  const [items, setItems] = useState<UploadItem[]>([]);
  const [selectedType, setSelectedType] = useState(EVIDENCE_TYPES[0].value);
  const localConfirmedCount = items.filter(
    (item) => item.status === "done" && !confirmedIds.has(item.remoteId ?? -1)
  ).length;
  const effectiveConfirmedCount = confirmedCount + localConfirmedCount;
  const canProceed = effectiveConfirmedCount > 0;
  const uploadableCount = items.filter(
    (item) => item.status === "idle" || item.status === "error"
  ).length;
  const uploadInProgress = items.some(
    (item) =>
      item.status === "hashing" ||
      item.status === "uploading" ||
      item.status === "confirming"
  );

  const onDrop = useCallback(
    (accepted: File[]) => {
      setItems((prev) => [
        ...prev,
        ...accepted.map((file) => ({
          id: createUploadId(),
          file,
          evidenceType: selectedType,
          status: "idle" as const,
        })),
      ]);
    },
    [selectedType]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [], "application/pdf": [] },
    multiple: true,
  });

  async function uploadItem(item: UploadItem) {
    try {
      setItems((prev) =>
        prev.map((i) =>
          i.id === item.id ? { ...i, status: "hashing", errorMsg: undefined } : i
        )
      );
      const evidence = await uploadEvidenceFile({
        agreementId,
        evidenceType: item.evidenceType,
        file: item.file,
        onPhaseChange: (phase) => {
          setItems((prev) =>
            prev.map((i) =>
              i.id === item.id
                ? { ...i, status: phase, errorMsg: undefined }
                : i
            )
          );
        },
      });
      setItems((prev) =>
        prev.map((i) =>
          i.id === item.id ? { ...i, status: "done", remoteId: evidence.id } : i
        )
      );
      queryClient.setQueryData<Agreement>(
        ["agreements", agreementId],
        (current) => {
          if (!current) return current;
          const nextEvidence = toAgreementEvidence(evidence);
          const existing = current.evidence_items ?? [];
          return {
            ...current,
            evidence_items: existing.some((entry) => entry.id === nextEvidence.id)
              ? existing.map((entry) =>
                  entry.id === nextEvidence.id ? nextEvidence : entry
                )
              : [...existing, nextEvidence],
          };
        }
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["agreements", agreementId] }),
        queryClient.invalidateQueries({ queryKey: ["agreements"] }),
      ]);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Upload failed. Please try again.";
      setItems((prev) =>
        prev.map((i) =>
          i.id === item.id ? { ...i, status: "error", errorMsg: message } : i
        )
      );
    }
  }

  function uploadAll() {
    items
      .filter((i) => i.status === "idle" || i.status === "error")
      .forEach((i) => {
        void uploadItem(i);
      });
  }

  function remove(item: UploadItem) {
    setItems((prev) => prev.filter((i) => i.id !== item.id));
  }

  function statusLabel(status: UploadItem["status"]): string {
    if (status === "hashing") return "Preparing";
    if (status === "uploading") return "Uploading";
    if (status === "confirming") return "Confirming";
    if (status === "done") return "Confirmed";
    if (status === "error") return "Upload failed";
    return "Ready";
  }

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <h1 className="text-2xl font-bold tracking-tight">Evidence</h1>
      <p className="text-sm text-neutral-500">
        Upload photos and any supporting files. Drag and drop
        multiple files at once.
      </p>
      <p className="rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        Ghana Card identity capture now happens in the Parties step. Use this page for
        asset photos, condition photos, signatures, and supporting documents.
      </p>

      {/* Type selector */}
      <div>
        <label className="text-sm font-medium text-neutral-700">
          Evidence type for next upload
        </label>
        <select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
          className="mt-1 block w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {EVIDENCE_TYPES.map(({ value, label }) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`rounded-2xl border-2 border-dashed px-6 py-12 text-center cursor-pointer transition-colors ${
          isDragActive
            ? "border-emerald-400 bg-emerald-50"
            : "border-neutral-200 hover:border-neutral-300 bg-neutral-50"
        }`}
      >
        <input {...getInputProps()} />
        <div className="flex justify-center mb-3">
          {isDragActive
            ? <Upload size={28} className="text-emerald-500" strokeWidth={1.5} />
            : <Paperclip size={28} className="text-neutral-400" strokeWidth={1.5} />
          }
        </div>
        <p className="text-sm font-medium text-neutral-700">
          {isDragActive ? "Drop files here" : "Drag photos or documents here"}
        </p>
        <p className="text-xs text-neutral-400 mt-1">
          or click to browse · images and PDFs supported
        </p>
      </div>

      {/* Queue */}
      {canProceed && (
        <div className="rounded-xl bg-emerald-50 px-4 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-1.5 text-sm text-emerald-700">
            <Check size={14} className="shrink-0" strokeWidth={2.5} />
            {effectiveConfirmedCount} file{effectiveConfirmedCount > 1 ? "s" : ""} confirmed
          </div>
          <button
            onClick={() => router.push(`/agreements/${agreementId}/review`)}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-neutral-900 text-white text-xs font-medium hover:bg-neutral-700 transition-colors shrink-0"
          >
            <span>Review agreement</span>
            <ArrowRight size={12} />
          </button>
        </div>
      )}

      {items.length > 0 && (
        <div className="flex flex-col gap-2">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between px-4 py-2.5 rounded-xl border border-neutral-100 bg-white"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="shrink-0">
                  {item.status === "done" ? (
                    <CheckCircle2 size={18} className="text-emerald-500" strokeWidth={2} />
                  ) : item.status === "error" ? (
                    <XCircle size={18} className="text-red-500" strokeWidth={2} />
                  ) : item.status === "hashing" ||
                    item.status === "uploading" ||
                    item.status === "confirming" ? (
                    <Loader2 size={18} className="text-neutral-400 animate-spin" strokeWidth={2} />
                  ) : (
                    <FileText size={18} className="text-neutral-400" strokeWidth={1.8} />
                  )}
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{item.file.name}</p>
                  <p className="text-xs text-neutral-400">
                    {EVIDENCE_TYPES.find((t) => t.value === item.evidenceType)?.label}
                    <span> · {statusLabel(item.status)}</span>
                    {item.errorMsg && (
                      <span className="text-red-500"> · {item.errorMsg}</span>
                    )}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 ml-2">
                {item.status === "error" && (
                  <button
                    onClick={() => void uploadItem(item)}
                    aria-label={`Retry ${item.file.name}`}
                    className="text-neutral-400 hover:text-neutral-700"
                  >
                    <RefreshCw size={16} />
                  </button>
                )}
                {(item.status === "idle" || item.status === "error") && (
                  <button
                    onClick={() => remove(item)}
                    aria-label={`Remove ${item.file.name}`}
                    className="text-neutral-400 hover:text-red-500"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            </div>
          ))}
          <button
            onClick={uploadAll}
            disabled={uploadInProgress || uploadableCount === 0}
            className="mt-2 px-5 py-2.5 rounded-full bg-neutral-900 text-white text-sm font-medium disabled:opacity-50 hover:bg-neutral-700 transition-colors w-fit"
          >
            {uploadInProgress
              ? "Uploading…"
              : uploadableCount === 0
                ? "All files uploaded"
                : "Upload all"}
          </button>
        </div>
      )}
    </div>
  );
}
