import { useEffect, useState } from "react";
import { Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button } from "@/components/ui";
import { OTPInput } from "@/components/ui/OTPInput";
import { KotokuLogo } from "@/components/brand/KotokuLogo";
import { usePinSetup, validatePinStrength } from "@/features/auth/otpFlow";

type Step = "enter" | "confirm";

export default function PinSetupScreen() {
  const insets = useSafeAreaInsets();
  const mutation = usePinSetup();

  const [step, setStep] = useState<Step>("enter");
  const [firstPin, setFirstPin] = useState("");
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (value.length < 4) return;

    if (step === "enter") {
      const strengthError = validatePinStrength(value);
      if (strengthError) {
        setError(strengthError);
        setValue("");
        return;
      }
      setError(null);
      setFirstPin(value);
      setValue("");
      setStep("confirm");
    } else {
      if (value !== firstPin) {
        setError("PINs do not match. Try again.");
        setValue("");
        setStep("enter");
        setFirstPin("");
        return;
      }
      setError(null);
      mutation.mutate(value);
    }
  }, [value]);

  return (
    <View
      className="flex-1 bg-surface-canvas px-lg"
      style={{ paddingTop: insets.top + 32 }}
    >
      <View className="items-center mb-2xl">
        <KotokuLogo variant="icon" size={48} color="navy" />
      </View>

      <View className="gap-xs mb-xl">
        <Text className="text-2xl font-semibold text-ink-primary">
          {step === "enter" ? "Create your Kotoku PIN" : "Confirm your PIN"}
        </Text>
        <Text className="text-md text-ink-secondary leading-relaxed">
          {step === "enter"
            ? "Your 4-digit PIN keeps your agreements safe. You'll use it every time you open Kotoku."
            : "Enter your PIN again to confirm."}
        </Text>
      </View>

      <OTPInput
        length={4}
        value={value}
        onChange={(val) => {
          setError(null);
          setValue(val);
        }}
        secureTextEntry
        disabled={mutation.isPending}
        error={error ?? undefined}
      />

      {mutation.isError && (
        <Text className="mt-md text-sm text-semantic-error text-center">
          Failed to save PIN. Please try again.
        </Text>
      )}

      {mutation.isPending && (
        <View className="mt-xl items-center">
          <Button title="Saving…" variant="primary" size="lg" fullWidth disabled loading />
        </View>
      )}
    </View>
  );
}
