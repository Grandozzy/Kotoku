import { useAgreementStore } from "@/features/agreements/agreementStore";
import type { PartyDraft } from "@/features/agreements/agreementStore";
import { getAgreement, updateAgreement } from "@/api/agreements";

import type { ScenarioId } from "@/constants/scenarios";

export interface DraftState {
  agreementId: number;
  scenarioId: ScenarioId;
  stepIndex: number;
  partyA: PartyDraft;
  partyB: PartyDraft;
  subjectData: Record<string, unknown>;
}

export function useDraftSession() {
  const store = useAgreementStore();

  const load = async (agreementId: number): Promise<DraftState> => {
    const agreement = await getAgreement(agreementId);

    if (agreement.status !== "draft") {
      throw new Error(`Cannot load agreement with status ${agreement.status}. Expected 'draft'.`);
    }

    const partyA: PartyDraft = {
      fullName: agreement.parties[0]?.displayName ?? "",
      phone: agreement.parties[0]?.phone ?? "",
      idType: agreement.parties[0]?.idType ?? "ghana_card",
      idNumber: agreement.parties[0]?.idNumber ?? "",
    };

    const partyB: PartyDraft = {
      fullName: agreement.parties[1]?.displayName ?? "",
      phone: agreement.parties[1]?.phone ?? "",
      idType: agreement.parties[1]?.idType ?? "ghana_card",
      idNumber: agreement.parties[1]?.idNumber ?? "",
    };

    const stepIndex = 0;

    const subjectData = agreement.fieldData ?? {};

    return {
      agreementId,
      scenarioId: agreement.scenarioId,
      stepIndex,
      partyA,
      partyB,
      subjectData,
    };
  };

  const save = async (delta: Partial<DraftState>): Promise<void> => {
    if (delta.subjectData !== undefined) {
      const agreementId = delta.agreementId ?? store.agreementId;
      if (agreementId === null) {
        throw new Error("Cannot save: no agreement ID available");
      }
      await updateAgreement(agreementId, { field_data: delta.subjectData });
    }
  };

  const abandon = (): void => {
    store.reset();
  };

  return { load, save, abandon };
}