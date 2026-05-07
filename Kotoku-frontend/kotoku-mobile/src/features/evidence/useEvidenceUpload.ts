import * as FileSystem from "expo-file-system";
import * as ImagePicker from "expo-image-picker";
import { useState } from "react";

import {
  confirmUpload,
  getUploadUrl,
} from "@/api/evidence";
import { getApiErrorMessage } from "@/lib/errorHandler";
import type { UploadStatus } from "@/types/evidence";

const MIME_JPEG = "image/jpeg";

async function uploadFileToUrl(fileUri: string, uploadUrl: string, contentType: string): Promise<void> {
  const response = await fetch(fileUri);
  const blob = await response.blob();
  await fetch(uploadUrl, {
    method: "PUT",
    headers: { "Content-Type": contentType },
    body: blob,
  });
}

interface UploadItem {
  slotId: string;
  evidenceType: string;
  localUri: string;
  uploadStatus: UploadStatus;
  remoteId?: number;
  error?: string;
}

interface UseEvidenceUploadReturn {
  items: Record<string, UploadItem>;
  pickImage: (slotId: string, evidenceType: string) => Promise<void>;
  uploadStatus: (slotId: string) => UploadStatus;
  error: string | null;
}

export function useEvidenceUpload(
  agreementId: number,
): UseEvidenceUploadReturn {
  const [items, setItems] = useState<Record<string, UploadItem>>({});
  const [error, setError] = useState<string | null>(null);

  const pickImage = async (slotId: string, evidenceType: string) => {
    setError(null);
    try {
      const permission =
        await ImagePicker.requestMediaLibraryPermissionsAsync();
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

      setItems((prev) => ({
        ...prev,
        [slotId]: {
          slotId,
          evidenceType,
          localUri: asset.uri,
          uploadStatus: "uploading",
        },
      }));

      const fileInfo = await FileSystem.getInfoAsync(asset.uri);
      const sizeBytes = fileInfo.exists && !fileInfo.isDirectory
        ? fileInfo.size
        : 0;

      const uploadUrlRes = await getUploadUrl(
        agreementId,
        evidenceType,
        MIME_JPEG,
        sizeBytes || 1,
      );

      await uploadFileToUrl(asset.uri, uploadUrlRes.upload_url, MIME_JPEG);

      await confirmUpload(
        agreementId,
        uploadUrlRes.file_key,
        evidenceType,
        MIME_JPEG,
      );

      setItems((prev) => ({
        ...prev,
        [slotId]: {
          ...prev[slotId],
          uploadStatus: "uploaded",
          remoteId: uploadUrlRes.evidence_id,
        },
      }));
    } catch (err) {
      const msg = getApiErrorMessage(err, "Failed to upload photo.");
      setError(msg);
      setItems((prev) => {
        if (!prev[slotId]) return prev;
        return {
          ...prev,
          [slotId]: { ...prev[slotId], uploadStatus: "failed", error: msg },
        };
      });
    }
  };

  const uploadStatus = (slotId: string): UploadStatus =>
    items[slotId]?.uploadStatus ?? "pending";

  return { items, pickImage, uploadStatus, error };
}