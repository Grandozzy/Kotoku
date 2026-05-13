import { useQuery } from "@tanstack/react-query";
import { getCurrentPlan } from "@/api/billing";

/**
 * Fetch the current account's plan, usage, and flags.
 * Stale after 5 minutes; re-fetched after sealing an agreement by
 * invalidating the ["billing", "current-plan"] key.
 */
export function usePlan() {
  return useQuery({
    queryKey: ["billing", "current-plan"],
    queryFn: getCurrentPlan,
    staleTime: 5 * 60 * 1000,
    // Don't throw on error — billing is not a hard dependency for core flows
    retry: 1,
  });
}
