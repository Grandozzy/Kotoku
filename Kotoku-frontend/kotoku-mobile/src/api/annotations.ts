import { apiClient } from "@/api/client";
import type { ApiResponse } from "@/types/api";

export interface Annotation {
  id: number;
  authorPartyId: number;
  authorDisplayName: string;
  body: string;
  createdAt: string;
}

interface RawAnnotation {
  id: number;
  author_party_id: number;
  author_display_name: string;
  body: string;
  created_at: string;
}

function mapAnnotation(raw: RawAnnotation): Annotation {
  return {
    id: raw.id,
    authorPartyId: raw.author_party_id,
    authorDisplayName: raw.author_display_name,
    body: raw.body,
    createdAt: raw.created_at,
  };
}

export async function createAnnotation(
  agreementId: number,
  payload: { authorPartyId: number; body: string },
): Promise<Annotation> {
  const res = await apiClient.post<ApiResponse<{ annotation: RawAnnotation }>>(
    `/agreements/${agreementId}/annotations/`,
    { author_party_id: payload.authorPartyId, body: payload.body },
  );
  return mapAnnotation(res.data.data.annotation);
}

export async function listAnnotations(
  agreementId: number,
): Promise<Annotation[]> {
  const res = await apiClient.get<ApiResponse<{ annotations: RawAnnotation[] }>>(
    `/agreements/${agreementId}/annotations/`,
  );
  return res.data.data.annotations.map(mapAnnotation);
}

export async function deleteAnnotation(
  agreementId: number,
  annotationId: number,
  partyId: number,
): Promise<void> {
  await apiClient.delete(
    `/agreements/${agreementId}/annotations/${annotationId}?party_id=${partyId}`,
  );
}

export async function updateAnnotation(
  agreementId: number,
  annotationId: number,
  partyId: number,
  body: string,
): Promise<Annotation> {
  const res = await apiClient.put<ApiResponse<{ annotation: RawAnnotation }>>(
    `/agreements/${agreementId}/annotations/${annotationId}?party_id=${partyId}`,
    { body },
  );
  return mapAnnotation(res.data.data.annotation);
}
