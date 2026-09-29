import { CameraView, type CameraCapturedPicture } from "expo-camera";
import { RotateCcw, X } from "lucide-react-native";
import { useRef, useState } from "react";
import { ActivityIndicator, Image, Modal, Pressable, Text, View } from "react-native";

import { colors } from "@/theme/tokens";

interface Props {
  visible: boolean;
  side: "front" | "back";
  onClose: () => void;
  onUsePhoto: (photo: CameraCapturedPicture) => Promise<void>;
}

export function GhanaCardCamera({ visible, side, onClose, onUsePhoto }: Props) {
  const cameraRef = useRef<CameraView>(null);
  const [photo, setPhoto] = useState<CameraCapturedPicture | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const close = () => {
    if (busy) return;
    setPhoto(null);
    setError(null);
    onClose();
  };

  const capture = async () => {
    if (!cameraRef.current || busy) return;
    setBusy(true);
    setError(null);
    try {
      const next = await cameraRef.current.takePictureAsync({ quality: 0.9 });
      if (!next || Math.min(next.width, next.height) < 1000) {
        setError("The photo resolution is too low. Move closer and retake it.");
        return;
      }
      setPhoto(next);
    } catch {
      setError("The photo could not be captured. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const usePhoto = async () => {
    if (!photo || busy) return;
    setBusy(true);
    setError(null);
    try {
      await onUsePhoto(photo);
      setPhoto(null);
      onClose();
    } catch {
      setError("The photo could not be prepared. Please retake it.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="fullScreen" onRequestClose={close}>
      <View className="flex-1 bg-black">
        {photo ? (
          <Image source={{ uri: photo.uri }} className="absolute inset-0 h-full w-full" resizeMode="contain" />
        ) : (
          <CameraView ref={cameraRef} style={{ flex: 1 }} facing="back" mode="picture" />
        )}

        <View pointerEvents="none" className="absolute inset-0 items-center justify-center px-lg">
          <View
            className="w-full rounded-2xl border-[3px] border-white"
            style={{ aspectRatio: 85.6 / 53.98 }}
          />
        </View>

        <View className="absolute inset-x-0 top-0 bg-black/65 px-lg pb-lg pt-14">
          <Text className="text-center text-lg font-semibold text-white">
            Align Ghana Card {side}
          </Text>
          <Text className="mt-xs text-center text-sm text-white/80">
            Keep all four edges inside the frame. Avoid glare, blur and shadows.
          </Text>
        </View>

        <Pressable
          onPress={close}
          disabled={busy}
          accessibilityRole="button"
          accessibilityLabel="Close camera"
          className="absolute left-md top-14 h-11 w-11 items-center justify-center rounded-full bg-black/60"
        >
          <X size={22} color="#fff" />
        </Pressable>

        <View className="absolute inset-x-0 bottom-0 items-center bg-black/70 px-lg pb-10 pt-lg">
          {error && <Text className="mb-md text-center text-sm text-red-200">{error}</Text>}
          {busy ? (
            <ActivityIndicator color="#fff" size="large" />
          ) : photo ? (
            <View className="w-full flex-row gap-md">
              <Pressable
                onPress={() => setPhoto(null)}
                className="h-14 flex-1 flex-row items-center justify-center gap-sm rounded-2xl border border-white/40"
              >
                <RotateCcw size={18} color="#fff" />
                <Text className="font-semibold text-white">Retake</Text>
              </Pressable>
              <Pressable
                onPress={() => void usePhoto()}
                className="h-14 flex-1 items-center justify-center rounded-2xl bg-white"
              >
                <Text className="font-semibold text-ink-primary">Use photo</Text>
              </Pressable>
            </View>
          ) : (
            <Pressable
              onPress={() => void capture()}
              accessibilityRole="button"
              accessibilityLabel={`Capture Ghana Card ${side}`}
              className="h-20 w-20 items-center justify-center rounded-full border-4 border-white"
            >
              <View className="h-16 w-16 rounded-full" style={{ backgroundColor: colors.bgCard }} />
            </Pressable>
          )}
        </View>
      </View>
    </Modal>
  );
}
