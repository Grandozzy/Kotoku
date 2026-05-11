import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createAnnotation, type Annotation } from "@/api/annotations";

export function useAddAnnotation(agreementId: number) {
  const queryClient = useQueryClient();

  return useMutation<Annotation, Error, { author_party_id: number; body: string }>({
    mutationFn: (payload) => createAnnotation(agreementId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["annotations", agreementId] });
    },
  });
}