import { apiClient } from "@/api/client";
import type { Agreement } from "@/types/agreement";
import type { ApiResponse } from "@/types/api";
import type { ScenarioId } from "@/constants/scenarios";
import type { IdType } from "@/features/agreements/agreementStore";

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
    parties: (raw.parties ?? []).map((p) => ({
      id: p.id,
      role: p.role as Agreement["parties"][number]["role"],
      displayName: p.display_name,
      phone: p.phone,
      idType: p.id_type as IdType,
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
    scenario_template: payload.scenarioId,
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

export interface ValidationError {
  code: string;
  message: string;
  field: string;
}

export interface ValidateAgreementResponse {
  valid: boolean;
  errors: ValidationError[];
}

export async function validateAgreement(id: number): Promise<ValidateAgreementResponse> {
  const res = await apiClient.post<ApiResponse<ValidateAgreementResponse>>(
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
  const page = await listAgreementsPage(params);
  return page.results;
}

export async function listAgreementsPage(params?: {
  status?: string;
}): Promise<{
  results: Agreement[];
  count: number;
  next: string | null;
  previous: string | null;
}> {
  const res = await apiClient.get<ApiResponse<{
    results: RawAgreement[];
    count: number;
    next: string | null;
    previous: string | null;
  }>>("/agreements/", { params });
  return {
    ...res.data.data,
    results: res.data.data.results.map(mapAgreement),
  };
}

export interface PendingActionItem {
  id: number;
  title: string;
  status: string;
  scenario_template: string;
  created_at: string;
  updated_at: string;
  parties?: Array<{
    id: number;
    role: string;
    full_name: string;
    phone: string;
  }>;
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

export interface PartyPayload {
  role: string;
  full_name: string;
  phone: string;
  id_type: IdType;
  id_number: string;
}

export async function setParties(
  agreementId: number,
  parties: PartyPayload[],
): Promise<void> {
  await apiClient.post<ApiResponse<unknown>>(
    `/agreements/${agreementId}/parties/`,
    { parties },
  );
}

export async function deleteDraft(agreementId: number): Promise<void> {
  await apiClient.delete(`/agreements/${agreementId}/`);
}
