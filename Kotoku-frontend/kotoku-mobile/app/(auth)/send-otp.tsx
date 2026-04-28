import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { Text, View } from "react-native";

import { Button, TextInput } from "@/components/ui";
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
    <View className="flex-1 bg-surface-canvas px-lg justify-center gap-xl">
      <View className="gap-sm">
        <Text className="text-2xl font-semibold text-ink-primary">
          Enter your number
        </Text>
        <Text className="text-md text-ink-secondary">
          We will send you a one-time code to verify your phone.
        </Text>
      </View>

      <View className="gap-lg">
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
              required
            />
          )}
        />

        {/* API-level error (e.g. rate limited, server down) */}
        {mutation.isError && (
          <Text className="text-sm text-semantic-error text-center">
            {getApiErrorMessage(mutation.error)}
          </Text>
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
    </View>
  );
}
