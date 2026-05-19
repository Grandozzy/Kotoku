import { useAgreementStore } from "@/features/agreements/agreementStore";
import type { PartyDraft } from "@/features/agreements/agreementStore";
import { getAgreement, setParties, updateAgreement } from "@/api/agreements";
import type { PartyPayload } from "@/api/agreements";

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

    return {
      agreementId,
      scenarioId: agreement.scenarioId,
      stepIndex: agreement.stepIndex ?? 0,
      partyA,
      partyB,
      subjectData: agreement.fieldData ?? {},
    };
  };

  const saveStepProgress = async (
    agreementId: number,
    stepIndex: number,
    fieldData?: Record<string, unknown>,
  ): Promise<void> => {
    const payload: Record<string, unknown> = { step_index: stepIndex };
    if (fieldData !== undefined) {
      payload.field_data = fieldData;
    }
    await updateAgreement(agreementId, payload);
  };

  const saveParties = async (
    agreementId: number,
    parties: PartyPayload[],
  ): Promise<void> => {
    await setParties(agreementId, parties);
  };

  const abandon = (): void => {
    store.reset();
  };

  return { load, saveStepProgress, saveParties, abandon };
}
