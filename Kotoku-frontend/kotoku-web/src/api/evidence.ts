import { api } from "@/lib/apiClient";

export interface UploadUrlResponse {
  evidence_id: number;
  upload_url: string;
  file_key: string;
  headers: Record<string, string>;
}

export interface EvidenceItemResponse {
  id: number;
  evidence_type: string;
  file_type: string;
  mime_type: string;
  size_bytes: number | null;
  view_url: string | null;
  upload_status: string;
  uploaded_by_role: string | null;
  created_at: string;
}

export const evidenceApi = {
  requestUploadUrl: (
    agreementId: number,
    data: {
      evidence_type: string;
      mime_type: string;
      size_bytes: number;
      checksum_sha256: string;
    }
  ) =>
    api.post<UploadUrlResponse>(
      `/api/agreements/${agreementId}/evidence/upload-url/`,
      data
    ),

  confirm: (
    agreementId: number,
    data: {
      file_key: string;
      evidence_type: string;
      mime_type: string;
      checksum_sha256: string;
    }
  ) =>
    api.post<{ evidence: EvidenceItemResponse }>(
      `/api/agreements/${agreementId}/evidence/`,
      data
    ),

  list: (agreementId: number) =>
    api
      .get<{ evidence: EvidenceItemResponse[] }>(
        `/api/agreements/${agreementId}/evidence/`
      )
      .then((res) => res.evidence),
};
