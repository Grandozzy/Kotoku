import type { Annotation } from "@/api/annotations";
import type { ValidateAgreementResponse } from "@/api/agreements";
import type { listAgreementsPage } from "@/api/agreements";
import type {
  ConsentRecord,
  ConsentStatus,
  RequestOtpResponse,
} from "@/api/consent";
import type { Dispute } from "@/api/disputes";
import type {
  EvidenceItemResponse,
  UploadUrlResponse,
} from "@/api/evidence";
import type { AuditEvent } from "@/api/vault";
import type { Agreement } from "@/types/agreement";
import type { VaultRecord } from "@/types/vault";

const agreement: Agreement = {
  id: 101,
  scenarioId: "used_vehicle_sale",
  title: "Used vehicle sale",
  status: "draft",
  createdAt: "2026-05-19T12:00:00Z",
  sealedAt: null,
  fieldData: {},
  parties: [],
};

const agreementPage: Awaited<ReturnType<typeof listAgreementsPage>> = {
  results: [agreement],
  count: 1,
  next: null,
  previous: null,
};

const validateResult: ValidateAgreementResponse = {
  valid: false,
  errors: [
    {
      code: "missing_required_evidence",
      field: "buyer_id_photo",
      message: "Buyer ID photo is required.",
    },
  ],
};

const consentRecord: ConsentRecord = {
  id: 1,
  partyId: 10,
  partyPhone: "+233501234567",
  channel: "sms",
  granted: false,
  grantedAt: null,
  expiresAt: "2026-05-19T12:10:00Z",
  createdAt: "2026-05-19T12:00:00Z",
};

const requestOtpResult: RequestOtpResponse = {
  consentRecords: [consentRecord],
  partiesCount: 2,
};

const consentStatus: ConsentStatus = {
  agreementId: agreement.id,
  allConsented: false,
  records: [consentRecord],
};

const uploadUrlResult: UploadUrlResponse = {
  evidence_id: 55,
  upload_url: "https://storage.example/upload",
  file_key: "agreements/101/evidence/file.jpg",
  headers: { "Content-Type": "image/jpeg" },
};

const evidenceResult: EvidenceItemResponse = {
  id: 55,
  evidence_type: "buyer_id_photo",
  file_type: "photo",
  mime_type: "image/jpeg",
  size_bytes: 1234,
  original_name: "buyer-id.jpg",
  view_url: "https://storage.example/evidence/file.jpg?response-content-disposition=inline",
  upload_status: "confirmed",
  uploaded_by_role: null,
  created_at: "2026-05-19T12:00:00Z",
};

const vaultRecord: VaultRecord = {
  id: 77,
  agreementId: agreement.id,
  title: agreement.title,
  scenarioId: agreement.scenarioId,
  status: "active",
  agreementStatus: "sealed",
  pdfStatus: "ready",
  pdfUrl: "https://storage.example/agreement.pdf",
  sealedAt: "2026-05-19T12:00:00Z",
  retentionExpiresAt: "2026-06-19T12:00:00Z",
  createdByPhone: "+233501234567",
  parties: [],
};

const auditEvent: AuditEvent = {
  id: "2026-05-19T12:00:00Z-sealed-0",
  eventType: "sealed",
  actorPhone: "",
  createdAt: "2026-05-19T12:00:00Z",
  metadata: { description: "Agreement sealed" },
};

const dispute: Dispute = {
  id: 9,
  agreement_id: agreement.id,
  agreement_type: agreement.scenarioId,
  agreement_sealed_at: "2026-05-19T12:00:00Z",
  raised_by_party_id: consentRecord.partyId,
  raised_by_display_name: "Abena Mensah",
  reason: "Payment was not completed.",
  status: "open",
  resolution: undefined,
  resolved_at: undefined,
  created_at: "2026-05-19T12:00:00Z",
};

const annotation: Annotation = {
  id: 20,
  authorPartyId: consentRecord.partyId,
  authorDisplayName: "Abena Mensah",
  body: "Follow-up note.",
  createdAt: "2026-05-19T12:00:00Z",
};

const checksumUploadArgs: [number, string, string, number, string] = [
  agreement.id,
  evidenceResult.evidence_type,
  evidenceResult.mime_type,
  evidenceResult.size_bytes ?? 1,
  "a".repeat(64),
];

const confirmUploadArgs: [number, string, string, string, string, number] = [
  agreement.id,
  uploadUrlResult.file_key,
  evidenceResult.evidence_type,
  evidenceResult.mime_type,
  checksumUploadArgs[4],
  uploadUrlResult.evidence_id,
];

void agreement;
void agreementPage;
void validateResult;
void requestOtpResult;
void consentStatus;
void evidenceResult;
void vaultRecord;
void auditEvent;
void dispute;
void annotation;
void checksumUploadArgs;
void confirmUploadArgs;

// Compile-time type contract test — no runtime assertions needed.
test("API contract types are consistent", () => {});
