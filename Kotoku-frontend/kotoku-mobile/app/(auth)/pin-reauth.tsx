import { useEffect, useState } from "react";
import { useLocalSearchParams } from "expo-router";
import { Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button } from "@/components/ui";
import { OTPInput } from "@/components/ui/OTPInput";
import { KotokuLogo } from "@/components/brand/KotokuLogo";
import { usePinVerify, getApiErrorMessage } from "@/features/auth/otpFlow";

export default function PinReauthScreen() {
  const insets = useSafeAreaInsets();
  const { phone } = useLocalSearchParams<{ phone: string }>();
  const mutation = usePinVerify(phone ?? "");
  const [value, setValue] = useState("");

  const isLocked = mutation.error
    ? (mutation.error as { status?: number }).status === 429
    : false;

  const isForceOtp = mutation.error
    ? (mutation.error as { response?: { data?: { data?: { force_otp?: boolean } } } })?.response?.data?.data?.force_otp === true
    : false;

  useEffect(() => {
    if (value.length < 4) return;
    mutation.mutate(value);
  }, [value]);

  // Reset input on error so user can retry
  useEffect(() => {
    if (mutation.isError) setValue("");
  }, [mutation.isError]);

  return (
    <View
      className="flex-1 bg-surface-canvas px-lg"
      style={{ paddingTop: insets.top + 48 }}
    >
      <View className="items-center mb-2xl">
        <KotokuLogo variant="stacked" size={64} color="navy" />
      </View>

      <View className="gap-xs mb-xl items-center">
        <Text className="text-2xl font-semibold text-ink-primary text-center">
          Welcome back
        </Text>
        <Text className="text-md text-ink-secondary text-center leading-relaxed">
          Enter your PIN to continue.
        </Text>
        {phone && (
          <Text className="text-sm text-ink-muted text-center mt-xs">{phone}</Text>
        )}
      </View>

      {!isForceOtp && (
        <OTPInput
          length={4}
          value={value}
          onChange={(val) => {
            mutation.reset();
            setValue(val);
          }}
          secureTextEntry
          disabled={mutation.isPending || isLocked}
          error={
            mutation.isError && !isForceOtp
              ? isLocked
                ? "Too many attempts. Please wait before trying again."
                : getApiErrorMessage(mutation.error)
              : undefined
          }
        />
      )}

      {mutation.isPending && (
        <Text className="mt-md text-sm text-ink-muted text-center">Verifying…</Text>
      )}

      {isForceOtp && (
        <View className="gap-md mt-lg items-center">
          <Text className="text-md text-semantic-error text-center font-medium">
            Too many failed attempts. You need to verify with OTP.
          </Text>
          <Button
            title="Sign in with phone"
            variant="primary"
            size="lg"
            fullWidth
            onPress={() => {
              import("@/lib/secureStore").then(({ clearSession }) => clearSession());
              import("@/store/sessionStore").then(({ useSessionStore }) =>
                useSessionStore.getState().clearSession()
              );
            }}
          />
        </View>
      )}
    </View>
  );
}
