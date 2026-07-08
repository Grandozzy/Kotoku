import { Camera, CheckCircle, ImagePlus, RefreshCw } from "lucide-react-native";
import { ActivityIndicator, Image, Pressable, Text, View } from "react-native";

import { colors } from "@/theme/tokens";
import type { UploadStatus } from "@/types/evidence";

interface PhotoSlotProps {
  label: string;
  required: boolean;
  localUri?: string;
  status?: UploadStatus;
  error?: string;
  failedActionLabel?: string;
  onPress: () => void;
}

export function PhotoSlot({
  label,
  required,
  localUri,
  status = "pending",
  error,
  failedActionLabel = "Retry",
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
          ? failedActionLabel
          : null;
  const footerLabel = failed ? failedActionLabel : filled ? "Tap to replace" : "Tap to add";

  return (
    <Pressable
      onPress={onPress}
      disabled={busy}
      accessibilityRole="button"
      accessibilityLabel={`${failed ? failedActionLabel : filled ? "Replace" : "Add"} ${label}`}
      accessibilityState={{ disabled: busy, busy }}
      className={[
        "overflow-hidden rounded-2xl border-2 bg-surface-card",
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
          <View className="absolute inset-x-0 bottom-0 bg-ink-primary/55 px-sm py-xs">
            <View className="flex-row items-center justify-between gap-sm">
              <Text className="flex-1 text-[11px] font-semibold text-white" numberOfLines={1}>
                {label}
              </Text>
              <Text className="text-[10px] text-white/80">{footerLabel}</Text>
            </View>
          </View>
          <View className="absolute right-xs top-xs rounded-full bg-brand-primary p-xs">
            <CheckCircle size={14} color={colors.bgCard} />
          </View>
        </View>
      ) : (
        <View className="flex-1 items-center justify-center gap-sm bg-surface-subtle px-sm">
          <View className="h-12 w-12 items-center justify-center rounded-2xl bg-white">
            <ImagePlus size={24} color={colors.inkMuted} strokeWidth={1.6} />
          </View>
          <Text className="text-center text-xs font-semibold text-ink-primary" numberOfLines={2}>
            {label}
            {required && <Text className="text-semantic-error"> *</Text>}
          </Text>
          <Text className="text-center text-[11px] text-ink-muted">
            {footerLabel}
          </Text>
        </View>
      )}
      {(busy || failed) && (
        <View className="absolute inset-0 items-center justify-center bg-ink-primary/60 px-sm">
          {busy ? (
            <ActivityIndicator color={colors.bgCard} />
          ) : (
            <RefreshCw size={18} color={colors.bgCard} strokeWidth={2} />
          )}
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
