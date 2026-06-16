// src/hooks/useSmsOtp.ts
// Android SMS User Consent API — prompts the user to share a received SMS so
// we can extract the OTP automatically. No app hash required.
import { useEffect } from "react";
import { Platform } from "react-native";

/**
 * On Android, starts a one-shot SMS User Consent listener.
 * When an SMS arrives while the listener is active the system shows a
 * permission dialog; if the user accepts, `onCode` is called with the
 * extracted digits.
 *
 * Does nothing on iOS (iOS autofill is handled by `textContentType="oneTimeCode"`).
 *
 * @param length  Expected OTP length (used to extract the right digit run).
 * @param onCode  Called with the extracted digit string on success.
 */
export function useSmsOtp(length: number, onCode: (code: string) => void) {
  useEffect(() => {
    if (Platform.OS !== "android") return;

    let cancelled = false;

    const startListener = async () => {
      try {
        // Dynamic import so the native module is never loaded on iOS.
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const SMSUserConsent = (await import("react-native-sms-user-consent"))
          .default;

        const result = await SMSUserConsent.listenOTP();
        if (cancelled) return;

        const message: string = result?.receivedOtpMessage ?? "";
        // Extract the first run of `length` consecutive digits from the message.
        const match = message.match(/\d+/g);
        if (!match) return;

        const digits = match
          .join("")
          .replace(/\D/g, "")
          .match(new RegExp(`\\d{${length}}`))?.[0];

        if (digits) onCode(digits);
      } catch {
        // User dismissed the dialog or no SMS arrived — silently ignore.
      }
    };

    startListener();

    return () => {
      cancelled = true;
      // Best-effort cleanup; ignore errors if listener already resolved.
      import("react-native-sms-user-consent")
        .then(({ default: SMSUserConsent }) => SMSUserConsent.removeOTPListener())
        .catch(() => {});
    };
  }, [length, onCode]);
}
