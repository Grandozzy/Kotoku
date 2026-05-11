import { apiClient } from "@/api/client";
import type { ApiResponse } from "@/types/api";

export interface Annotation {
  id: number;
  authorPartyId: number;
  authorDisplayName: string;
  body: string;
  createdAt: string;
}

interface CreateAnnotationResponse {
  annotation: Annotation;
}

interface ListAnnotationsResponse {
  annotations: Annotation[];
}

export async function createAnnotation(
  agreementId: number,
  payload: { author_party_id: number; body: string },
): Promise<Annotation> {
  const res = await apiClient.post<ApiResponse<CreateAnnotationResponse>>(
    `/agreements/${agreementId}/annotations/`,
    payload,
  );
  return res.data.data.annotation;
}

export async function listAnnotations(
  agreementId: number,
): Promise<Annotation[]> {
  const res = await apiClient.get<ApiResponse<ListAnnotationsResponse>>(
    `/agreements/${agreementId}/annotations/`,
  );
  return res.data.data.annotations;
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
  const res = await apiClient.put<ApiResponse<{ annotation: Annotation }>>(
    `/agreements/${agreementId}/annotations/${annotationId}?party_id=${partyId}`,
    { body },
  );
  return res.data.data.annotation;
}