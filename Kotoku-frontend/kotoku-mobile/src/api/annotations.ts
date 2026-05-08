import { apiClient } from "@/api/client";
import type { ApiResponse } from "@/types/api";

export interface Annotation {
  id: number;
  authorPartyId: number;
  author: {
    displayName: string;
    role: string;
  };
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