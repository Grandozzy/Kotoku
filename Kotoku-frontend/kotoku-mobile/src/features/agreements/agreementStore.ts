import { create } from "zustand";

import type { ScenarioId } from "@/constants/scenarios";

export type IdType = "ghana_card" | "passport" | "other";

export interface PartyDraft {
  fullName: string;
  phone: string;
  idType: IdType;
  idNumber: string;
}

export interface ConsentPartyState {
  consentRecordId: number | null;
  otpSent: boolean;
  confirmed: boolean;
}

export const STEPS = ["parties", "details", "evidence", "review", "consent"] as const;
export type StepId = (typeof STEPS)[number];

interface AgreementDraftStore {
  // Agreement identity
  agreementId: number | null;
  scenarioId: ScenarioId | null;

  // Step tracking
  stepIndex: number;
  steps: readonly StepId[];

  // Draft data
  partyA: PartyDraft;
  partyB: PartyDraft;
  subjectData: Record<string, unknown>;

  // Consent state
  consentA: ConsentPartyState;
  consentB: ConsentPartyState;

  // Re-edit mode
  isReopened: boolean;

  // Actions
  initDraft: (agreementId: number, scenarioId: ScenarioId) => void;
  initReopened: (agreementId: number, scenarioId: ScenarioId) => void;
  goToStep: (index: number) => void;
  nextStep: () => void;
  prevStep: () => void;
  setPartyA: (party: PartyDraft) => void;
  setPartyB: (party: PartyDraft) => void;
  setSubjectData: (data: Record<string, unknown>) => void;
  setConsentSent: (party: "A" | "B", consentRecordId: number) => void;
  setConsentConfirmed: (party: "A" | "B") => void;
  reset: () => void;
}

const emptyParty: PartyDraft = {
  fullName: "",
  phone: "",
  idType: "ghana_card",
  idNumber: "",
};

const emptyConsent: ConsentPartyState = {
  consentRecordId: null,
  otpSent: false,
  confirmed: false,
};

export const useAgreementStore = create<AgreementDraftStore>((set) => ({
  agreementId: null,
  scenarioId: null,
  stepIndex: 0,
  steps: STEPS,
  partyA: emptyParty,
  partyB: emptyParty,
  subjectData: {},
  consentA: emptyConsent,
  consentB: emptyConsent,
  isReopened: false,

  initDraft: (agreementId, scenarioId) =>
    set({ agreementId, scenarioId, stepIndex: 0, isReopened: false }),

  initReopened: (agreementId, scenarioId) =>
    set({ agreementId, scenarioId, stepIndex: 0, isReopened: true }),

  goToStep: (index) => set({ stepIndex: index }),

  nextStep: () =>
    set((s) => ({ stepIndex: Math.min(s.stepIndex + 1, STEPS.length - 1) })),

  prevStep: () =>
    set((s) => ({ stepIndex: Math.max(s.stepIndex - 1, 0) })),

  setPartyA: (partyA) => set({ partyA }),
  setPartyB: (partyB) => set({ partyB }),
  setSubjectData: (subjectData) => set({ subjectData }),

  setConsentSent: (party, consentRecordId) =>
    set((s) =>
      party === "A"
        ? { consentA: { ...s.consentA, consentRecordId, otpSent: true } }
        : { consentB: { ...s.consentB, consentRecordId, otpSent: true } },
    ),

  setConsentConfirmed: (party) =>
    set((s) =>
      party === "A"
        ? { consentA: { ...s.consentA, confirmed: true } }
        : { consentB: { ...s.consentB, confirmed: true } },
    ),

  reset: () =>
    set({
      agreementId: null,
      scenarioId: null,
      stepIndex: 0,
      partyA: emptyParty,
      partyB: emptyParty,
      subjectData: {},
      consentA: emptyConsent,
      consentB: emptyConsent,
      isReopened: false,
    }),
}));
