import * as ImagePicker from "expo-image-picker";
import { useState } from "react";

import { getApiErrorMessage } from "@/lib/errorHandler";
import type { LocalEvidenceItem, UploadStatus } from "@/types/evidence";

// TODO: wire to registerEvidence() API call once backend evidence endpoint is ready.
// For now, this hook handles local capture and tracks upload state per slot.

interface UseEvidenceUploadReturn {
  items: Record<string, LocalEvidenceItem>;
  pickImage: (slotId: string) => Promise<void>;
  uploadStatus: (slotId: string) => UploadStatus;
  error: string | null;
}

export function useEvidenceUpload(_agreementId: number): UseEvidenceUploadReturn {
  const [items, setItems] = useState<Record<string, LocalEvidenceItem>>({});
  const [error, setError] = useState<string | null>(null);

  const pickImage = async (slotId: string) => {
    setError(null);
    try {
      const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        const camera = await ImagePicker.requestCameraPermissionsAsync();
        if (!camera.granted) {
          setError("Camera and gallery access are required to attach photos.");
          return;
        }
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        quality: 0.75,
        allowsEditing: false,
      });

      if (result.canceled || !result.assets[0]) return;

      const asset = result.assets[0];
      const localItem: LocalEvidenceItem = {
        localId: slotId,
        fileType: "photo",
        localUri: asset.uri,
        uploadStatus: "pending",
      };

      setItems((prev) => ({ ...prev, [slotId]: localItem }));

      // Mark as uploaded optimistically — real upload queued in Phase 5 (sync queue)
      setItems((prev) => ({
        ...prev,
        [slotId]: { ...localItem, uploadStatus: "uploaded" },
      }));
    } catch (err) {
      setError(getApiErrorMessage(err, "Failed to pick image. Please try again."));
    }
  };

  const uploadStatus = (slotId: string): UploadStatus =>
    items[slotId]?.uploadStatus ?? "pending";

  return { items, pickImage, uploadStatus, error };
}
