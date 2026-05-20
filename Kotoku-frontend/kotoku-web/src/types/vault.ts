export type PdfStatus = "pending" | "generating" | "ready" | "failed";

export interface VaultEntry {
  id: number;
  agreement: number;
  title: string;
  status: string;
  seal_hash: string;
  sealed_at: string;
  created_by_phone: string;
  pdf_status: PdfStatus;
  pdf_url: string | null;
  retain_until: string | null;
  archived: boolean;
  created_at: string;
}
