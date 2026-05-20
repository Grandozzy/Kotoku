export type DisputeStatus = "open" | "under_review" | "resolved" | "closed";

export interface Dispute {
  id: number;
  raised_by_party_id: number;
  raised_by_display_name: string;
  reason: string;
  status: DisputeStatus;
  resolution: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DisputeCreate {
  reason: string;
}
