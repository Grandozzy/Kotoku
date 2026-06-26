import { AlertCircle, type LucideIcon } from "lucide-react-native";
import { Text, View } from "react-native";

import { Button } from "./button";
import { colors } from "@/theme/tokens";

interface ErrorStateProps {
  title: string;
  body: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: LucideIcon;
}

export function ErrorState({
  title,
  body,
  actionLabel = "Try again",
  onAction,
  icon: Icon = AlertCircle,
}: ErrorStateProps) {
  return (
    <View className="flex-1 items-center justify-center px-2xl py-3xl gap-lg">
      <View className="w-16 h-16 rounded-2xl bg-rose-50 border border-rose-100 items-center justify-center">
        <Icon size={28} color={colors.error} strokeWidth={1.7} />
      </View>
      <View className="items-center gap-sm">
        <Text className="text-lg font-semibold text-ink-primary text-center">
          {title}
        </Text>
        <Text className="text-sm text-ink-secondary text-center leading-relaxed max-w-xs">
          {body}
        </Text>
      </View>
      {onAction && (
        <Button
          title={actionLabel}
          variant="secondary"
          size="md"
          onPress={onAction}
        />
      )}
    </View>
  );
}
