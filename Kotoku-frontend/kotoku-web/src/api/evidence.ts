import { api } from "@/lib/apiClient";

interface UploadUrlResponse {
  evidence_id: number;
  upload_url: string;
  file_key: string;
  headers: Record<string, string>;
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
  ) => api.post<{ evidence: { id: number } }>(`/api/agreements/${agreementId}/evidence/`, data),

  uploadToStorage: async (uploadUrl: string, headers: Record<string, string>, file: File) => {
    const res = await fetch(uploadUrl, { method: "PUT", headers, body: file });
    if (!res.ok) throw new Error(`S3 upload failed: ${res.status}`);
  },
};
