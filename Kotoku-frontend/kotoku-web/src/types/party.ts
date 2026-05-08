export type PartyRole = "buyer" | "seller" | "landlord" | "tenant" | "witness";
export type IdType = "ghana_card" | "passport" | "other";

export interface Party {
  id: number;
  role: PartyRole;
  full_name: string;
  phone: string;
  id_type: IdType;
  id_number: string;
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
