/**
 * Normalize phone number to E.164 format.
 * Handles Ghana numbers: 0501234567 → +233501234567
 */
export function normalizePhone(phone: string): string {
  const cleaned = phone.replace(/\s/g, "");

  // Already in E.164 format
  if (cleaned.startsWith("+")) {
    return cleaned;
  }

  // Ghana format: starts with 0, prefix with +233
  if (cleaned.startsWith("0") && cleaned.length === 10) {
    return `+233${cleaned.substring(1)}`;
  }

  // Assume E.164 without +
  if (/^\d{10,15}$/.test(cleaned)) {
    return `+${cleaned}`;
  }

  return cleaned;
}