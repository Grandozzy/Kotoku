export type VaultStatus = "active" | "expired" | "archived";
export type PdfStatus = "pending" | "generating" | "ready" | "failed";

export interface VaultRecord {
  id: number;
  agreementId: number;
  title: string;
  status: VaultStatus;
  pdfStatus: PdfStatus;
  pdfUrl: string | null;
  sealedAt: string;
  retentionExpiresAt: string;
}
