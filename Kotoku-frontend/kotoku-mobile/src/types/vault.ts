export type VaultStatus = "active" | "expired" | "archived";
export type AgreementStatus =
  | "draft"
  | "pending_consent"
  | "active"
  | "sealed"
  | "reopen_requested"
  | "closed"
  | "archived"
  | "expired";
export type PdfStatus = "pending" | "generating" | "ready" | "failed";

export interface VaultRecord {
  id: number;
  agreementId: number;
  title: string;
  scenarioId: string;
  status: VaultStatus;
  agreementStatus: AgreementStatus;
  pdfStatus: PdfStatus;
  pdfUrl: string | null;
  sealedAt: string;
  retentionExpiresAt: string;
  createdByPhone: string;
}
