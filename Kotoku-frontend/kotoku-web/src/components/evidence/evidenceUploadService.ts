import {
  evidenceApi,
  type EvidenceItemResponse,
} from "@/api/evidence";

const STORAGE_UPLOAD_TIMEOUT_MS = 45_000;
const CONFIRM_RETRY_DELAYS_MS = [0, 750, 1500, 3000];
const RETRYABLE_CONFIRM_STATUSES = new Set([
  408,
  409,
  425,
  429,
  500,
  502,
  503,
  504,
]);

const MIME_BY_EXTENSION: Record<string, string> = {
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  pdf: "application/pdf",
};

export type UploadPhase = "hashing" | "uploading" | "confirming";

export interface UploadEvidenceFileInput {
  agreementId: number;
  evidenceType: string;
  file: File;
  onPhaseChange?: (phase: UploadPhase) => void;
}

interface ApiStatusError extends Error {
  response?: { status?: number };
  status?: number;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function getErrorStatus(error: unknown): number | null {
  const status =
    (error as ApiStatusError | undefined)?.response?.status ??
    (error as ApiStatusError | undefined)?.status;
  return typeof status === "number" ? status : null;
}

function shouldRetryConfirm(error: unknown): boolean {
  const status = getErrorStatus(error);
  return status === null || RETRYABLE_CONFIRM_STATUSES.has(status);
}

function getMimeType(file: File): string {
  if (file.type) return file.type;
  const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
  return MIME_BY_EXTENSION[extension] ?? "application/octet-stream";
}

async function sha256Hex(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function uploadToStorage(
  uploadUrl: string,
  headers: Record<string, string>,
  file: File,
): Promise<void> {
  const controller = new AbortController();
  let timedOut = false;
  const timeout = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, STORAGE_UPLOAD_TIMEOUT_MS);

  try {
    const response = await fetch(uploadUrl, {
      method: "PUT",
      headers,
      body: file,
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(
        `File upload failed: storage returned ${response.status}. Please try again.`,
      );
    }
  } catch (error) {
    if (timedOut) {
      throw new Error("File upload timed out before the file was fully sent.");
    }
    throw new Error(
      error instanceof Error
        ? error.message
        : "File upload failed: storage server could not be reached.",
    );
  } finally {
    clearTimeout(timeout);
  }
}

async function findConfirmedEvidence(
  agreementId: number,
  evidenceType: string,
): Promise<EvidenceItemResponse | null> {
  const evidence = await evidenceApi.list(agreementId);
  return evidence.find((item) => item.evidence_type === evidenceType) ?? null;
}

async function confirmWithRetry(
  agreementId: number,
  evidenceId: number,
  fileKey: string,
  evidenceType: string,
  mimeType: string,
  checksumSha256: string,
): Promise<EvidenceItemResponse> {
  let lastError: unknown = null;

  for (const delay of CONFIRM_RETRY_DELAYS_MS) {
    if (delay > 0) {
      await sleep(delay);
    }

    try {
      const result = await evidenceApi.confirm(agreementId, {
        evidence_id: evidenceId,
        file_key: fileKey,
        evidence_type: evidenceType,
        mime_type: mimeType,
        checksum_sha256: checksumSha256,
      });
      return result.evidence;
    } catch (error) {
      lastError = error;
      if (!shouldRetryConfirm(error)) {
        break;
      }
    }
  }

  const recovered = await findConfirmedEvidence(agreementId, evidenceType);
  if (recovered) return recovered;

  throw lastError ?? new Error("Upload could not be confirmed.");
}

export async function uploadEvidenceFile({
  agreementId,
  evidenceType,
  file,
  onPhaseChange,
}: UploadEvidenceFileInput): Promise<EvidenceItemResponse> {
  onPhaseChange?.("hashing");
  const checksumSha256 = await sha256Hex(file);
  const mimeType = getMimeType(file);
  const init = await evidenceApi.requestUploadUrl(agreementId, {
    evidence_type: evidenceType,
    mime_type: mimeType,
    size_bytes: file.size,
    checksum_sha256: checksumSha256,
  });
  const uploadHeaders =
    Object.keys(init.headers ?? {}).length > 0
      ? init.headers
      : { "Content-Type": mimeType };

  onPhaseChange?.("uploading");
  await uploadToStorage(init.upload_url, uploadHeaders, file);

  onPhaseChange?.("confirming");
  return confirmWithRetry(
    agreementId,
    init.evidence_id,
    init.file_key,
    evidenceType,
    mimeType,
    checksumSha256,
  );
}
