import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { z } from "zod";

import { fetchMe, sendOtp, updateProfile, verifyOtp } from "@/api/auth";
import { getApiErrorMessage } from "@/lib/errorHandler";
import { saveSession } from "@/lib/secureStore";
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
  code: z
    .string()
    .length(8, "Enter the full 8-digit code."),
});

export type PhoneFormValues = z.infer<typeof phoneSchema>;
export type OtpFormValues = z.infer<typeof otpSchema>;

// ---------- Hooks ----------

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
    // Error is handled in the screen via mutation.error
  });
}

export function useVerifyOtp(phone: string) {
  const setSession = useSessionStore((s) => s.setSession);
  const router = useRouter();

  return useMutation({
    mutationFn: (code: string) => verifyOtp({ phone, code }),
    onSuccess: async (data) => {
      await saveSession(data.token, phone, data.account_id);
      setSession(data.token, phone, data.account_id);
      router.replace("/(main)/home");
    },
  });
}

export function useResendOtp(phone: string) {
  return useMutation({
    mutationFn: () => sendOtp({ phone }),
  });
}

// ---------- Current user ----------

export function useMe() {
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);

  return useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 10, // 10 minutes
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
