// src/components/ui/OTPInput.tsx
import React, { useEffect, useRef } from "react";
import {
  NativeSyntheticEvent,
  Platform,
  Text,
  TextInput,
  View,
} from "react-native";

type KeyboardEventData = { key: string };

import { cn } from "@/lib/cn";

interface OTPInputProps {
  // Default is 6 to match Kotoku's OTP policy (6-digit codes).
  length?: number;
  value: string;
  onChange: (val: string) => void;
  error?: string;
  disabled?: boolean;
  secureTextEntry?: boolean;
}

export const OTPInput: React.FC<OTPInputProps> = ({
  length = 6,
  value,
  onChange,
  error,
  disabled,
  secureTextEntry,
}) => {
  const inputs = useRef<Array<TextInput | null>>([]);
  const isDeleting = useRef(false);

  // Auto-focus the first empty cell
  useEffect(() => {
    const firstEmptyIndex = value.length;
    if (firstEmptyIndex < length) {
      inputs.current[firstEmptyIndex]?.focus();
    }
  }, [value, length]);

  const handleChange = (text: string, index: number) => {
    if (isDeleting.current) {
      isDeleting.current = false;
      return;
    }

    const digit = text.slice(-1);
    const nextValue =
      value.substring(0, index) + digit + value.substring(index + 1);
    onChange(nextValue);

    // Move focus to next cell if digit entered
    if (digit && index < length - 1) {
      inputs.current[index + 1]?.focus();
    }
  };

  const handleKeyPress = (
    e: NativeSyntheticEvent<KeyboardEventData>,
    index: number,
  ) => {
    if (e.nativeEvent.key === "Backspace") {
      if (value[index]) {
        // Clear current cell and stay
        isDeleting.current = true;
        const prevValue = value.substring(0, index) + value.substring(index + 1);
        onChange(prevValue);
      } else if (index > 0) {
        // Move to previous cell if current is empty
        inputs.current[index - 1]?.focus();
      }
    }
  };

  const cellBorder = error ? "border-semantic-error" : "border-border-subtle";
  const cellBorderFilled = error ? "border-semantic-error" : "border-brand-primary";

  return (
    <View>
      <View className="flex-row justify-center gap-sm">
        {Array.from({ length }).map((_, idx) => {
          const filled = Boolean(value[idx]);
          return (
            <View
              key={idx}
              className={cn(
                "w-12 h-14 items-center justify-center rounded-md border-2",
                filled ? cellBorderFilled : cellBorder,
                "bg-surface-card",
                disabled && "opacity-40",
              )}
            >
              <TextInput
                ref={(ref) => { inputs.current[idx] = ref; }}
                keyboardType="number-pad"
                maxLength={1}
                value={secureTextEntry && value[idx] ? "•" : (value[idx] ?? "")}
                editable={!disabled}
                onChangeText={(t) => handleChange(t, idx)}
                onKeyPress={(e) => handleKeyPress(e, idx)}
                className="w-full text-center text-lg font-semibold text-ink-primary"
                style={{ height: "100%", paddingTop: 0, paddingBottom: 0 }}
                textAlignVertical="center"
                includeFontPadding={Platform.OS === "android" ? false : undefined}
                accessibilityLabel={`OTP digit ${idx + 1}`}
                selectTextOnFocus
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