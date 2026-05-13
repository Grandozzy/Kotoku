import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";

import { createDraft, getAgreement, listAgreements, sealAgreement, validateAgreement } from "@/api/agreements";
import type { ScenarioId } from "@/constants/scenarios";
import { LOCAL_TEMPLATES } from "@/constants/templates";
import type { ScenarioTemplate } from "@/types/template";
import { useAgreementStore } from "./agreementStore";
import { useSessionStore } from "@/store/sessionStore";

// ---------- Draft creation ----------

export function useCreateDraft() {
  const router = useRouter();
  const initDraft = useAgreementStore((s) => s.initDraft);

  return useMutation({
    mutationFn: (scenarioId: ScenarioId) =>
      createDraft({
        scenarioId,
        title: LOCAL_TEMPLATES[scenarioId]?.title ?? scenarioId,
      }),
    onSuccess: (agreement, scenarioId) => {
      initDraft(agreement.id, scenarioId);
      router.push(`/agreement/${agreement.id}/steps/parties?scenarioId=${scenarioId}`);
    },
  });
}

// ---------- Agreement queries ----------

export function useAgreement(id: number) {
  return useQuery({
    queryKey: ["agreement", id],
    queryFn: () => getAgreement(id),
    enabled: id > 0,
  });
}

export function useAgreements(status?: string) {
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  return useQuery({
    queryKey: ["agreements", status],
    queryFn: () => listAgreements({ status }),
    enabled: isAuthenticated,
  });
}

// ---------- Validation + seal ----------

export function useValidateAgreement(id: number) {
  return useMutation({
    mutationFn: () => validateAgreement(id),
  });
}

export function useSealAgreement(id: number) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const reset = useAgreementStore((s) => s.reset);
  const isReopened = useAgreementStore((s) => s.isReopened);

  return useMutation({
    mutationFn: () => sealAgreement(id),
    onSuccess: () => {
      const wasReopened = isReopened;
      // Refresh billing usage so the home screen reflects the new count
      queryClient.invalidateQueries({ queryKey: ["billing", "current-plan"] });
      router.replace(`/agreement/${id}/sealed?reopened=${wasReopened}`);
      setTimeout(() => reset(), 0);
    },
  });
}

// ---------- Template resolution ----------
// Uses local templates as the source of truth until the backend API is ready.
// When backend delivers GET /templates/{scenarioId}, swap the return here.

export function useTemplate(scenarioId: string | null): ScenarioTemplate | null {
  if (!scenarioId) return null;
  return LOCAL_TEMPLATES[scenarioId] ?? null;
}
