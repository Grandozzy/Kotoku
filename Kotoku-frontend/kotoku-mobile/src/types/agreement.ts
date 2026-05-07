import type { ScenarioId } from "@/constants/scenarios";

export type AgreementStatus =
  | "draft"
  | "awaiting_other_party"
  | "ready_for_review"
  | "ready_to_seal"
  | "sealed"
  | "reopen_requested"
  | "reopened_mutual"
  | "active"
  | "pending_consent"
  | "superseded"
  | "annotated_post_seal"
  | "archived"
  | "expired";

export interface Party {
  id: number;
  role: "buyer" | "seller" | "landlord" | "tenant" | "witness";
  displayName: string;
  phone: string;
  idType: "ghana_card" | "passport" | "other";
  idNumber: string;
  phoneVerifiedAt: string | null;
}

export interface Agreement {
  id: number;
  scenarioId: ScenarioId;
  title: string;
  status: AgreementStatus;
  createdAt: string;
  sealedAt: string | null;
  fieldData: Record<string, unknown>;
  parties: Party[];
}
