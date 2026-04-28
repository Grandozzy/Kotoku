export type VaultStatus = "active" | "expired" | "archived";
export type PdfStatus = "pending" | "ready" | "failed";

export interface VaultRecord {
  id: number;
  agreementId: number;
  status: VaultStatus;
  pdfStatus: PdfStatus;
  pdfUrl: string | null;
  sealedAt: string;
  retentionExpiresAt: string;
}
