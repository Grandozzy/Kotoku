import { apiClient } from "@/api/client";
import type { ApiResponse } from "@/types/api";
import type { VaultRecord } from "@/types/vault";

export interface AuditEvent {
  id: number;
  eventType: string;
  actorPhone: string;
  createdAt: string;
  metadata: Record<string, unknown>;
}

export async function listVault(): Promise<VaultRecord[]> {
  const res = await apiClient.get<ApiResponse<VaultRecord[]>>("/vault/");
  return res.data.data;
}

export async function getVaultRecord(agreementId: number): Promise<VaultRecord> {
  const res = await apiClient.get<ApiResponse<VaultRecord>>(
    `/vault/${agreementId}/`,
  );
  return res.data.data;
}

export async function requestPdfExport(agreementId: number): Promise<VaultRecord> {
  const res = await apiClient.post<ApiResponse<VaultRecord>>(
    `/vault/${agreementId}/export/`,
  );
  return res.data.data;
}

export async function getAuditLog(agreementId: number): Promise<AuditEvent[]> {
  const res = await apiClient.get<ApiResponse<AuditEvent[]>>(
    `/vault/${agreementId}/audit-log/`,
  );
  return res.data.data;
}
