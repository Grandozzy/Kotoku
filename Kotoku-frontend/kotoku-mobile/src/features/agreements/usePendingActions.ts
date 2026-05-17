import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useFocusEffect } from "@react-navigation/native";
import { useCallback } from "react";

import { fetchPendingActions } from "@/api/agreements";
import { useSessionStore } from "@/store/sessionStore";

export function usePendingActions() {
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  const queryClient = useQueryClient();

  // Refetch when home screen comes into focus
  useFocusEffect(
    useCallback(() => {
      queryClient.invalidateQueries({ queryKey: ["pending-actions"] });
    }, [queryClient]),
  );

  return useQuery({
    queryKey: ["pending-actions"],
    queryFn: fetchPendingActions,
    enabled: isAuthenticated,
    staleTime: 0,
    refetchOnMount: "always",
  });
}
