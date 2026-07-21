// src/components/ui/OTPInput.tsx
import React, { useCallback, useRef } from "react";
import {
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { useSmsOtp } from "@/hooks/useSmsOtp";
import { cn } from "@/lib/cn";

interface OTPInputProps {
  length?: number;
  value: string;
  onChange: (val: string) => void;
  error?: string;
  disabled?: boolean;
  secureTextEntry?: boolean;
}

const normalizeOtpValue = (text: string, length: number) =>
  text.replace(/\D/g, "").slice(0, length);

export const OTPInput: React.FC<OTPInputProps> = ({
  length = 6,
  value,
  onChange,
  error,
  disabled,
  secureTextEntry,
}) => {
  const inputRef = useRef<TextInput | null>(null);
  const displayValue = normalizeOtpValue(value, length);

  const focusInput = useCallback(() => {
    if (disabled) return;
    inputRef.current?.focus();
  }, [disabled]);

  const handleOtpChange = useCallback(
    (text: string) => {
      onChange(normalizeOtpValue(text, length));
    },
    [length, onChange],
  );

  // Android: auto-fill via SMS User Consent API when an SMS arrives.
  const handleSmsCode = useCallback(
    (code: string) => {
      handleOtpChange(code);
      focusInput();
    },
    [focusInput, handleOtpChange],
  );
  useSmsOtp(length, handleSmsCode);

  const cellBorder = error ? "border-semantic-error" : "border-border-subtle";
  const cellBorderFilled = error ? "border-semantic-error" : "border-brand-primary";

  return (
    <View>
      <Pressable
        className="items-center"
        disabled={disabled}
        onPress={focusInput}
        accessibilityRole="button"
        accessibilityLabel="OTP code input"
      >
        <View className="flex-row justify-center gap-xs">
          {Array.from({ length }).map((_, idx) => {
            const digit = displayValue[idx] ?? "";
            const filled = Boolean(digit);
            return (
              <View
                key={idx}
                className={cn(
                  "w-9 h-11 items-center justify-center rounded-md border",
                  filled ? cellBorderFilled : cellBorder,
                  "bg-surface-card",
                  disabled && "opacity-40",
                )}
              >
                <Text className="text-lg font-semibold text-ink-primary">
                  {secureTextEntry && digit ? "•" : digit}
                </Text>
              </View>
            );
          })}
        </View>

        <TextInput
          ref={inputRef}
          keyboardType="number-pad"
          maxLength={length}
          textContentType={Platform.OS === "ios" ? "oneTimeCode" : undefined}
          value={displayValue}
          editable={!disabled}
          onChangeText={handleOtpChange}
          caretHidden
          selectTextOnFocus={false}
          contextMenuHidden={false}
          className="text-transparent"
          style={styles.hiddenInput}
          accessibilityLabel="OTP code"
          importantForAccessibility="no-hide-descendants"
        />
      </Pressable>

      {error && (
        <Text className="mt-xs text-xs text-semantic-error text-center">
          {error}
        </Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  hiddenInput: {
    ...StyleSheet.absoluteFillObject,
    opacity: 0.01,
  },
});
