import type { annotationsApi, Annotation } from "@/api/annotations";
import type { agreementsApi, ValidateAgreementResponse } from "@/api/agreements";
import type { consentApi } from "@/api/consent";
import type { disputesApi } from "@/api/disputes";
import type { evidenceApi } from "@/api/evidence";
import type { vaultApi } from "@/api/vault";
import type { Agreement } from "@/types/agreement";
import type { ConsentStatus } from "@/types/consent";
import type { Dispute } from "@/types/dispute";
import type { Party } from "@/types/party";
import type { VaultEntry } from "@/types/vault";

const agreement: Agreement = {
  id: 101,
  title: "Used vehicle sale",
  description: "",
  status: "draft",
  scenario_template: "used_vehicle_sale",
  field_data: {},
  seal_hash: null,
  sealed_at: null,
  closed_at: null,
  created_at: "2026-05-19T12:00:00Z",
  updated_at: "2026-05-19T12:00:00Z",
  parties: [],
};

const agreementListResult: Awaited<ReturnType<typeof agreementsApi.list>> = {
  results: [agreement],
  count: 1,
};

const agreementDetailResult: Awaited<ReturnType<typeof agreementsApi.get>> = agreement;

const agreementCreatePayload: Parameters<typeof agreementsApi.create>[0] = {
  title: "Used vehicle sale",
  scenario_template: "used_vehicle_sale",
};

const validationResult: ValidateAgreementResponse = {
  valid: false,
  errors: [
    {
      code: "missing_required_evidence",
      field: "buyer_id_photo",
      message: "Buyer ID photo is required.",
    },
  ],
};

const consentRecord: ConsentStatus["records"][number] = {
  id: 1,
  party_id: 10,
  party_phone: "+233501234567",
  channel: "sms",
  granted: false,
  granted_at: null,
  expires_at: "2026-05-19T12:10:00Z",
  created_at: "2026-05-19T12:00:00Z",
};

const consentRequestResult: Awaited<ReturnType<typeof consentApi.requestOtps>> = {
  consent_records: [consentRecord],
  parties_count: 2,
};

const consentConfirmResult: Awaited<ReturnType<typeof consentApi.confirm>> = {
  consent_record: { ...consentRecord, granted: true, granted_at: "2026-05-19T12:05:00Z" },
};

const consentStatusResult: Awaited<ReturnType<typeof consentApi.status>> = {
  agreement_id: 101,
  all_consented: false,
  records: [consentRecord],
};

const uploadUrlPayload: Parameters<typeof evidenceApi.requestUploadUrl>[1] = {
  evidence_type: "buyer_id_photo",
  mime_type: "image/jpeg",
  size_bytes: 1234,
  checksum_sha256: "a".repeat(64),
};

const uploadUrlResult: Awaited<ReturnType<typeof evidenceApi.requestUploadUrl>> = {
  evidence_id: 55,
  upload_url: "https://storage.example/upload",
  file_key: "agreements/101/evidence/file.jpg",
  headers: { "Content-Type": "image/jpeg" },
};

const confirmEvidencePayload: Parameters<typeof evidenceApi.confirm>[1] = {
  file_key: uploadUrlResult.file_key,
  evidence_type: uploadUrlPayload.evidence_type,
  mime_type: uploadUrlPayload.mime_type,
  checksum_sha256: uploadUrlPayload.checksum_sha256,
};

const confirmEvidenceResult: Awaited<ReturnType<typeof evidenceApi.confirm>> = {
  evidence: {
    id: 55,
    evidence_type: uploadUrlPayload.evidence_type,
    file_type: "photo",
    mime_type: uploadUrlPayload.mime_type,
    size_bytes: uploadUrlPayload.size_bytes,
    view_url: "https://storage.example/evidence/file.jpg",
    upload_status: "confirmed",
    uploaded_by_role: null,
    created_at: "2026-05-19T12:00:00Z",
  },
};

const party: Party = {
  id: 10,
  role: "buyer",
  full_name: "Abena Mensah",
  phone: "+233501234567",
  id_type: "ghana_card",
  id_number: "GHA-123456789-0",
  created_at: "2026-05-19T12:00:00Z",
  updated_at: "2026-05-19T12:00:00Z",
};

const vaultEntry: VaultEntry = {
  id: 77,
  agreement: 101,
  title: "Used vehicle sale",
  status: "sealed",
  seal_hash: "abc123",
  sealed_at: "2026-05-19T12:00:00Z",
  created_by_phone: "+233501234567",
  pdf_status: "ready",
  pdf_url: "https://storage.example/agreement.pdf",
  retain_until: "2026-06-19T12:00:00Z",
  archived: false,
  created_at: "2026-05-19T12:00:00Z",
};

const vaultListResult: Awaited<ReturnType<typeof vaultApi.list>> = {
  results: [vaultEntry],
  count: 1,
  next: null,
  previous: null,
};

const vaultDetailResult: Awaited<ReturnType<typeof vaultApi.get>> = vaultEntry;
const vaultExportResult: Awaited<ReturnType<typeof vaultApi.requestExport>> = vaultEntry;
const vaultRetryResult: Awaited<ReturnType<typeof vaultApi.retryExport>> = vaultEntry;

const dispute: Dispute = {
  id: 9,
  raised_by_party_id: party.id,
  raised_by_display_name: party.full_name,
  reason: "Payment was not completed.",
  status: "open",
  resolution: null,
  resolved_at: null,
  created_at: "2026-05-19T12:00:00Z",
  updated_at: "2026-05-19T12:00:00Z",
};

const disputeListResult: Awaited<ReturnType<typeof disputesApi.list>> = [dispute];
const disputeCreatePayload: Parameters<typeof disputesApi.create>[1] = {
  reason: dispute.reason,
};
const disputeCreateResult: Awaited<ReturnType<typeof disputesApi.create>> = dispute;

const annotation: Annotation = {
  id: 20,
  authorPartyId: party.id,
  authorDisplayName: party.full_name,
  body: "Follow-up note.",
  createdAt: "2026-05-19T12:00:00Z",
};

const annotationListResult: Awaited<ReturnType<typeof annotationsApi.list>> = [annotation];
const annotationCreateResult: Awaited<ReturnType<typeof annotationsApi.create>> = annotation;

void agreementListResult;
void agreementDetailResult;
void agreementCreatePayload;
void validationResult;
void consentRequestResult;
void consentConfirmResult;
void consentStatusResult;
void uploadUrlPayload;
void confirmEvidencePayload;
void confirmEvidenceResult;
void vaultListResult;
void vaultDetailResult;
void vaultExportResult;
void vaultRetryResult;
void disputeListResult;
void disputeCreatePayload;
void disputeCreateResult;
void annotationListResult;
void annotationCreateResult;

// This file is a compile-time type contract test — no runtime assertions needed.
test("API contract types are consistent", () => {});
