export type PartyRole = "buyer" | "seller" | "landlord" | "tenant" | "witness";
export type IdType = "ghana_card";

export interface Party {
  id: number;
  role: PartyRole;
  full_name: string;
  phone: string;
  id_type: IdType;
  id_number: string;
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
  created_at: string;
  updated_at: string;
}

export interface PartyInput {
  role: PartyRole;
  full_name: string;
  phone: string;
  id_type: IdType;
  id_number: string;
}
