import { Camera, CheckCircle } from "lucide-react-native";
import { Image, Pressable, Text, View } from "react-native";

import { colors } from "@/theme/tokens";

interface PhotoSlotProps {
  label: string;
  required: boolean;
  localUri?: string;
  onPress: () => void;
}

export function PhotoSlot({ label, required, localUri, onPress }: PhotoSlotProps) {
  const filled = Boolean(localUri);

  return (
    <Pressable
      onPress={onPress}
      className={[
        "rounded-lg border-2 overflow-hidden",
        filled ? "border-brand-primary" : "border-dashed border-border-strong",
      ].join(" ")}
      style={{ aspectRatio: 4 / 3 }}
    >
      {filled ? (
        <View className="flex-1">
          <Image
            source={{ uri: localUri }}
            className="flex-1"
            resizeMode="cover"
          />
          {/* Filled overlay badge */}
          <View className="absolute bottom-xs right-xs bg-brand-primary rounded-pill p-xs">
            <CheckCircle size={14} color={colors.bgCard} />
          </View>
        </View>
      ) : (
        <View className="flex-1 items-center justify-center gap-sm bg-surface-subtle">
          <Camera size={28} color={colors.inkMuted} strokeWidth={1.5} />
          <Text className="text-xs text-ink-muted text-center px-sm" numberOfLines={2}>
            {label}
            {required && (
              <Text className="text-semantic-error"> *</Text>
            )}
          </Text>
        </View>
      )}
    </Pressable>
  );
}
