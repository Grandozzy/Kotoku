import { useLocalSearchParams, useRouter } from "expo-router";
import { CheckCircle2 } from "lucide-react-native";
import { useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";

import { Button, NoticeCard, OTPInput } from "@/components/ui";
import { KotokuLogo } from "@/components/brand/KotokuLogo";
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
    if (code.length < 4) return;
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
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="flex-grow px-lg py-2xl justify-center gap-xl"
      keyboardShouldPersistTaps="handled"
    >
      <View className="items-center gap-md">
        <KotokuLogo variant="stacked" size={68} color="navy" />
        <View className="items-center gap-xs">
          <Text className="text-xs font-semibold uppercase tracking-widest text-brand-primary">
            Verify phone
          </Text>
          <Text className="text-3xl font-bold text-ink-primary text-center">
            Enter your code
          </Text>
          <Text className="text-md text-ink-secondary text-center leading-relaxed px-sm">
            We sent a 4-digit code to{" "}
            <Text className="font-semibold text-ink-primary">{phone}</Text>.
            {" "}It expires in {OTP_EXPIRY_SECONDS / 60} minutes.
          </Text>
        </View>
      </View>

      <View className="rounded-3xl border border-border-subtle bg-surface-card p-xl gap-lg shadow-sm">
        <OTPInput
          value={code}
          onChange={(val) => {
            setCode(val);
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
          disabled={code.length < 4 || isDisabled}
          loading={isLoading}
          onPress={handleVerify}
        />

        <View className="items-center gap-xs">
          <Text className="text-sm text-ink-muted">Didn&apos;t receive a code?</Text>
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

      <NoticeCard
        variant="info"
        title="Wrong number?"
        body="Go back and request a fresh code for the correct phone number."
        footer={
          <Pressable onPress={() => router.back()} disabled={isDisabled}>
            <Text className="text-sm font-medium text-brand-primary text-center">
              Go back
            </Text>
          </Pressable>
        }
        compact
      />
    </ScrollView>
  );
}
