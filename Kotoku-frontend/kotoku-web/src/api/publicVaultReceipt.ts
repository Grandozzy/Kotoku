const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface PublicReceiptParty {
  id: number;
  role: string;
  display_name: string;
  phone: string;
  id_type: string | null;
  id_number: string | null;
}

export interface PublicReceiptAgreement {
  id: number;
  title: string;
  status: string;
  scenario_template: string;
  sealed_at: string;
  seal_hash: string;
  field_data: Record<string, unknown>;
}

export interface PublicReceiptVaultEntry {
  id: number;
  pdf_status: string;
  retain_until: string;
  archived: boolean;
  created_at: string;
}

export interface PublicReceiptEvidence {
  id: number;
  evidence_type: string;
  file_type: string;
  mime_type: string;
  size_bytes: number | null;
  original_name: string;
  upload_status: string;
  uploaded_by_role: string | null;
  created_at: string;
  view_url: string | null;
}

export interface PublicVaultReceipt {
  vault_entry: PublicReceiptVaultEntry;
  agreement: PublicReceiptAgreement;
  party: PublicReceiptParty;
  parties: PublicReceiptParty[];
  evidence: PublicReceiptEvidence[];
}

type ApiEnvelope<T> = { status: "ok"; data: T };

function encodeReceiptToken(token: string): string {
  try {
    return encodeURIComponent(decodeURIComponent(token));
  } catch {
    return encodeURIComponent(token);
  }
}

export async function getPublicVaultReceipt(
  token: string,
): Promise<PublicVaultReceipt> {
  const response = await fetch(
    `${BASE_URL}/api/vault-receipts/${encodeReceiptToken(token)}/`,
    { cache: "no-store" },
  );

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(
      typeof body?.message === "string"
        ? body.message
        : `Request failed with status ${response.status}`,
    );
  }

  if (body && body.status === "ok" && "data" in body) {
    return (body as ApiEnvelope<PublicVaultReceipt>).data;
  }
  return body as PublicVaultReceipt;
}
