import * as ImagePicker from "expo-image-picker";
import { useEffect, useState } from "react";

import {
  confirmUpload,
  getUploadUrl,
  listEvidence,
} from "@/api/evidence";
import { getApiErrorMessage } from "@/lib/errorHandler";
import type { UploadStatus } from "@/types/evidence";

const MIME_JPEG = "image/jpeg";

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
            localUri: item.storage_url,
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

  const pickImage = async (slotId: string, evidenceType: string) => {
    setError(null);
    let step = "permissions";
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

      step = "getUploadUrl";
      const sizeBytes = asset.fileSize || 1;
      const uploadUrlRes = await getUploadUrl(
        agreementId,
        evidenceType,
        MIME_JPEG,
        sizeBytes || 1,
      );

      console.log(`[EVIDENCE-${agreementId}] getUploadUrl OK: ${uploadUrlRes.upload_url.slice(0, 100)}`);

      step = "uploadToS3";
      const s3resp = await fetch(uploadUrlRes.upload_url, {
        method: "PUT",
        headers: { "Content-Type": MIME_JPEG },
        body: await (await fetch(asset.uri)).blob(),
      });
      console.log(`[EVIDENCE-${agreementId}] S3 PUT status: ${s3resp.status}`);

      if (!s3resp.ok) {
        const body = await s3resp.text().catch(() => "(no body)");
        throw new Error(`S3 upload failed (${s3resp.status}): ${body}`);
      }

      step = "confirmUpload";
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
      const prefix = `[step:${step}]`;
      const msg = getApiErrorMessage(err, `${prefix} Failed to upload photo.`);
      console.error(`[EVIDENCE-${agreementId}] ${prefix}`, err);
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
