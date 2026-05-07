import { apiClient } from "@/api/client";
import type { Agreement } from "@/types/agreement";
import type { ApiResponse } from "@/types/api";
import type { ScenarioId } from "@/constants/scenarios";

interface RawAgreement {
  id: number;
  title: string;
  status: string;
  scenario_template: string;
  field_data: Record<string, unknown>;
  sealed_at: string | null;
  created_at: string;
  parties: {
    id: number;
    role: string;
    display_name: string;
    phone: string;
    id_type: string;
    id_number: string;
  }[];
}

function mapAgreement(raw: RawAgreement): Agreement {
  return {
    id: raw.id,
    scenarioId: raw.scenario_template as ScenarioId,
    title: raw.title,
    status: raw.status as Agreement["status"],
    createdAt: raw.created_at,
    sealedAt: raw.sealed_at,
    fieldData: raw.field_data ?? {},
    parties: raw.parties.map((p) => ({
      id: p.id,
      role: p.role as Agreement["parties"][number]["role"],
      displayName: p.display_name,
      phone: p.phone,
      idType: p.id_type as "ghana_card" | "passport" | "other",
      idNumber: p.id_number,
      phoneVerifiedAt: null,
    })),
  };
}

export async function createDraft(payload: {
  scenarioId: string;
  title: string;
}): Promise<Agreement> {
  const res = await apiClient.post<ApiResponse<{ agreement: RawAgreement }>>("/agreements/", {
    scenario_id: payload.scenarioId,
    title: payload.title,
  });
  return mapAgreement(res.data.data.agreement);
}

export async function getAgreement(id: number): Promise<Agreement> {
  const res = await apiClient.get<ApiResponse<{ agreement: RawAgreement }>>(`/agreements/${id}/`);
  return mapAgreement(res.data.data.agreement);
}

export async function updateAgreement(
  id: number,
  payload: Record<string, unknown>,
): Promise<Agreement> {
  const res = await apiClient.patch<ApiResponse<{ agreement: RawAgreement }>>(
    `/agreements/${id}/`,
    payload,
  );
  return mapAgreement(res.data.data.agreement);
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
  const res = await apiClient.post<ApiResponse<{ agreement: RawAgreement }>>(
    `/agreements/${id}/seal/`,
  );
  return mapAgreement(res.data.data.agreement);
}

export async function listAgreements(params?: {
  status?: string;
}): Promise<Agreement[]> {
  const res = await apiClient.get<ApiResponse<RawAgreement[]>>("/agreements/", {
    params,
  });
  return res.data.data.map(mapAgreement);
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
