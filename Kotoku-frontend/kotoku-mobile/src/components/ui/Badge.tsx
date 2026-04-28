// src/components/ui/Badge.tsx
import React from "react";
import { Text, View } from "react-native";

import { cn } from "@/lib/cn";

type BadgeVariant = "default" | "success" | "warning" | "error" | "info" | "sealed" | "draft";

interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
}

// Using bg/text pairs that are available in Tailwind's default palette.
// Semantic tokens only define a single color per state; soft backgrounds
// are intentionally taken from Tailwind's palette here.
const variantClasses: Record<BadgeVariant, string> = {
  default:  "bg-surface-subtle text-ink-secondary",
  success:  "bg-emerald-50 text-emerald-700",
  warning:  "bg-amber-50 text-amber-700",
  error:    "bg-rose-50 text-rose-700",
  info:     "bg-sky-50 text-sky-700",
  sealed:   "bg-blue-50 text-blue-700",
  draft:    "bg-slate-100 text-slate-500",
};

export const Badge: React.FC<BadgeProps> = ({
  label,
  variant = "default",
}) => {
  return (
    <View
      className={cn(
        "flex-row self-start items-center rounded-pill px-sm py-xs",
        variantClasses[variant],
      )}
    >
      <Text className="text-xs font-medium">{label}</Text>
    </View>
  );
};
