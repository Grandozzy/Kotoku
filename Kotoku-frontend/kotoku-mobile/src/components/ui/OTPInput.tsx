// src/components/ui/OTPInput.tsx
import React, { useCallback, useRef } from "react";
import {
  NativeSyntheticEvent,
  Platform,
  Text,
  TextInput,
  View,
} from "react-native";

// KeyboardEventData is the non-deprecated successor to TextInputKeyPressEventData
type KeyboardEventData = { key: string };

import { cn } from "@/lib/cn";
import { useSmsOtp } from "@/hooks/useSmsOtp";

interface OTPInputProps {
  // Default is 8 to match Kotoku's OTP policy (8-digit codes).
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
  length = 8,
  value,
  onChange,
  error,
  disabled,
  secureTextEntry,
}) => {
  const inputs = useRef<Array<TextInput | null>>([]);
  const displayValue = normalizeOtpValue(value, length);

  const focusCell = useCallback((index: number) => {
    requestAnimationFrame(() => {
      inputs.current[Math.max(0, Math.min(index, length - 1))]?.focus();
    });
  }, [length]);

  // Android: auto-fill via SMS User Consent API when an SMS arrives.
  const handleSmsCode = useCallback(
    (code: string) => {
      const digits = normalizeOtpValue(code, length);
      onChange(digits);
      // Focus the last filled cell (or last cell if fully filled).
      focusCell(digits.length);
    },
    [focusCell, length, onChange],
  );
  useSmsOtp(length, handleSmsCode);

  const handleChange = (text: string, index: number) => {
    const digits = normalizeOtpValue(text, length);

    // Pasting/autofill can insert the full OTP into a single focused cell.
    // Replace the full OTP value so this behaves consistently across flows.
    if (
      digits.length === 2 &&
      displayValue[index] &&
      digits.startsWith(displayValue[index])
    ) {
      const typedDigit = digits.slice(-1);
      const next =
        displayValue.substring(0, index) +
        typedDigit +
        displayValue.substring(index + 1);
      onChange(next);
      if (index < length - 1) {
        focusCell(index + 1);
      }
      return;
    }

    if (digits.length > 1) {
      onChange(digits);
      focusCell(digits.length);
      return;
    }

    if (!digits) {
      const next =
        displayValue.substring(0, index) + displayValue.substring(index + 1);
      onChange(next);
      return;
    }

    const next =
      displayValue.substring(0, index) +
      digits +
      displayValue.substring(index + 1);
    onChange(next);
    if (index < length - 1) {
      focusCell(index + 1);
    }
  };

  const handleKeyPress = (
    e: NativeSyntheticEvent<KeyboardEventData>,
    index: number,
  ) => {
    if (e.nativeEvent.key === "Backspace" && !displayValue[index] && index > 0) {
      focusCell(index - 1);
    }
  };

  const cellBorder = error ? "border-semantic-error" : "border-border-subtle";
  const cellBorderFilled = error ? "border-semantic-error" : "border-brand-primary";

  return (
    <View>
      <View className="flex-row justify-center gap-xs">
        {Array.from({ length }).map((_, idx) => {
          const filled = Boolean(displayValue[idx]);
          return (
            <View
              key={idx}
              className={cn(
                // w-9 (36px) × 8 cells + gap-xs (4px) × 7 = 288 + 28 = 316px — fits 360px screens
                "w-9 h-11 items-center justify-center rounded-md border",
                filled ? cellBorderFilled : cellBorder,
                "bg-surface-card",
                disabled && "opacity-40",
              )}
            >
              <TextInput
                ref={(ref) => { inputs.current[idx] = ref; }}
                keyboardType="number-pad"
                maxLength={length}
                textContentType={Platform.OS === "ios" ? "oneTimeCode" : undefined}
                value={secureTextEntry && displayValue[idx] ? "•" : (displayValue[idx] ?? "")}
                editable={!disabled}
                onChangeText={(t) => handleChange(t, idx)}
                onKeyPress={(e) => handleKeyPress(e, idx)}
                className="w-full text-center text-lg font-semibold text-ink-primary"
                style={{ height: "100%", paddingTop: 0, paddingBottom: 0 }}
                textAlignVertical="center"
                accessibilityLabel={`OTP digit ${idx + 1}`}
              />
            </View>
          );
        })}
      </View>

      {error && (
        <Text className="mt-xs text-xs text-semantic-error text-center">
          {error}
        </Text>
      )}
    </View>
  );
};
