import { apiClient } from "@/api/client";
import type { ApiResponse } from "@/types/api";
import type { VaultRecord } from "@/types/vault";

interface RawPartySummary {
  id: number;
  role: string;
  display_name: string;
  phone: string;
  id_type: string;
  id_number: string;
}

interface RawVaultEntry {
  id: number;
  agreement: {
    id: number;
    title: string;
    status: string;
    scenario_template: string;
    sealed_at: string;
    created_by_phone: string;
    parties: RawPartySummary[];
  };
  pdf_status: string;
  pdf_url: string | null;
  retain_until: string;
  archived: boolean;
  created_at: string;
  updated_at: string;
}

function mapVaultRecord(raw: RawVaultEntry): VaultRecord {
  return {
    id: raw.id,
    agreementId: raw.agreement.id,
    title: raw.agreement.title,
    scenarioId: raw.agreement.scenario_template,
    status: raw.archived ? "archived" : "active",
    agreementStatus: raw.agreement.status as VaultRecord["agreementStatus"],
    pdfStatus: raw.pdf_status as VaultRecord["pdfStatus"],
    pdfUrl: raw.pdf_url || null,
    sealedAt: raw.agreement.sealed_at,
    retentionExpiresAt: raw.retain_until,
    createdByPhone: raw.agreement.created_by_phone,
    parties: (raw.agreement.parties ?? []).map((p) => ({
      id: p.id,
      role: p.role,
      displayName: p.display_name,
      phone: p.phone,
      idType: p.id_type,
      idNumber: p.id_number,
    })),
  };
}

export interface AuditEvent {
  id: number;
  eventType: string;
  actorPhone: string;
  createdAt: string;
  metadata: Record<string, unknown>;
}

export async function listVault(): Promise<VaultRecord[]> {
  const res = await apiClient.get<ApiResponse<{ results: RawVaultEntry[] }>>("/vault/");
  return res.data.data.results.map(mapVaultRecord);
}

export async function getVaultRecord(agreementId: number): Promise<VaultRecord> {
  const res = await apiClient.get<ApiResponse<{ vault_entry: RawVaultEntry }>>(
    `/vault/${agreementId}/`,
  );
  return mapVaultRecord(res.data.data.vault_entry);
}

export async function requestPdfExport(agreementId: number): Promise<VaultRecord> {
  const res = await apiClient.post<ApiResponse<{ vault_entry: RawVaultEntry }>>(
    `/vault/${agreementId}/export/`,
  );
  return mapVaultRecord(res.data.data.vault_entry);
}

export async function retryPdfExport(agreementId: number): Promise<VaultRecord> {
  const res = await apiClient.post<ApiResponse<{ vault_entry: RawVaultEntry }>>(
    `/vault/${agreementId}/retry-export/`,
  );
  return mapVaultRecord(res.data.data.vault_entry);
}

export async function getAuditLog(agreementId: number): Promise<AuditEvent[]> {
  const res = await apiClient.get<ApiResponse<AuditEvent[]>>(
    `/vault/${agreementId}/audit-log/`,
  );
  return res.data.data;
}
