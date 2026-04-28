export type EvidenceFileType = "photo" | "document" | "signature" | "voice_note";

export type UploadStatus = "pending" | "uploading" | "uploaded" | "failed";

export interface EvidenceItem {
  id: number;
  agreementId: number;
  fileType: EvidenceFileType;
  originalName: string;
  storageUrl: string;
  uploadedAt: string;
}

export interface LocalEvidenceItem {
  localId: string;
  fileType: EvidenceFileType;
  localUri: string;
  uploadStatus: UploadStatus;
  remoteId?: number;
}
