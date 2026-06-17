import * as FileSystem from "expo-file-system/legacy";
import * as ImagePicker from "expo-image-picker";
import { useEffect, useState } from "react";

import { listEvidence } from "@/api/evidence";
import { uploadEvidenceItem } from "@/features/evidence/evidenceUploadService";
import { getApiErrorMessage } from "@/lib/errorHandler";
import type { UploadStatus } from "@/types/evidence";

const MIME_JPEG = "image/jpeg";
const ALLOWED_MIMES = new Set([
  "image/jpeg",
  "image/png",
  "audio/wav",
  "audio/ogg",
  "audio/mpeg",
  "application/pdf",
]);
const BASE64_ALPHABET =
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

function arrayBufferToHex(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function rightRotate(value: number, amount: number): number {
  return (value >>> amount) | (value << (32 - amount));
}

function sha256Bytes(bytes: Uint8Array): ArrayBuffer {
  const constants = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b,
    0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01,
    0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7,
    0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152,
    0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
    0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819,
    0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08,
    0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f,
    0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ];
  const hash = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ];
  const bitLength = bytes.length * 8;
  const paddedLength = Math.ceil((bytes.length + 9) / 64) * 64;
  const padded = new Uint8Array(paddedLength);
  padded.set(bytes);
  padded[bytes.length] = 0x80;

  const view = new DataView(padded.buffer);
  view.setUint32(paddedLength - 4, bitLength, false);

  for (let offset = 0; offset < paddedLength; offset += 64) {
    const words = new Uint32Array(64);
    for (let index = 0; index < 16; index += 1) {
      words[index] = view.getUint32(offset + index * 4, false);
    }
    for (let index = 16; index < 64; index += 1) {
      const s0 =
        rightRotate(words[index - 15], 7) ^
        rightRotate(words[index - 15], 18) ^
        (words[index - 15] >>> 3);
      const s1 =
        rightRotate(words[index - 2], 17) ^
        rightRotate(words[index - 2], 19) ^
        (words[index - 2] >>> 10);
      words[index] = (words[index - 16] + s0 + words[index - 7] + s1) >>> 0;
    }

    let [a, b, c, d, e, f, g, h] = hash;
    for (let index = 0; index < 64; index += 1) {
      const s1 = rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25);
      const ch = (e & f) ^ (~e & g);
      const temp1 = (h + s1 + ch + constants[index] + words[index]) >>> 0;
      const s0 = rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const temp2 = (s0 + maj) >>> 0;
      h = g;
      g = f;
      f = e;
      e = (d + temp1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (temp1 + temp2) >>> 0;
    }

    hash[0] = (hash[0] + a) >>> 0;
    hash[1] = (hash[1] + b) >>> 0;
    hash[2] = (hash[2] + c) >>> 0;
    hash[3] = (hash[3] + d) >>> 0;
    hash[4] = (hash[4] + e) >>> 0;
    hash[5] = (hash[5] + f) >>> 0;
    hash[6] = (hash[6] + g) >>> 0;
    hash[7] = (hash[7] + h) >>> 0;
  }

  const output = new ArrayBuffer(32);
  const outputView = new DataView(output);
  hash.forEach((value, index) => {
    outputView.setUint32(index * 4, value, false);
  });
  return output;
}

function base64ToBytes(base64: string): Uint8Array {
  const cleanBase64 = base64.replace(/[\n\r\s=]/g, "");
  const bytes: number[] = [];

  for (let index = 0; index < cleanBase64.length; index += 4) {
    const chunk =
      (BASE64_ALPHABET.indexOf(cleanBase64[index]) << 18) |
      (BASE64_ALPHABET.indexOf(cleanBase64[index + 1]) << 12) |
      ((BASE64_ALPHABET.indexOf(cleanBase64[index + 2]) & 63) << 6) |
      (BASE64_ALPHABET.indexOf(cleanBase64[index + 3]) & 63);

    bytes.push((chunk >> 16) & 255);
    if (index + 2 < cleanBase64.length) {
      bytes.push((chunk >> 8) & 255);
    }
    if (index + 3 < cleanBase64.length) {
      bytes.push(chunk & 255);
    }
  }

  return new Uint8Array(bytes);
}

async function sha256HexFromUri(uri: string): Promise<string> {
  // blob.arrayBuffer() is not available on Android React Native — read the
  // file via the native FileSystem module and decode from base64 instead.
  const base64 = await FileSystem.readAsStringAsync(uri, {
    encoding: FileSystem.EncodingType.Base64,
  });
  return arrayBufferToHex(sha256Bytes(base64ToBytes(base64)));
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
  error?: string;
}

interface UseEvidenceUploadReturn {
  items: Record<string, UploadItem>;
  pickImage: (slotId: string, evidenceType: string) => Promise<void>;
  retryUpload: (slotId: string) => Promise<void>;
  uploadStatus: (slotId: string) => UploadStatus;
  error: string | null;
}

export function useEvidenceUpload(
  agreementId: number,
): UseEvidenceUploadReturn {
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
    } catch (err) {
      const prefix = `[step:${step}]`;
      const msg = getApiErrorMessage(err, `${prefix} Failed to upload photo.`);
      if (__DEV__) {
        console.error(`[EVIDENCE-${agreementId}] ${prefix}`, err);
      }
      setError(msg);
      setItems((prev) => {
        if (!prev[item.slotId]) return prev;
        return {
          ...prev,
          [item.slotId]: {
            ...prev[item.slotId],
            uploadStatus: "failed",
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
      const checksumSha256 = await sha256HexFromUri(asset.uri);

      // Use the real asset MIME when it's a type the backend accepts; fall back
      // to image/jpeg so the declared type always matches the uploaded bytes.
      const mimeType =
        asset.mimeType && ALLOWED_MIMES.has(asset.mimeType)
          ? asset.mimeType
          : MIME_JPEG;

      step = "getUploadUrl";
      const sizeBytes = asset.fileSize || 1;
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
      const msg = getApiErrorMessage(err, `${prefix} Failed to upload photo.`);
      if (__DEV__) {
        console.error(`[EVIDENCE-${agreementId}] ${prefix}`, err);
      }
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
