import { apiClient } from "@/api/client";
import type { ApiResponse } from "@/types/api";

export interface Dispute {
  id: number;
  agreement_id: number;
  agreement_type: string;
  agreement_sealed_at: string;
  raised_by_party_id: number;
  raised_by_display_name: string;
  reason: string;
  status: "open" | "investigating" | "resolved" | "dismissed";
  resolution?: string;
  resolved_at?: string;
  created_at: string;
}

interface ListDisputesResponse {
  disputes: Dispute[];
}

interface DisputeDetailResponse {
  dispute: Dispute;
}

export async function listDisputes(): Promise<Dispute[]> {
  const res = await apiClient.get<ApiResponse<ListDisputesResponse>>("/disputes/");
  return res.data.data.disputes;
}

export async function listDisputesForAgreement(agreementId: number): Promise<Dispute[]> {
  const res = await apiClient.get<ApiResponse<ListDisputesResponse>>(
    `/agreements/${agreementId}/disputes/`,
  );
  return res.data.data.disputes;
}

export async function getDispute(disputeId: number): Promise<Dispute> {
  const res = await apiClient.get<ApiResponse<DisputeDetailResponse>>(`/disputes/${disputeId}/`);
  return res.data.data.dispute;
}

export async function createDispute(
  agreementId: number,
  payload: { reason: string },
): Promise<Dispute> {
  const res = await apiClient.post<ApiResponse<DisputeDetailResponse>>(
    `/agreements/${agreementId}/disputes/`,
    payload,
  );
  return res.data.data.dispute;
}
