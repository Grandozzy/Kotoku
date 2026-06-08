"use client";

import { useCallback, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, CheckCircle2, FileText, Loader2, Paperclip, Upload, XCircle } from "lucide-react";
import { agreementsApi } from "@/api/agreements";
import { evidenceApi } from "@/api/evidence";

const EVIDENCE_TYPES = [
  { value: "vehicle_photo", label: "Vehicle photo" },
  { value: "property_photo", label: "Property photo" },
  { value: "buyer_id_photo", label: "Buyer ID photo (required for sealing)" },
  { value: "seller_id_photo", label: "Seller ID photo (required for sealing)" },
  { value: "landlord_id_photo", label: "Landlord ID photo (required for sealing)" },
  { value: "tenant_id_photo", label: "Tenant ID photo (required for sealing)" },
  { value: "condition_photo", label: "Condition / defect photo" },
  { value: "signature", label: "Signature" },
  { value: "document", label: "Supporting document" },
];

interface UploadItem {
  file: File;
  evidenceType: string;
  status: "idle" | "uploading" | "done" | "error";
  errorMsg?: string;
}

async function sha256Hex(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
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

  const [items, setItems] = useState<UploadItem[]>([]);
  const [selectedType, setSelectedType] = useState(EVIDENCE_TYPES[0].value);

  const onDrop = useCallback(
    (accepted: File[]) => {
      setItems((prev) => [
        ...prev,
        ...accepted.map((file) => ({
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

  const uploadMutation = useMutation({
    mutationFn: async (item: UploadItem) => {
      const checksumSha256 = await sha256Hex(item.file);
      const init = await evidenceApi.requestUploadUrl(agreementId, {
        evidence_type: item.evidenceType,
        mime_type: item.file.type,
        size_bytes: item.file.size,
        checksum_sha256: checksumSha256,
      });
      await evidenceApi.uploadToStorage(init.upload_url, init.headers, item.file);
      await evidenceApi.confirm(agreementId, {
        file_key: init.file_key,
        evidence_type: item.evidenceType,
        mime_type: item.file.type,
        checksum_sha256: checksumSha256,
      });
      return init.evidence_id;
    },
    onMutate: (item) => {
      setItems((prev) =>
        prev.map((i) => (i === item ? { ...i, status: "uploading" } : i))
      );
    },
    onSuccess: (_, item) => {
      setItems((prev) =>
        prev.map((i) => (i === item ? { ...i, status: "done" } : i))
      );
      queryClient.invalidateQueries({ queryKey: ["agreements", agreementId] });
    },
    onError: (err: Error, item) => {
      setItems((prev) =>
        prev.map((i) =>
          i === item ? { ...i, status: "error", errorMsg: err.message } : i
        )
      );
    },
  });

  function uploadAll() {
    items
      .filter((i) => i.status === "idle" || i.status === "error")
      .forEach((i) => uploadMutation.mutate(i));
  }

  function remove(item: UploadItem) {
    setItems((prev) => prev.filter((i) => i !== item));
  }

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <h1 className="text-2xl font-bold tracking-tight">Evidence</h1>
      <p className="text-sm text-neutral-500">
        Upload photos, ID documents, and any supporting files. Drag and drop
        multiple files at once.
      </p>
      <p className="rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        Each non-witness party must have a role-specific ID photo before consent
        and sealing can complete. Use buyer/seller or landlord/tenant ID photo
        types to match the party roles on this agreement.
      </p>

      {/* Type selector */}
      <div>
        <label className="text-sm font-medium text-neutral-700">
          Evidence type for next upload
        </label>
        <select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
          className="mt-1 block w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
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
      {confirmedCount > 0 && (
        <div className="rounded-xl bg-emerald-50 px-4 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-1.5 text-sm text-emerald-700">
            <Check size={14} className="shrink-0" strokeWidth={2.5} />
            {confirmedCount} file{confirmedCount > 1 ? "s" : ""} confirmed
          </div>
          <button
            onClick={() => router.push(`/agreements/${agreementId}/consent`)}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-neutral-900 text-white text-xs font-medium hover:bg-neutral-700 transition-colors shrink-0"
          >
            <span>Proceed to Consent</span>
            <ArrowRight size={12} />
          </button>
        </div>
      )}

      {items.length > 0 && (
        <div className="flex flex-col gap-2">
          {items.map((item, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between px-4 py-2.5 rounded-xl border border-neutral-100 bg-white"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="shrink-0">
                  {item.status === "done" ? (
                    <CheckCircle2 size={18} className="text-emerald-500" strokeWidth={2} />
                  ) : item.status === "error" ? (
                    <XCircle size={18} className="text-red-500" strokeWidth={2} />
                  ) : item.status === "uploading" ? (
                    <Loader2 size={18} className="text-neutral-400 animate-spin" strokeWidth={2} />
                  ) : (
                    <FileText size={18} className="text-neutral-400" strokeWidth={1.8} />
                  )}
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{item.file.name}</p>
                  <p className="text-xs text-neutral-400">
                    {EVIDENCE_TYPES.find((t) => t.value === item.evidenceType)?.label}
                    {item.errorMsg && (
                      <span className="text-red-500"> · {item.errorMsg}</span>
                    )}
                  </p>
                </div>
              </div>
              {item.status === "idle" && (
                <button
                  onClick={() => remove(item)}
                  className="text-xs text-neutral-400 hover:text-red-500 ml-2"
                >
                  Remove
                </button>
              )}
            </div>
          ))}
          <button
            onClick={uploadAll}
            disabled={uploadMutation.isPending}
            className="mt-2 px-5 py-2.5 rounded-full bg-neutral-900 text-white text-sm font-medium disabled:opacity-50 hover:bg-neutral-700 transition-colors w-fit"
          >
            {uploadMutation.isPending ? "Uploading…" : "Upload all"}
          </button>
        </div>
      )}
    </div>
  );
}
