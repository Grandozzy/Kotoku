import type { Agreement } from "@/types/agreement";

import { isPartyIdentityComplete } from "./partyIdentity";

export function getDraftResumeStep(agreement: Agreement): {
  step: "parties" | "details" | "evidence" | "review";
  index: 0 | 1 | 2 | 3;
} {
  const hasRequiredParties = agreement.parties.length >= 2;
  const partiesReady =
    hasRequiredParties &&
    agreement.parties.every((party) => isPartyIdentityComplete(party));

  if (!partiesReady) {
    return { step: "parties", index: 0 };
  }

  const hasDetails = Object.keys(agreement.fieldData ?? {}).length > 0;
  if (!hasDetails) {
    return { step: "details", index: 1 };
  }

  return { step: "evidence", index: 2 };
}
