const E164_PHONE_PATTERN = /^\+[1-9]\d{9,14}$/;

export function isValidE164Phone(phone: string): boolean {
  return E164_PHONE_PATTERN.test(phone.trim());
}
