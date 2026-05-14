import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { z } from "zod";

import {
  fetchMe,
  sendOtp,
  setupPin,
  signOut,
  signOutAll,
  updateProfile,
  verifyOtp,
  verifyPin,
} from "@/api/auth";
import { getApiErrorMessage } from "@/lib/errorHandler";
import { clearSession, savePinConfigured, saveSession } from "@/lib/secureStore";
import { useSessionStore } from "@/store/sessionStore";

// ---------- Validation schemas ----------

export const phoneSchema = z.object({
  phone: z
    .string()
    .min(1, "Phone number is required.")
    .regex(
      /^\+[1-9]\d{9,14}$/,
      "Enter a valid number with country code, e.g. +233XXXXXXXXX",
    ),
});

export const otpSchema = z.object({
  code: z.string().length(6, "Enter the full 6-digit code."),
});

export const pinSchema = z.object({
  pin: z
    .string()
    .length(4, "PIN must be 4 digits.")
    .regex(/^\d{4}$/, "PIN must be 4 digits."),
});

export const pinConfirmSchema = pinSchema
  .extend({ confirm: z.string().length(4) })
  .refine((d) => d.pin === d.confirm, {
    message: "PINs do not match.",
    path: ["confirm"],
  });

const SEQUENTIAL_PINS = new Set([
  "0000", "1111", "2222", "3333", "4444",
  "5555", "6666", "7777", "8888", "9999",
  "1234", "2345", "3456", "4567", "5678",
  "6789", "9876", "8765", "7654", "6543",
  "5432", "4321",
]);

export function validatePinStrength(pin: string): string | null {
  if (SEQUENTIAL_PINS.has(pin)) return "PIN is too simple. Avoid repeated or sequential digits.";
  return null;
}

export type PhoneFormValues = z.infer<typeof phoneSchema>;
export type OtpFormValues = z.infer<typeof otpSchema>;
export type PinFormValues = z.infer<typeof pinSchema>;

// ---------- OTP hooks ----------

export function useSendOtp() {
  const router = useRouter();

  return useMutation({
    mutationFn: sendOtp,
    onSuccess: (_, variables) => {
      router.push({
        pathname: "/(auth)/verify-otp",
        params: { phone: variables.phone },
      });
    },
  });
}

export function useVerifyOtp(phone: string) {
  const setSession = useSessionStore((s) => s.setSession);
  const router = useRouter();

  return useMutation({
    mutationFn: (code: string) => verifyOtp({ phone, code }),
    onSuccess: async (data) => {
      const { access, refresh, session_id, user } = data;
      await saveSession(access, refresh, session_id, phone, user.account_id, user.pin_configured);
      setSession(access, phone, user.account_id, user.pin_configured);
      if (!user.pin_configured) {
        router.replace("/(auth)/pin-setup" as never);
      } else {
        router.replace("/(main)/home");
      }
    },
  });
}

export function useResendOtp(phone: string) {
  return useMutation({ mutationFn: () => sendOtp({ phone }) });
}

// ---------- PIN hooks ----------

export function usePinSetup() {
  const setPinConfigured = useSessionStore((s) => s.setPinConfigured);
  const router = useRouter();

  return useMutation({
    mutationFn: (pin: string) => setupPin(pin),
    onSuccess: async () => {
      await savePinConfigured(true);
      setPinConfigured(true);
      router.replace("/(main)/home");
    },
  });
}

export function usePinVerify(phone: string) {
  const setSession = useSessionStore((s) => s.setSession);
  const router = useRouter();

  return useMutation({
    mutationFn: (pin: string) => verifyPin({ phone, pin }),
    onSuccess: async (data) => {
      const { access, refresh, session_id, user } = data;
      await saveSession(access, refresh, session_id, phone, user.account_id, true);
      setSession(access, phone, user.account_id, true);
      router.replace("/(main)/home");
    },
  });
}

// ---------- Sign-out hooks ----------

export function useSignOut() {
  const clearStoreSession = useSessionStore((s) => s.clearSession);
  const router = useRouter();

  return useMutation({
    mutationFn: async () => {
      try {
        await signOut();
      } finally {
        await clearSession();
        clearStoreSession();
      }
    },
    onSuccess: () => {
      router.replace("/(auth)/welcome");
    },
  });
}

export function useSignOutAll() {
  const clearStoreSession = useSessionStore((s) => s.clearSession);
  const router = useRouter();

  return useMutation({
    mutationFn: async () => {
      try {
        await signOutAll();
      } finally {
        await clearSession();
        clearStoreSession();
      }
    },
    onSuccess: () => {
      router.replace("/(auth)/welcome");
    },
  });
}

// ---------- Current user ----------

export function useMe() {
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);

  return useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 10,
  });
}

// ---------- Profile update ----------

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

// ---------- Shared error extractor ----------

export { getApiErrorMessage };
