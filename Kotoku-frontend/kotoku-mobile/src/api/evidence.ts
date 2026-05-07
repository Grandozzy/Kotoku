import { apiClient } from "@/api/client";
import type { ApiResponse } from "@/types/api";

export interface UploadUrlResponse {
  upload_url: string;
  file_key: string;
  headers: Record<string, string>;
  evidence_id: number;
}

export interface EvidenceItemResponse {
  id: number;
  evidence_type: string;
  file_type: string;
  mime_type: string;
  size_bytes: number | null;
  file_key: string;
  storage_url: string;
  upload_status: string;
  uploaded_by_role: string | null;
  created_at: string;
}

export async function getUploadUrl(
  agreementId: number,
  evidenceType: string,
  mimeType: string,
  sizeBytes: number,
): Promise<UploadUrlResponse> {
  const res = await apiClient.post<ApiResponse<UploadUrlResponse>>(
    `/agreements/${agreementId}/evidence/upload-url/`,
    { evidence_type: evidenceType, mime_type: mimeType, size_bytes: sizeBytes },
  );
  return res.data.data;
}

export async function confirmUpload(
  agreementId: number,
  fileKey: string,
  evidenceType: string,
  mimeType: string,
): Promise<EvidenceItemResponse> {
  const res = await apiClient.post<ApiResponse<{ evidence: EvidenceItemResponse }>>(
    `/agreements/${agreementId}/evidence/`,
    { file_key: fileKey, evidence_type: evidenceType, mime_type: mimeType },
  );
  return res.data.data.evidence;
}

export async function listEvidence(
  agreementId: number,
): Promise<EvidenceItemResponse[]> {
  const res = await apiClient.get<ApiResponse<{ evidence: EvidenceItemResponse[] }>>(
    `/agreements/${agreementId}/evidence/`,
  );
  return res.data.data.evidence;
}
