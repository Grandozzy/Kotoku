import * as ImagePicker from "expo-image-picker";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { listEvidence } from "@/api/evidence";
import { getEvidenceFileDescriptor } from "@/features/evidence/evidenceFile";
import { uploadEvidenceItem } from "@/features/evidence/evidenceUploadService";
import { getApiErrorCode, getApiErrorMessage } from "@/lib/errorHandler";
import { feedbackSuccess, feedbackWarning } from "@/lib/feedback";
import type { UploadStatus } from "@/types/evidence";

function isNonRetryableEvidenceError(message: string): boolean {
  const normalized = message.toLowerCase();
  return (
    normalized.includes("file size does not match") ||
    normalized.includes("content type does not match") ||
    normalized.includes("checksum does not match") ||
    normalized.includes("mime_type does not match") ||
    normalized.includes("evidence_type does not match")
  );
}

interface UploadItem {
  slotId: string;
  evidenceType: string;
  localUri: string;
  uploadStatus: UploadStatus;
  remoteId?: number;
  mimeType?: string;
  sizeBytes?: number;
  checksumSha256?: string;
  retryable?: boolean;
  error?: string;
}

interface UseEvidenceUploadReturn {
  items: Record<string, UploadItem>;
  pickImage: (
    slotId: string,
    evidenceType: string,
    options?: PickImageOptions,
  ) => Promise<void>;
  retryUpload: (slotId: string) => Promise<void>;
  uploadStatus: (slotId: string) => UploadStatus;
  error: string | null;
}

interface PickImageOptions {
  source?: "library" | "camera";
  cameraType?: "front" | "back";
}

function describeUploadError(error: unknown, fallback: string): string {
  const code = getApiErrorCode(error);
  if (code === "evidence_upload_not_pending") {
    return "The upload session expired or was replaced. Choose the file again and retry.";
  }
  if (code === "evidence_mime_mismatch") {
    return "The uploaded file type did not match the original request. Choose the image again.";
  }
  if (code === "evidence_checksum_mismatch") {
    return "The uploaded file changed before confirmation. Choose the image again.";
  }
  if (code === "evidence_file_size_mismatch") {
    return "The uploaded file size changed before confirmation. Choose the image again.";
  }
  if (code === "identity_role_mismatch") {
    return "This upload slot does not match the selected party. Refresh the draft and try again.";
  }
  const message = getApiErrorMessage(error, fallback);
  if (message.includes("could not be verified in storage")) {
    return "The file reached storage but could not be confirmed yet. Retry in a moment.";
  }
  return message;
}

export function useEvidenceUpload(
  agreementId: number,
): UseEvidenceUploadReturn {
  const queryClient = useQueryClient();
  const [items, setItems] = useState<Record<string, UploadItem>>({});
  const [error, setError] = useState<string | null>(null);

  const uploadItem = async (item: UploadItem) => {
    let step = "getUploadUrl";
    try {
      if (!item.mimeType || !item.sizeBytes || !item.checksumSha256) {
        throw new Error("Please choose the photo again before retrying.");
      }

      const confirmed = await uploadEvidenceItem({
        agreementId,
        evidenceType: item.evidenceType,
        mimeType: item.mimeType,
        fileBlob: await (await fetch(item.localUri)).blob(),
        sizeBytes: item.sizeBytes,
        checksumSha256: item.checksumSha256,
        onPhaseChange: (phase) => {
          step = phase === "uploading" ? "uploadToS3" : "confirmUpload";
          setItems((prev) => ({
            ...prev,
            [item.slotId]: {
              ...prev[item.slotId],
              uploadStatus: phase,
              error: undefined,
            },
          }));
        },
      });

      setItems((prev) => ({
        ...prev,
        [item.slotId]: {
          ...prev[item.slotId],
          localUri:
            confirmed.view_url ?? prev[item.slotId]?.localUri ?? item.localUri,
          uploadStatus: "uploaded",
          remoteId: confirmed.id,
          error: undefined,
        },
      }));
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["agreement", agreementId] }),
        queryClient.invalidateQueries({ queryKey: ["agreements"] }),
      ]);
      feedbackSuccess();
    } catch (err) {
      const prefix = `[step:${step}]`;
      const msg = describeUploadError(err, `${prefix} Failed to upload photo.`);
      const retryable = !isNonRetryableEvidenceError(msg);
      if (__DEV__) {
        console.error(`[EVIDENCE-${agreementId}] ${prefix}`, err);
      }
      feedbackWarning();
      setError(msg);
      setItems((prev) => {
        if (!prev[item.slotId]) return prev;
        return {
          ...prev,
          [item.slotId]: {
            ...prev[item.slotId],
            uploadStatus: "failed",
            retryable,
            error: msg,
          },
        };
      });
    }
  };

  useEffect(() => {
    if (!agreementId) return;
    let cancelled = false;
    (async () => {
      try {
        const evidence = await listEvidence(agreementId);
        if (cancelled) return;
        const hydrated: Record<string, UploadItem> = {};
        for (const item of evidence) {
          const slotId = item.evidence_type;
          hydrated[slotId] = {
            slotId,
            evidenceType: item.evidence_type,
            localUri: item.view_url ?? "",
            uploadStatus: "uploaded",
            remoteId: item.id,
          };
        }
        setItems((prev) => ({ ...hydrated, ...prev }));
      } catch {
        // hydration failure is non-fatal — user can still upload fresh
      }
    })();
    return () => { cancelled = true; };
  }, [agreementId]);

  const pickImage = async (
    slotId: string,
    evidenceType: string,
    options: PickImageOptions = {},
  ) => {
    setError(null);
    let step = "permissions";
    try {
      const source = options.source ?? "library";
      const cameraType = options.cameraType ?? "back";
      if (source === "camera") {
        const camera = await ImagePicker.requestCameraPermissionsAsync();
        if (!camera.granted) {
          setError("Camera access is required to capture a photo.");
          return;
        }
      } else {
        const permission =
          await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!permission.granted) {
          const camera = await ImagePicker.requestCameraPermissionsAsync();
          if (!camera.granted) {
            setError("Camera and gallery access are required to attach photos.");
            return;
          }
        }
      }

      const result =
        source === "camera"
          ? await ImagePicker.launchCameraAsync({
              mediaTypes: ["images"],
              quality: 0.75,
              allowsEditing: false,
              cameraType:
                cameraType === "front"
                  ? ImagePicker.CameraType.front
                  : ImagePicker.CameraType.back,
            })
          : await ImagePicker.launchImageLibraryAsync({
              mediaTypes: ["images"],
              quality: 0.75,
              allowsEditing: false,
            });

      if (result.canceled || !result.assets[0]) return;

      const asset = result.assets[0];
      const { checksumSha256, mimeType, sizeBytes } =
        await getEvidenceFileDescriptor(asset.uri, asset.mimeType);

      step = "getUploadUrl";
      const nextItem: UploadItem = {
        slotId,
        evidenceType,
        localUri: asset.uri,
        uploadStatus: "uploading",
        mimeType,
        sizeBytes,
        checksumSha256,
      };
      setItems((prev) => ({ ...prev, [slotId]: nextItem }));
      await uploadItem(nextItem);
    } catch (err) {
      const prefix = `[step:${step}]`;
      const msg = describeUploadError(err, `${prefix} Failed to upload photo.`);
      const retryable = !isNonRetryableEvidenceError(msg);
      if (__DEV__) {
        console.error(`[EVIDENCE-${agreementId}] ${prefix}`, err);
      }
      feedbackWarning();
      setError(msg);
      setItems((prev) => {
        if (!prev[slotId]) return prev;
        return {
          ...prev,
          [slotId]: {
            ...prev[slotId],
            uploadStatus: "failed",
            retryable,
            error: msg,
          },
        };
      });
    }
  };

  const uploadStatus = (slotId: string): UploadStatus =>
    items[slotId]?.uploadStatus ?? "pending";

  const retryUpload = async (slotId: string) => {
    setError(null);
    const item = items[slotId];
    if (
      !item ||
      item.uploadStatus === "uploading" ||
      item.uploadStatus === "confirming"
    ) {
      return;
    }
    await uploadItem({ ...item, uploadStatus: "uploading" });
  };

  return { items, pickImage, retryUpload, uploadStatus, error };
}
