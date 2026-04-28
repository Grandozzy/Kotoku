// src/components/ui/Card.tsx
import React from "react";
import { View, ViewProps } from "react-native";

import { cn } from "@/lib/cn";
import { shadow } from "@/theme/tokens";

type ShadowLevel = "none" | "sm" | "md" | "lg";

interface CardProps extends ViewProps {
  elevation?: ShadowLevel;
  padded?: boolean;
}

const shadowStyle: Record<ShadowLevel, object> = {
  none: {},
  sm: shadow.sm,
  md: shadow.md,
  lg: shadow.lg,
};

export const Card: React.FC<CardProps> = ({
  children,
  elevation = "sm",
  padded = true,
  className,
  style,
  ...rest
}) => {
  return (
    <View
      className={cn(
        "bg-surface-card rounded-lg",
        padded && "p-lg",
        className,
      )}
      style={[shadowStyle[elevation], style]}
      {...rest}
    >
      {children}
    </View>
  );
};
