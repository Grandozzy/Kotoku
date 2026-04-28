import { useEffect, useRef } from "react";

import { saveDraft, updateDraft } from "@/db/drafts";
import { useAgreementStore } from "@/features/agreements/agreementStore";

/**
 * Persists the active draft to SQLite whenever store state changes.
 * Mount once inside the agreement steps layout — not in every step screen.
 *
 * On first call (no localId yet): inserts a new draft row.
 * On subsequent calls: updates the existing row.
 */
export function useDraftPersistence() {
  const store = useAgreementStore();
  const localIdRef = useRef<number | null>(null);

  useEffect(() => {
    if (!store.scenarioId) return;

    async function persist() {
      const patch = {
        stepIndex: store.stepIndex,
        partyA: store.partyA,
        partyB: store.partyB,
        subjectData: store.subjectData,
        agreementId: store.agreementId ?? undefined,
      };

      if (localIdRef.current === null) {
        const id = await saveDraft({
          scenarioId: store.scenarioId!,
          title: `Draft — ${store.scenarioId}`,
          ...patch,
        });
        localIdRef.current = id;
      } else {
        await updateDraft(localIdRef.current, patch);
      }
    }

    persist();
  }, [
    store.scenarioId,
    store.stepIndex,
    store.partyA,
    store.partyB,
    store.subjectData,
    store.agreementId,
  ]);
}
