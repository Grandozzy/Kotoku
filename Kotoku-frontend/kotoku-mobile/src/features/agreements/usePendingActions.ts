import { useQuery } from "@tanstack/react-query";

import { fetchPendingActions } from "@/api/agreements";
import { useSessionStore } from "@/store/sessionStore";

export function usePendingActions() {
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  return useQuery({
    queryKey: ["pending-actions"],
    queryFn: fetchPendingActions,
    enabled: isAuthenticated,
  });
}
