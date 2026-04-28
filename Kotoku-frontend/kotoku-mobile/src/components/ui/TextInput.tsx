// src/components/ui/TextInput.tsx
import React from "react";
import {
  TextInput as RNTextInput,
  TextInputProps,
  Text,
  View,
} from "react-native";

import { cn } from "@/lib/cn";

interface Props extends TextInputProps {
  label?: string;
  error?: string;
  hint?: string;
  required?: boolean;
}

export const TextInput: React.FC<Props> = ({
  label,
  error,
  hint,
  required,
  editable = true,
  className,
  ...rest
}) => {
  const borderClass = error
    ? "border-semantic-error"
    : "border-border-subtle focus:border-brand-primary";

  return (
    <View className="w-full">
      {label && (
        <View className="flex-row mb-xs">
          <Text className="text-sm font-medium text-ink-secondary">
            {label}
          </Text>
          {required && (
            <Text className="text-sm text-semantic-error ml-xs">*</Text>
          )}
        </View>
      )}

      <RNTextInput
        editable={editable}
        className={cn(
          "w-full rounded-md border px-md py-sm text-md text-ink-primary bg-surface-card",
          borderClass,
          !editable && "opacity-40 bg-surface-subtle",
          className,
        )}
        placeholderTextColor="#94A3B8"
        {...rest}
      />

      {error && (
        <Text className="mt-xs text-xs text-semantic-error">{error}</Text>
      )}
      {!error && hint && (
        <Text className="mt-xs text-xs text-ink-muted">{hint}</Text>
      )}
    </View>
  );
};
