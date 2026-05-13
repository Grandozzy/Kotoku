import { useQuery, useQueryClient } from "@tanstack/react-query";
import { billingApi } from "@/api/billing";

export const PLAN_QUERY_KEY = ["billing", "current-plan"] as const;

export function usePlan() {
  return useQuery({
    queryKey: PLAN_QUERY_KEY,
    queryFn: billingApi.currentPlan,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
}

/** Call after a seal to refresh the usage counter. */
export function useInvalidatePlan() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: PLAN_QUERY_KEY });
}
