import { create } from "zustand";

import type { ScenarioId } from "@/constants/scenarios";

export type IdType = "ghana_card" | "passport" | "national_id";

export interface PartyDraft {
  fullName: string;
  phone: string;
  idType: IdType;
  idNumber: string;
}

export interface ConsentPartyState {
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
  initReopened: (agreementId: number, scenarioId: ScenarioId, partyA?: PartyDraft, partyB?: PartyDraft, subjectData?: Record<string, unknown>) => void;
  initForConsent: (agreementId: number, scenarioId: ScenarioId, partyA: PartyDraft, partyB: PartyDraft) => void;
  setScenarioId: (id: ScenarioId | null) => void;
  goToStep: (index: number) => void;
  nextStep: () => void;
  prevStep: () => void;
  setPartyA: (party: PartyDraft) => void;
  setPartyB: (party: PartyDraft) => void;
  setSubjectData: (data: Record<string, unknown>) => void;
  setConsentSent: (party: "A" | "B") => void;
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

  initReopened: (agreementId, scenarioId, partyA, partyB, subjectData) =>
    set({
      agreementId,
      scenarioId,
      stepIndex: 0,
      isReopened: true,
      partyA: partyA ?? emptyParty,
      partyB: partyB ?? emptyParty,
      subjectData: subjectData ?? {},
    }),

  initForConsent: (agreementId, scenarioId, partyA, partyB) =>
    set({
      agreementId,
      scenarioId,
      stepIndex: 4,
      isReopened: false,
      partyA,
      partyB,
      subjectData: {},
    }),

  setScenarioId: (id) => set({ scenarioId: id }),

  goToStep: (index) => set({ stepIndex: index }),

  nextStep: () =>
    set((s) => ({ stepIndex: Math.min(s.stepIndex + 1, STEPS.length - 1) })),

  prevStep: () =>
    set((s) => ({ stepIndex: Math.max(s.stepIndex - 1, 0) })),

  setPartyA: (partyA) => set({ partyA }),
  setPartyB: (partyB) => set({ partyB }),
  setSubjectData: (subjectData) => set({ subjectData }),

  setConsentSent: (party) =>
    set((s) =>
      party === "A"
        ? { consentA: { ...s.consentA, otpSent: true } }
        : { consentB: { ...s.consentB, otpSent: true } },
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
