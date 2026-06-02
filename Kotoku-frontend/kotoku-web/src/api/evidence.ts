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
    let res: Response;
    try {
      res = await fetch(uploadUrl, { method: "PUT", headers, body: file });
    } catch {
      // fetch() itself throws (TypeError) on network errors, CORS preflight
      // failures, or when the storage host is unreachable.
      throw new Error(
        "File upload failed: storage server could not be reached. " +
          "This may be a network or CORS configuration issue."
      );
    }
    if (!res.ok) {
      throw new Error(
        `File upload failed: storage returned ${res.status}. Please try again.`
      );
    }
  },
};
