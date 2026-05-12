import { LucideIcon } from "lucide-react-native";
import { Text, View } from "react-native";

import { Button } from "./button";
import { colors } from "@/theme/tokens";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  body: string;
  action?: {
    label: string;
    onPress: () => void;
  };
}

export function EmptyState({ icon: Icon, title, body, action }: EmptyStateProps) {
  return (
    <View className="flex-1 items-center justify-center px-2xl py-3xl gap-lg">
      <View className="w-16 h-16 rounded-2xl bg-brand-primary/10 items-center justify-center">
        <Icon size={28} color={colors.brandPrimary} strokeWidth={1.6} />
      </View>
      <View className="items-center gap-sm">
        <Text className="text-lg font-semibold text-ink-primary text-center">
          {title}
        </Text>
        <Text className="text-sm text-ink-secondary text-center leading-relaxed max-w-xs">
          {body}
        </Text>
      </View>
      {action && (
        <Button
          title={action.label}
          variant="primary"
          size="md"
          onPress={action.onPress}
        />
      )}
    </View>
  );
}
