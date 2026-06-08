import { useLocalSearchParams, useRouter } from "expo-router";
import { CheckCircle2 } from "lucide-react-native";
import { useState } from "react";
import { Pressable, Text, View } from "react-native";

import { Button, OTPInput } from "@/components/ui";
import { OTP_EXPIRY_SECONDS } from "@/constants/config";
import {
  getApiErrorMessage,
  useResendOtp,
  useVerifyOtp,
} from "@/features/auth/otpFlow";

export default function VerifyOtpScreen() {
  const router = useRouter();
  const { phone } = useLocalSearchParams<{ phone: string }>();
  const [code, setCode] = useState("");

  const verifyMutation = useVerifyOtp(phone ?? "");
  const resendMutation = useResendOtp(phone ?? "");

  const handleVerify = () => {
    if (code.length < 8) return;
    verifyMutation.mutate(code);
  };

  const handleResend = () => {
    setCode("");
    verifyMutation.reset();
    resendMutation.mutate();
  };

  // Surface the most relevant error — verify takes priority over resend
  const apiError = verifyMutation.isError
    ? getApiErrorMessage(verifyMutation.error)
    : null;

  const isLoading = verifyMutation.isPending;
  const isDisabled = isLoading || resendMutation.isPending;

  return (
    <View className="flex-1 bg-surface-canvas px-lg justify-center gap-xl">
      <View className="gap-sm">
        <Text className="text-2xl font-semibold text-ink-primary">
          Enter your code
        </Text>
        <Text className="text-md text-ink-secondary">
          We sent an 8-digit code to{" "}
          <Text className="font-semibold text-ink-primary">{phone}</Text>.
          {"\n"}It expires in {OTP_EXPIRY_SECONDS / 60} minutes.
        </Text>
      </View>

      <View className="gap-lg">
        <OTPInput
          value={code}
          onChange={(val) => {
            setCode(val);
            // Clear error as user re-enters
            if (verifyMutation.isError) verifyMutation.reset();
          }}
          error={apiError ?? undefined}
          disabled={isDisabled}
        />

        <Button
          title="Verify"
          variant="primary"
          size="lg"
          fullWidth
          disabled={code.length < 8 || isDisabled}
          loading={isLoading}
          onPress={handleVerify}
        />

        {/* Resend */}
        <View className="items-center gap-xs">
          <Text className="text-sm text-ink-muted">Didn't receive a code?</Text>
          <Pressable
            onPress={handleResend}
            disabled={isDisabled || resendMutation.isPending}
          >
            {resendMutation.isSuccess ? (
              <View className="flex-row items-center gap-xs">
                <CheckCircle2 size={14} color="#16a34a" strokeWidth={2} />
                <Text className="text-sm text-brand-primary font-medium">Code sent</Text>
              </View>
            ) : (
              <Text
                className={
                  resendMutation.isPending
                    ? "text-sm text-ink-muted"
                    : "text-sm text-brand-primary font-medium"
                }
              >
                {resendMutation.isPending ? "Sending..." : "Resend code"}
              </Text>
            )}
          </Pressable>
        </View>
      </View>

      {/* Back */}
      <Pressable onPress={() => router.back()} disabled={isDisabled}>
        <Text className="text-sm text-brand-primary text-center">
          Wrong number? Go back
        </Text>
      </Pressable>
    </View>
  );
}
