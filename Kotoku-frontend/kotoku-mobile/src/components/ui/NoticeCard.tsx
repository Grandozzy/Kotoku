import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  Info,
  type LucideIcon,
} from "lucide-react-native";
import type { ReactNode } from "react";
import { Text, View } from "react-native";

import { cn } from "@/lib/cn";
import { colors } from "@/theme/tokens";

type NoticeVariant = "info" | "success" | "warning" | "error";

interface NoticeCardProps {
  title?: string;
  body: string;
  variant?: NoticeVariant;
  icon?: LucideIcon;
  footer?: ReactNode;
  compact?: boolean;
}

const VARIANT_STYLES: Record<
  NoticeVariant,
  {
    container: string;
    title: string;
    body: string;
    iconBg: string;
    iconColor: string;
    Icon: LucideIcon;
  }
> = {
  info: {
    container: "bg-blue-50 border-blue-200",
    title: "text-blue-950",
    body: "text-blue-800",
    iconBg: "bg-white/80",
    iconColor: colors.brandPrimary,
    Icon: Info,
  },
  success: {
    container: "bg-emerald-50 border-emerald-200",
    title: "text-emerald-950",
    body: "text-emerald-800",
    iconBg: "bg-white/80",
    iconColor: colors.success,
    Icon: CheckCircle2,
  },
  warning: {
    container: "bg-amber-50 border-amber-200",
    title: "text-amber-950",
    body: "text-amber-800",
    iconBg: "bg-white/80",
    iconColor: "#d97706",
    Icon: Clock3,
  },
  error: {
    container: "bg-rose-50 border-rose-200",
    title: "text-rose-950",
    body: "text-rose-800",
    iconBg: "bg-white/80",
    iconColor: colors.error,
    Icon: AlertCircle,
  },
};

export function NoticeCard({
  title,
  body,
  variant = "info",
  icon,
  footer,
  compact = false,
}: NoticeCardProps) {
  const tone = VARIANT_STYLES[variant];
  const Icon = icon ?? tone.Icon;
  const footerContent =
    typeof footer === "string" || typeof footer === "number" ? (
      <Text className={cn("text-xs leading-relaxed", tone.body)}>{footer}</Text>
    ) : (
      footer
    );

  return (
    <View
      className={cn(
        "rounded-2xl border",
        compact ? "px-md py-md" : "px-lg py-lg",
        tone.container,
      )}
    >
      <View className="flex-row items-start gap-md">
        <View className={cn("mt-0.5 h-10 w-10 items-center justify-center rounded-2xl", tone.iconBg)}>
          <Icon size={18} color={tone.iconColor} strokeWidth={1.9} />
        </View>
        <View className="flex-1 gap-xs">
          {title ? (
            <Text className={cn("text-sm font-semibold", tone.title)}>{title}</Text>
          ) : null}
          <Text className={cn("text-sm leading-relaxed", tone.body)}>{body}</Text>
        </View>
      </View>
      {footerContent ? <View className="mt-md">{footerContent}</View> : null}
    </View>
  );
}
