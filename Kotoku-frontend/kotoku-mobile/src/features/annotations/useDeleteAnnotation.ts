import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteAnnotation } from "@/api/annotations";

export function useDeleteAnnotation(agreementId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ annotationId, partyId }: { annotationId: number; partyId: number }) =>
      deleteAnnotation(agreementId, annotationId, partyId),
    onError: (error) => {
      console.error("Delete annotation failed:", error);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["annotations", agreementId] });
    },
  });
}