import { useQuery } from "@tanstack/react-query";
import { listAnnotations } from "@/api/annotations";

interface AnnotationItem {
  id: number;
  author_party_id: number;
  author_display_name: string;
  body: string;
  created_at: string;
}

function mapAnnotation(raw: AnnotationItem) {
  return {
    id: raw.id,
    authorPartyId: raw.author_party_id,
    authorDisplayName: raw.author_display_name,
    body: raw.body,
    createdAt: raw.created_at,
  };
}

export function useAnnotations(agreementId: number) {
  return useQuery({
    queryKey: ["annotations", agreementId],
    queryFn: async () => {
      const raw = await listAnnotations(agreementId);
      return raw.map(mapAnnotation);
    },
  });
}