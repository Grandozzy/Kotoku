import { api } from "@/lib/apiClient";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

if (process.env.NODE_ENV === "production" && BASE_URL.startsWith("http://")) {
  throw new Error(
    `[Kotoku] NEXT_PUBLIC_API_URL must use https:// in production.\nCurrent value: "${BASE_URL}"`,
  );
}

export interface InviteDetail {
  agreement_id: number;
  agreement_title: string;
  role: string;
  party_name: string;
  expires_at: string;
}

export interface ClaimResult {
  agreement_id: number;
  role: string;
}

export interface LivenessSession {
  session_id: string;
  region: string;
}

type Envelope<T> = { status: "ok"; data: T };

async function publicGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body?.message ?? `HTTP ${res.status}`);
  if (body?.status === "ok" && "data" in body) return (body as Envelope<T>).data;
  return body as T;
}

export const invitesApi = {
  getDetail: (token: string) =>
    publicGet<{ invite: InviteDetail }>(`/api/invites/${encodeURIComponent(token)}/`).then(
      (r) => r.invite,
    ),

  claim: (token: string) =>
    api.post<ClaimResult>(`/api/invites/${encodeURIComponent(token)}/claim/`),

  createLivenessSession: (agreementId: number, role: string) =>
    api.post<LivenessSession>(
      `/api/agreements/${agreementId}/identity/${role}/liveness-session/`,
    ),

  submitLivenessResult: (agreementId: number, role: string) =>
    api.post<{ status: string }>(
      `/api/agreements/${agreementId}/identity/${role}/liveness-result/`,
    ),
};
