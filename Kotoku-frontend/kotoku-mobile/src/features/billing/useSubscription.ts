import { useQuery } from "@tanstack/react-query";
import { getSubscriptionStatus } from "@/api/payments";

/**
 * Fetch the current account's subscription status.
 * Stale after 5 minutes; invalidated on successful payment initiation,
 * cancellation, or plan change via the ["billing", "subscription"] key.
 */
export function useSubscription() {
  return useQuery({
    queryKey: ["billing", "subscription"],
    queryFn: getSubscriptionStatus,
    staleTime: 5 * 60 * 1000,
    // Don't throw on error — subscription state is not a hard dependency
    retry: 1,
  });
}
