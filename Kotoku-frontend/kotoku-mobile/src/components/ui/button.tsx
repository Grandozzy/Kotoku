// src/components/ui/Button.tsx
import React from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";

import { cn } from "@/lib/cn";
import { colors } from "@/theme/tokens";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps {
  title: string;
  onPress?: () => void;
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  loading?: boolean;
  fullWidth?: boolean;
  accessibilityLabel?: string;
}

const variantContainer: Record<ButtonVariant, string> = {
  primary: "bg-brand-primary active:opacity-80",
  secondary: "bg-surface-subtle border border-border-subtle active:opacity-80",
  ghost: "bg-transparent active:opacity-60",
};

const variantText: Record<ButtonVariant, string> = {
  primary: "text-white",
  secondary: "text-ink-primary",
  ghost: "text-brand-primary",
};

const sizeContainer: Record<ButtonSize, string> = {
  sm: "px-md py-xs rounded-sm",
  md: "px-lg py-sm rounded-md",
  lg: "px-xl py-md rounded-md",
};

const sizeText: Record<ButtonSize, string> = {
  sm: "text-sm",
  md: "text-md",
  lg: "text-lg",
};

const spinnerColor: Record<ButtonVariant, string> = {
  primary: colors.bgCard,
  secondary: colors.inkPrimary,
  ghost: colors.brandPrimary,
};

export const Button: React.FC<ButtonProps> = ({
  title,
  onPress,
  variant = "primary",
  size = "md",
  disabled,
  loading,
  fullWidth,
  accessibilityLabel,
}) => {
  const isDisabled = disabled || loading;

  return (
    <Pressable
      onPress={isDisabled ? undefined : onPress}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? title}
      accessibilityState={{ disabled: isDisabled }}
      android_ripple={
        variant !== "ghost"
          ? { color: "rgba(0,0,0,0.08)", borderless: false }
          : null
      }
      className={cn(
        "flex-row items-center justify-center",
        variantContainer[variant],
        sizeContainer[size],
        fullWidth && "w-full",
        isDisabled && "opacity-40",
      )}
    >
      {loading && (
        <View className="mr-sm">
          <ActivityIndicator
            size="small"
            color={spinnerColor[variant]}
          />
        </View>
      )}
      <Text
        className={cn(
          "font-semibold",
          sizeText[size],
          variantText[variant],
        )}
      >
        {title}
      </Text>
    </Pressable>
  );
};
