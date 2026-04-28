import { apiClient } from "@/api/client";
import type { EvidenceItem } from "@/types/evidence";
import type { ApiResponse } from "@/types/api";

export async function getUploadUrl(
  agreementId: number,
  fileType: string,
): Promise<{ uploadUrl: string; storageKey: string }> {
  const res = await apiClient.post<
    ApiResponse<{ uploadUrl: string; storageKey: string }>
  >(`/agreements/${agreementId}/evidence/upload-url/`, { file_type: fileType });
  return res.data.data;
}

export async function registerEvidence(
  agreementId: number,
  payload: {
    partyId: number;
    fileType: string;
    storageKey: string;
    originalName: string;
  },
): Promise<EvidenceItem> {
  const res = await apiClient.post<ApiResponse<EvidenceItem>>(
    `/agreements/${agreementId}/evidence/`,
    {
      party_id: payload.partyId,
      file_type: payload.fileType,
      storage_key: payload.storageKey,
      original_name: payload.originalName,
    },
  );
  return res.data.data;
}

export async function listEvidence(agreementId: number): Promise<EvidenceItem[]> {
  const res = await apiClient.get<ApiResponse<EvidenceItem[]>>(
    `/agreements/${agreementId}/evidence/`,
  );
  return res.data.data;
}
