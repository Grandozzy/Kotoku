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
  ghana_card_front_uploaded: boolean;
  ghana_card_back_uploaded: boolean;
  identity_selfie_uploaded: boolean;
  ghana_card_front_view_url: string | null;
  ghana_card_back_view_url: string | null;
  identity_selfie_view_url: string | null;
  identity_verification_status:
    | "pending"
    | "processing"
    | "verified"
    | "failed"
    | "manual_review_required";
  identity_verification_detail: string;
  identity_verification_failure_codes: string[];
  liveness_status: "" | "pending" | "passed" | "failed";
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
  description: string;
  status: AgreementStatus;
  scenario_template: string | null;
  field_data: Record<string, unknown>;
  seal_hash: string | null;
  sealed_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
  parties: Party[];
  evidence_items?: EvidenceItem[];
}

export interface AgreementCreate {
  title: string;
  description?: string;
  scenario_template?: string;
}

export interface AgreementUpdate {
  title?: string;
  description?: string;
  scenario_template?: string;
  field_data?: Record<string, unknown>;
}
