import type { PartyDraft } from "./agreementStore";
import { GHANA_CARD_PIN_REGEX, normalizeGhanaCardPin } from "./partyIdentity";

export function isPartyComplete(party: PartyDraft): boolean {
  return (
    party.fullName.trim().length > 0 &&
    party.phone.trim().length >= 10 &&
    GHANA_CARD_PIN_REGEX.test(normalizeGhanaCardPin(party.idNumber))
  );
}

export function arePartiesComplete(
  partyA: PartyDraft,
  partyB: PartyDraft,
): boolean {
  return isPartyComplete(partyA) && isPartyComplete(partyB);
}

// Returns field keys from the template that are required but missing a value
export function getMissingRequiredFields(
  requiredFields: string[],
  subjectData: Record<string, unknown>,
): string[] {
  return requiredFields.filter((key) => {
    const value = subjectData[key];
    return value === undefined || value === null || value === "";
  });
}
