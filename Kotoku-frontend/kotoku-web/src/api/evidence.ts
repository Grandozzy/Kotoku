import { api } from "@/lib/apiClient";

interface InitiateResponse {
  evidence_id: number;
  upload_url: string;
  fields: Record<string, string>;
}

export const evidenceApi = {
  initiate: (
    agreementId: number,
    data: { file_type: string; evidence_type: string; file_name: string; file_size: number }
  ) =>
    api.post<InitiateResponse>(
      `/api/agreements/${agreementId}/evidence/initiate/`,
      data
    ),

  confirm: (agreementId: number, evidenceId: number) =>
    api.post<{ detail: string }>(
      `/api/agreements/${agreementId}/evidence/${evidenceId}/confirm/`
    ),

  uploadToS3: async (uploadUrl: string, fields: Record<string, string>, file: File) => {
    const form = new FormData();
    Object.entries(fields).forEach(([k, v]) => form.append(k, v));
    form.append("file", file);
    const res = await fetch(uploadUrl, { method: "POST", body: form });
    if (!res.ok) throw new Error(`S3 upload failed: ${res.status}`);
  },
};
