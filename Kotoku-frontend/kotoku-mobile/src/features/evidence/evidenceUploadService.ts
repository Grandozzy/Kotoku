import * as FileSystem from "expo-file-system/legacy";

import {
  confirmUpload,
  getUploadUrl,
  listEvidence,
  type EvidenceItemResponse,
} from "@/api/evidence";

const S3_UPLOAD_TIMEOUT_MS = 45_000;
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

export interface UploadEvidenceInput {
  agreementId: number;
  evidenceType: string;
  localUri: string;
  mimeType: string;
  sizeBytes: number;
  checksumSha256: string;
  onPhaseChange?: (phase: "uploading" | "confirming") => void;
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

async function uploadFileToStorage(
  uploadUrl: string,
  headers: Record<string, string>,
  localUri: string,
): Promise<void> {
  let timedOut = false;
  let timeout: ReturnType<typeof setTimeout> | null = null;
  const uploadPromise = FileSystem.uploadAsync(uploadUrl, localUri, {
    httpMethod: "PUT",
    headers,
    uploadType: FileSystem.FileSystemUploadType.BINARY_CONTENT,
    sessionType: FileSystem.FileSystemSessionType.FOREGROUND,
  }).catch((error) => {
    if (timedOut) return null;
    throw error;
  });
  const timeoutPromise = new Promise<null>((resolve) => {
    timeout = setTimeout(() => {
      timedOut = true;
      resolve(null);
    }, S3_UPLOAD_TIMEOUT_MS);
  });

  try {
    const response = await Promise.race([uploadPromise, timeoutPromise]);
    if (!response) return;
    if (response.status < 200 || response.status >= 300) {
      throw new Error(
        `S3 upload failed (${response.status}): ${response.body || "(no body)"}`,
      );
    }
  } finally {
    if (timeout) {
      clearTimeout(timeout);
    }
  }
}

async function findConfirmedEvidence(
  agreementId: number,
  evidenceType: string,
): Promise<EvidenceItemResponse | null> {
  const evidence = await listEvidence(agreementId);
  return evidence.find((item) => item.evidence_type === evidenceType) ?? null;
}

async function confirmWithRetry(
  agreementId: number,
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
      return await confirmUpload(
        agreementId,
        fileKey,
        evidenceType,
        mimeType,
        checksumSha256,
      );
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

export async function uploadEvidenceItem({
  agreementId,
  evidenceType,
  localUri,
  mimeType,
  sizeBytes,
  checksumSha256,
  onPhaseChange,
}: UploadEvidenceInput): Promise<EvidenceItemResponse> {
  const uploadUrlRes = await getUploadUrl(
    agreementId,
    evidenceType,
    mimeType,
    sizeBytes,
    checksumSha256,
  );
  const uploadHeaders =
    Object.keys(uploadUrlRes.headers ?? {}).length > 0
      ? uploadUrlRes.headers
      : { "Content-Type": mimeType };

  onPhaseChange?.("uploading");
  await uploadFileToStorage(uploadUrlRes.upload_url, uploadHeaders, localUri);

  onPhaseChange?.("confirming");
  return confirmWithRetry(
    agreementId,
    uploadUrlRes.file_key,
    evidenceType,
    mimeType,
    checksumSha256,
  );
}
