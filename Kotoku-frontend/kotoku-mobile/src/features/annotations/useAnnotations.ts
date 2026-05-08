import { useQuery } from "@tanstack/react-query";
import { listAnnotations, type Annotation } from "@/api/annotations";

export function useAnnotations(agreementId: number) {
  return useQuery<Annotation[]>({
    queryKey: ["annotations", agreementId],
    queryFn: () => listAnnotations(agreementId),
  });
}