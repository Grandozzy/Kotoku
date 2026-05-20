import { api } from "@/lib/apiClient";

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

export const annotationsApi = {
  list: (agreementId: number) =>
    api
      .get<{ annotations: RawAnnotation[] }>(`/api/agreements/${agreementId}/annotations/`)
      .then((r) => r.annotations.map(mapAnnotation)),

  create: (agreementId: number, authorPartyId: number, body: string) =>
    api
      .post<{ annotation: RawAnnotation }>(`/api/agreements/${agreementId}/annotations/`, {
        author_party_id: authorPartyId,
        body,
      })
      .then((r) => mapAnnotation(r.annotation)),
};
