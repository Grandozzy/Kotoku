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
    if (Platform.OS !== "android" || length <= 0) return;

    let cancelled = false;
    let stopSmsHandling: (() => void) | null = null;

    const startListener = async () => {
      try {
        const mod = await import("@eabdullazyanov/react-native-sms-user-consent");
        if (cancelled) return;
        if (typeof mod?.startSmsHandling !== "function") return;
        const { retrieveVerificationCode, startSmsHandling: startSmsConsent } = mod;

        stopSmsHandling = startSmsConsent((event) => {
          if (cancelled) return;
          const message = event?.sms ?? "";
          const digits = retrieveVerificationCode(message, length);
          if (digits) onCode(digits);
        });
      } catch {
        // Library not available or incompatible with current RN arch — OTP autofill
        // is optional; manual entry still works.
      }
    };

    startListener();

    return () => {
      cancelled = true;
      stopSmsHandling?.();
    };
  }, [length, onCode]);
}
