import { Camera, CheckCircle } from "lucide-react-native";
import { ActivityIndicator, Image, Pressable, Text, View } from "react-native";

import { colors } from "@/theme/tokens";
import type { UploadStatus } from "@/types/evidence";

interface PhotoSlotProps {
  label: string;
  required: boolean;
  localUri?: string;
  status?: UploadStatus;
  error?: string;
  onPress: () => void;
}

export function PhotoSlot({
  label,
  required,
  localUri,
  status = "pending",
  error,
  onPress,
}: PhotoSlotProps) {
  const filled = Boolean(localUri);
  const busy = status === "uploading" || status === "confirming";
  const failed = status === "failed";
  const statusLabel =
    status === "uploading"
      ? "Uploading"
      : status === "confirming"
        ? "Confirming"
        : failed
          ? "Retry"
          : null;

  return (
    <Pressable
      onPress={onPress}
      disabled={busy}
      className={[
        "rounded-lg border-2 overflow-hidden",
        failed
          ? "border-semantic-error"
          : filled
            ? "border-brand-primary"
            : "border-dashed border-border-strong",
      ].join(" ")}
      style={{ aspectRatio: 4 / 3 }}
    >
      {filled ? (
        <View className="flex-1">
          <Image
            source={{ uri: localUri, cache: "force-cache" }}
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
      {(busy || failed) && (
        <View className="absolute inset-0 items-center justify-center bg-ink-primary/60 px-sm">
          {busy && <ActivityIndicator color={colors.bgCard} />}
          <Text
            className="text-xs text-white font-semibold text-center mt-xs"
            numberOfLines={2}
          >
            {statusLabel}
          </Text>
          {failed && error && (
            <Text
              className="text-[10px] text-white/90 text-center mt-xs"
              numberOfLines={2}
            >
              {error}
            </Text>
          )}
        </View>
      )}
    </Pressable>
  );
}
