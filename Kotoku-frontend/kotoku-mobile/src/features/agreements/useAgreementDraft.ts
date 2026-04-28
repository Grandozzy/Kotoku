import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";

import { createDraft, getAgreement, listAgreements, sealAgreement, validateAgreement } from "@/api/agreements";
import type { ScenarioId } from "@/constants/scenarios";
import { LOCAL_TEMPLATES } from "@/constants/templates";
import type { ScenarioTemplate } from "@/types/template";
import { useAgreementStore } from "./agreementStore";

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
      router.push(`/agreement/${agreement.id}/steps/parties`);
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
  return useQuery({
    queryKey: ["agreements", status],
    queryFn: () => listAgreements({ status }),
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
  const reset = useAgreementStore((s) => s.reset);

  return useMutation({
    mutationFn: () => sealAgreement(id),
    onSuccess: () => {
      reset();
      router.replace(`/agreement/${id}/sealed`);
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
