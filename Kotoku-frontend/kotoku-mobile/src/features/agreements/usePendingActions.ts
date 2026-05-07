import { useQuery } from "@tanstack/react-query";

import { fetchPendingActions } from "@/api/agreements";

export function usePendingActions() {
  return useQuery({
    queryKey: ["pending-actions"],
    queryFn: fetchPendingActions,
  });
}
