import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { ScrollView, Text, View } from "react-native";

function normalizeLocalDigits(input: string): string {
  const d = input.replace(/\D/g, "");
  if (d.startsWith("233") && d.length >= 12) return d.slice(3, 12);
  if (d.startsWith("0") && d.length >= 10) return d.slice(1, 10);
  return d.slice(0, 9);
}

import { TextInput as RNTextInput } from "react-native";
import { Button, NoticeCard } from "@/components/ui";
import { KotokuLogo } from "@/components/brand/KotokuLogo";
import {
  getApiErrorMessage,
  phoneSchema,
  PhoneFormValues,
  useSendOtp,
} from "@/features/auth/otpFlow";

export default function SendOtpScreen() {
  const mutation = useSendOtp();

  const {
    control,
    handleSubmit,
    formState: { errors, isValid },
  } = useForm<PhoneFormValues>({
    resolver: zodResolver(phoneSchema),
    mode: "onChange",
    defaultValues: { phone: "" },
  });

  const onSubmit = (values: PhoneFormValues) => {
    mutation.mutate(values);
  };

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="flex-grow px-lg py-2xl justify-center gap-xl"
      keyboardShouldPersistTaps="handled"
    >
      <View className="items-center gap-md">
        <KotokuLogo variant="stacked" size={72} color="navy" />
        <View className="items-center gap-xs">
          <Text className="text-xs font-semibold uppercase tracking-widest text-brand-primary">
            Secure sign in
          </Text>
          <Text className="text-3xl font-bold text-ink-primary text-center">
            Enter your number
          </Text>
          <Text className="text-md text-ink-secondary text-center leading-relaxed px-md">
            We&apos;ll send a one-time code to verify your phone and reconnect you to your agreements.
          </Text>
        </View>
      </View>

      <View className="rounded-3xl border border-border-subtle bg-surface-card p-xl gap-lg shadow-sm">
        <Controller
          control={control}
          name="phone"
          render={({ field: { value, onChange, onBlur } }) => {
            const digits = normalizeLocalDigits(value.replace(/^\+233/, ""));
            return (
              <View className="w-full">
                <View className="flex-row mb-xs">
                  <Text className="text-sm font-medium text-ink-secondary">Phone number</Text>
                  <Text className="text-sm text-semantic-error ml-xs">*</Text>
                </View>
                <View className="flex-row items-center rounded-md border border-border-subtle bg-surface-card overflow-hidden">
                  <View className="px-md py-sm border-r border-border-subtle">
                    <Text className="text-md text-ink-primary">🇬🇭 +233</Text>
                  </View>
                  <RNTextInput
                    className="flex-1 px-md py-sm text-md text-ink-primary"
                    placeholder="XX XXX XXXX"
                    keyboardType="phone-pad"
                    maxLength={9}
                    autoFocus
                    autoCorrect={false}
                    value={digits}
                    onChangeText={(d) => onChange(`+233${normalizeLocalDigits(d)}`)}
                    onBlur={onBlur}
                    placeholderTextColor="#94A3B8"
                  />
                </View>
                {errors.phone && (
                  <Text className="mt-xs text-xs text-semantic-error">{errors.phone.message}</Text>
                )}
                <Text className="mt-xs text-xs text-ink-muted">
                  Use the same number linked to your Kotoku agreements.
                </Text>
              </View>
            );
          }}
        />

        {mutation.isError && (
          <NoticeCard
            variant="error"
            title="Could not send code"
            body={getApiErrorMessage(mutation.error)}
            compact
          />
        )}

        <Button
          title="Send code"
          variant="primary"
          size="lg"
          fullWidth
          disabled={!isValid}
          loading={mutation.isPending}
          onPress={handleSubmit(onSubmit)}
        />
      </View>

      <NoticeCard
        variant="info"
        title="Why phone verification matters"
        body="Each OTP is tied to the phone number used for consent, disputes, and vault access. That is what gives your record legal weight."
        compact
      />
    </ScrollView>
  );
}
