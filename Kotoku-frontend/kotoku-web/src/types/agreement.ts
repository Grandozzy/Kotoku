export type AgreementStatus =
  | "draft"
  | "active"
  | "sealed"
  | "reopen_requested"
  | "archived"
  | "expired"
  | "closed";

export interface Party {
  id: number;
  role: string;
  display_name: string;
  phone: string;
  id_type: string | null;
  id_number: string | null;
}

export interface EvidenceItem {
  id: number;
  evidence_type: string;
  file_type: string;
  upload_status: string;
  created_at: string;
}

export interface Agreement {
  id: number;
  title: string;
  status: AgreementStatus;
  scenario_template: string | null;
  field_data: Record<string, unknown>;
  seal_hash: string | null;
  sealed_at: string | null;
  created_at: string;
  updated_at: string;
  parties: Party[];
  evidence_items?: EvidenceItem[];
}

export interface AgreementCreate {
  title: string;
  scenario_template?: string;
  field_data?: Record<string, unknown>;
}
