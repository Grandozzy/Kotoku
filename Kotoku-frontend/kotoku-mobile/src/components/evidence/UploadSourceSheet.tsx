import { Camera, Image as ImageIcon } from "lucide-react-native";
import { Text, View } from "react-native";

import { BottomSheet, Button } from "@/components/ui";

interface UploadSourceSheetProps {
  visible: boolean;
  title: string;
  body: string;
  cameraLabel?: string;
  libraryLabel?: string;
  guidance?: string;
  onClose: () => void;
  onPickCamera: () => void;
  onPickLibrary: () => void;
}

export function UploadSourceSheet({
  visible,
  title,
  body,
  cameraLabel = "Take photo",
  libraryLabel = "Choose from gallery",
  guidance,
  onClose,
  onPickCamera,
  onPickLibrary,
}: UploadSourceSheetProps) {
  return (
    <BottomSheet
      visible={visible}
      onClose={onClose}
      title={title}
      body={body}
      icon={Camera}
    >
      <View className="gap-sm">
        <Button title={cameraLabel} size="lg" onPress={onPickCamera} />
        <Button title={libraryLabel} variant="secondary" size="lg" onPress={onPickLibrary} />
      </View>
      {guidance ? (
        <View className="rounded-2xl bg-surface-subtle p-md">
          <Text className="text-sm leading-relaxed text-ink-secondary">{guidance}</Text>
        </View>
      ) : null}
      <View className="flex-row items-center gap-sm rounded-2xl border border-border-subtle bg-surface-card p-md">
        <View className="h-9 w-9 items-center justify-center rounded-2xl bg-brand-primary/10">
          <ImageIcon size={18} color="#2563EB" strokeWidth={1.8} />
        </View>
        <Text className="flex-1 text-sm leading-relaxed text-ink-secondary">
          Review the image before upload. If the upload or verification fails, replace it with a clearer photo instead of retrying the same poor image.
        </Text>
      </View>
    </BottomSheet>
  );
}
