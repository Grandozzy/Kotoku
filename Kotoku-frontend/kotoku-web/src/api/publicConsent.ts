const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface PublicConsentRecord {
  id: number;
  party_id: number;
  party_phone: string;
  channel: string;
  granted: boolean;
  granted_at: string | null;
  expires_at: string;
  created_at: string;
}

export interface PublicConsentParty {
  id: number;
  role: string;
  display_name: string;
  phone: string;
}

export interface PublicConsentAgreement {
  id: number;
  title: string;
  scenario_template: string;
  status: string;
  field_data: Record<string, unknown>;
}

export interface PublicConsentEvidence {
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

export interface PublicConsentContext {
  agreement: PublicConsentAgreement;
  party: PublicConsentParty;
  parties: PublicConsentParty[];
  evidence: PublicConsentEvidence[];
  consent_record: PublicConsentRecord | null;
  all_consented: boolean;
}

type ApiEnvelope<T> = { status: "ok"; data: T };

async function publicRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string> | undefined),
    },
    cache: "no-store",
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(
      typeof body?.message === "string"
        ? body.message
        : `Request failed with status ${response.status}`,
    );
  }

  if (body && body.status === "ok" && "data" in body) {
    return (body as ApiEnvelope<T>).data;
  }
  return body as T;
}

export function getPublicConsent(token: string): Promise<PublicConsentContext> {
  return publicRequest<PublicConsentContext>(
    `/api/consent-links/${encodeURIComponent(token)}/`,
  );
}

export function confirmPublicConsent(
  token: string,
  otpCode: string,
): Promise<{ consent_record: PublicConsentRecord; all_consented: boolean }> {
  return publicRequest(`/api/consent-links/${encodeURIComponent(token)}/confirm/`, {
    method: "POST",
    body: JSON.stringify({ otp_code: otpCode }),
  });
}
