import { useQuery } from "@tanstack/react-query";
import { listAnnotations } from "@/api/annotations";

export function useAnnotations(agreementId: number) {
  return useQuery({
    queryKey: ["annotations", agreementId],
    queryFn: () => listAnnotations(agreementId),
  });
}
