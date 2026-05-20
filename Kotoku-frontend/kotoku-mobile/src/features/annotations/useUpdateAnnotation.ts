import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateAnnotation } from "@/api/annotations";

export function useUpdateAnnotation(agreementId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      annotationId,
      partyId,
      body,
    }: {
      annotationId: number;
      partyId: number;
      body: string;
    }) => updateAnnotation(agreementId, annotationId, partyId, body),
    onError: (error) => {
      if (__DEV__) {
        console.error("Update annotation failed:", error);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["annotations", agreementId] });
    },
  });
}
