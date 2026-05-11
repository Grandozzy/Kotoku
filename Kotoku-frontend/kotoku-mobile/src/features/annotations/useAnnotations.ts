import { useQuery } from "@tanstack/react-query";
import { listAnnotations, type Annotation } from "@/api/annotations";

function mapAnnotation(raw: Annotation) {
  return {
    id: raw.id,
    authorPartyId: raw.authorPartyId,
    authorDisplayName: raw.authorDisplayName,
    body: raw.body,
    createdAt: raw.createdAt,
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