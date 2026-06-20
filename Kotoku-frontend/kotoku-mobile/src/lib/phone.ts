export function normalizePhoneForCompare(phone?: string | null): string {
  const digits = String(phone ?? "").replace(/\D/g, "");
  if (digits.startsWith("0") && digits.length === 10) {
    return `233${digits.slice(1)}`;
  }
  return digits;
}

export function normalizePhoneToE164(phone: string): string {
  const trimmed = phone.trim();
  const digits = trimmed.replace(/\D/g, "");
  if (digits.startsWith("0") && digits.length === 10) {
    return `+233${digits.slice(1)}`;
  }
  if (trimmed.startsWith("+") && digits.length > 0) {
    return `+${digits}`;
  }
  return trimmed;
}

export function isSamePhone(left?: string | null, right?: string | null): boolean {
  const normalizedLeft = normalizePhoneForCompare(left);
  const normalizedRight = normalizePhoneForCompare(right);
  return Boolean(normalizedLeft && normalizedLeft === normalizedRight);
}
