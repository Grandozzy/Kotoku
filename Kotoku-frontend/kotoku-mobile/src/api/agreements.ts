import { apiClient } from "@/api/client";
import type { Agreement } from "@/types/agreement";
import type { ApiResponse } from "@/types/api";

export async function createDraft(payload: {
  scenarioId: string;
  title: string;
}): Promise<Agreement> {
  const res = await apiClient.post<ApiResponse<Agreement>>("/agreements/", {
    scenario_id: payload.scenarioId,
    title: payload.title,
  });
  return res.data.data;
}

export async function getAgreement(id: number): Promise<Agreement> {
  const res = await apiClient.get<ApiResponse<Agreement>>(`/agreements/${id}/`);
  return res.data.data;
}

export async function updateAgreement(
  id: number,
  payload: Record<string, unknown>,
): Promise<Agreement> {
  const res = await apiClient.patch<ApiResponse<Agreement>>(
    `/agreements/${id}/`,
    payload,
  );
  return res.data.data;
}

export async function validateAgreement(id: number): Promise<{
  ready: boolean;
  missing: string[];
}> {
  const res = await apiClient.post<ApiResponse<{ ready: boolean; missing: string[] }>>(
    `/agreements/${id}/validate/`,
  );
  return res.data.data;
}

export async function sealAgreement(id: number): Promise<Agreement> {
  const res = await apiClient.post<ApiResponse<Agreement>>(
    `/agreements/${id}/seal/`,
  );
  return res.data.data;
}

export async function listAgreements(params?: {
  status?: string;
}): Promise<Agreement[]> {
  const res = await apiClient.get<ApiResponse<Agreement[]>>("/agreements/", {
    params,
  });
  return res.data.data;
}

export interface PendingActionItem {
  id: number;
  title: string;
  status: string;
  scenario_template: string;
  created_at: string;
  updated_at: string;
}

export interface PendingActionsResponse {
  action_required: PendingActionItem[];
  drafts: PendingActionItem[];
}

export async function fetchPendingActions(): Promise<PendingActionsResponse> {
  const res = await apiClient.get<ApiResponse<PendingActionsResponse>>(
    "/agreements/pending-actions/",
  );
  return res.data.data;
}
