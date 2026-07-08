import type { ReactNode } from "react";
import { Modal, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { X, type LucideIcon } from "lucide-react-native";

import { cn } from "@/lib/cn";
import { colors } from "@/theme/tokens";

interface BottomSheetProps {
  visible: boolean;
  onClose: () => void;
  title: string;
  body?: string;
  icon?: LucideIcon;
  footer?: ReactNode;
  children?: ReactNode;
  tone?: "default" | "warning" | "danger" | "success";
}

const toneStyles = {
  default: {
    iconWrap: "bg-brand-primary/10",
    iconColor: colors.brandPrimary,
  },
  warning: {
    iconWrap: "bg-amber-50",
    iconColor: "#d97706",
  },
  danger: {
    iconWrap: "bg-rose-50",
    iconColor: colors.error,
  },
  success: {
    iconWrap: "bg-emerald-50",
    iconColor: colors.success,
  },
} as const;

export function BottomSheet({
  visible,
  onClose,
  title,
  body,
  icon: Icon,
  footer,
  children,
  tone = "default",
}: BottomSheetProps) {
  const insets = useSafeAreaInsets();
  const palette = toneStyles[tone];

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View className="flex-1 justify-end bg-black/45">
        <Pressable className="flex-1" onPress={onClose} />
        <ScrollView
          className="max-h-[82%] rounded-t-3xl bg-surface-canvas"
          contentContainerClassName="px-xl pt-lg gap-lg"
          keyboardShouldPersistTaps="handled"
        >
          <View className="flex-row items-start justify-between gap-md">
            <View className="flex-1 flex-row items-start gap-md">
              {Icon ? (
                <View className={cn("h-11 w-11 items-center justify-center rounded-2xl", palette.iconWrap)}>
                  <Icon size={20} color={palette.iconColor} strokeWidth={1.9} />
                </View>
              ) : null}
              <View className="flex-1 gap-xs">
                <Text className="text-lg font-semibold text-ink-primary">{title}</Text>
                {body ? (
                  <Text className="text-sm leading-relaxed text-ink-secondary">{body}</Text>
                ) : null}
              </View>
            </View>
            <Pressable
              onPress={onClose}
              hitSlop={8}
              className="h-9 w-9 items-center justify-center rounded-full bg-surface-card"
            >
              <X size={18} color={colors.inkMuted} strokeWidth={2} />
            </Pressable>
          </View>

          {children ? <View className="gap-md">{children}</View> : null}
          {footer ? <View className="gap-sm">{footer}</View> : null}
          <View style={{ height: insets.bottom + 8 }} />
        </ScrollView>
      </View>
    </Modal>
  );
}
