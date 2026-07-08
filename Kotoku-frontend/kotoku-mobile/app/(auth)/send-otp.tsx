import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { ScrollView, Text, View } from "react-native";

import { Button, NoticeCard, TextInput } from "@/components/ui";
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
          render={({ field: { value, onChange, onBlur } }) => (
            <TextInput
              label="Phone number"
              placeholder="+233 XX XXX XXXX"
              keyboardType="phone-pad"
              autoFocus
              autoCorrect={false}
              value={value}
              onChangeText={onChange}
              onBlur={onBlur}
              error={errors.phone?.message}
              hint="Use the same number linked to your Kotoku agreements."
              required
            />
          )}
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
