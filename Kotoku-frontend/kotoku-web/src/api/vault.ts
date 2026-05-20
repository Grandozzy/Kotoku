import { api } from "@/lib/apiClient";
import type { VaultEntry } from "@/types/vault";

interface RawVaultEntry {
  id: number;
  agreement: {
    id: number;
    title: string;
    status: string;
    sealed_at: string;
    seal_hash: string;
    created_by_phone: string;
  };
  pdf_status: VaultEntry["pdf_status"];
  pdf_url: string | null;
  retain_until: string | null;
  archived: boolean;
  created_at: string;
}

function mapVaultEntry(raw: RawVaultEntry): VaultEntry {
  return {
    id: raw.id,
    agreement: raw.agreement.id,
    title: raw.agreement.title,
    status: raw.agreement.status,
    seal_hash: raw.agreement.seal_hash,
    sealed_at: raw.agreement.sealed_at,
    created_by_phone: raw.agreement.created_by_phone,
    pdf_status: raw.pdf_status,
    pdf_url: raw.pdf_url,
    retain_until: raw.retain_until,
    archived: raw.archived,
    created_at: raw.created_at,
  };
}

export const vaultApi = {
  list: () =>
    api
      .get<{ results: RawVaultEntry[]; count: number; next: string | null; previous: string | null }>(
        "/api/vault/",
      )
      .then((r) => ({
        ...r,
        results: r.results.map(mapVaultEntry),
      })),

  get: (agreementId: number) =>
    api
      .get<{ vault_entry: RawVaultEntry }>(`/api/vault/${agreementId}/`)
      .then((r) => mapVaultEntry(r.vault_entry)),

  requestExport: (agreementId: number) =>
    api
      .post<{ vault_entry: RawVaultEntry }>(`/api/vault/${agreementId}/export/`)
      .then((r) => mapVaultEntry(r.vault_entry)),

  retryExport: (agreementId: number) =>
    api
      .post<{ vault_entry: RawVaultEntry }>(`/api/vault/${agreementId}/retry-export/`)
      .then((r) => mapVaultEntry(r.vault_entry)),
};
