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

    const stepIndex = agreement.stepIndex ?? 0;

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
    const agreementId = delta.agreementId ?? store.agreementId;
    if (agreementId === null) {
      throw new Error("Cannot save: no agreement ID available");
    }

    const payload: Record<string, unknown> = {};
    if (delta.subjectData !== undefined) payload.field_data = delta.subjectData;
    if (delta.stepIndex !== undefined) payload.step_index = delta.stepIndex;
    if (delta.partyA !== undefined || delta.partyB !== undefined) {
      const partyA = delta.partyA ?? store.partyA;
      const partyB = delta.partyB ?? store.partyB;
      payload.parties = [
        { role: "party_a", full_name: partyA.fullName, phone: partyA.phone, id_type: partyA.idType, id_number: partyA.idNumber },
        { role: "party_b", full_name: partyB.fullName, phone: partyB.phone, id_type: partyB.idType, id_number: partyB.idNumber },
      ];
    }

    if (Object.keys(payload).length > 0) {
      await updateAgreement(agreementId, payload);
    }
  };

  const abandon = (): void => {
    store.reset();
  };

  return { load, save, abandon };
}