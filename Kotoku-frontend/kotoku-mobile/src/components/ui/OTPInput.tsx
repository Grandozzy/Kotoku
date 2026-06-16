// src/components/ui/OTPInput.tsx
import React, { useRef } from "react";
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

interface OTPInputProps {
  // Default is 8 to match Kotoku's OTP policy (8-digit codes).
  length?: number;
  value: string;
  onChange: (val: string) => void;
  error?: string;
  disabled?: boolean;
  secureTextEntry?: boolean;
}

export const OTPInput: React.FC<OTPInputProps> = ({
  length = 8,
  value,
  onChange,
  error,
  disabled,
  secureTextEntry,
}) => {
  const inputs = useRef<Array<TextInput | null>>([]);

  const handleChange = (text: string, index: number) => {
    // iOS OTP autofill pastes the full code into the focused cell at once.
    // Distribute digits across all cells starting from index 0.
    if (text.length > 1) {
      const digits = text.replace(/\D/g, "").slice(0, length);
      onChange(digits.padEnd(length, " ").slice(0, length).trimEnd());
      const nextFocus = Math.min(digits.length, length - 1);
      inputs.current[nextFocus]?.focus();
      return;
    }
    const digit = text.slice(-1);
    const next =
      value.substring(0, index) + digit + value.substring(index + 1);
    onChange(next);
    if (digit && index < length - 1) {
      inputs.current[index + 1]?.focus();
    }
  };

  const handleKeyPress = (
    e: NativeSyntheticEvent<KeyboardEventData>,
    index: number,
  ) => {
    if (e.nativeEvent.key === "Backspace" && !value[index] && index > 0) {
      inputs.current[index - 1]?.focus();
    }
  };

  const cellBorder = error ? "border-semantic-error" : "border-border-subtle";
  const cellBorderFilled = error ? "border-semantic-error" : "border-brand-primary";

  return (
    <View>
      <View className="flex-row justify-center gap-xs">
        {Array.from({ length }).map((_, idx) => {
          const filled = Boolean(value[idx]);
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
                maxLength={Platform.OS === "ios" ? length : 1}
                textContentType={Platform.OS === "ios" ? "oneTimeCode" : undefined}
                value={secureTextEntry && value[idx] ? "•" : (value[idx] ?? "")}
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
