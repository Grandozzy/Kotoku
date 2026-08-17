import { useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { CheckCircle2, ScanFace, ShieldCheck, XCircle } from "lucide-react-native";
import { useRef, useState } from "react";
import { ScrollView, Text, TouchableOpacity, View } from "react-native";

import { createLivenessSession, submitLivenessResult } from "@/api/agreements";
import { LivenessWebView } from "@/components/identity/LivenessWebView";
import { PhotoSlot } from "@/components/evidence/PhotoSlot";
import { UploadSourceSheet } from "@/components/evidence/UploadSourceSheet";
import { Button, NoticeCard, ScreenLoader } from "@/components/ui";
import {
  buildIdentityStatusMessage,
  identityEvidenceType,
  isPartyIdentityComplete,
} from "@/features/agreements/partyIdentity";
import type { Party } from "@/types/agreement";
import { useAgreement } from "@/features/agreements/useAgreementDraft";
import { useEvidenceUpload } from "@/features/evidence/useEvidenceUpload";
import { getApiErrorMessage } from "@/lib/errorHandler";

interface UploadSheetState {
  slotId: string;
  evidenceType: string;
  title: string;
  body: string;
  guidance: string;
}

export default function IdentityInviteStep() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { id, role } = useLocalSearchParams<{ id: string; role: string }>();
  const agreementId = Number(id);

  const { data: agreement, isLoading } = useAgreement(agreementId);
  const { items, pickImage, retryUpload, error: uploadError } = useEvidenceUpload(agreementId);

  const [livenessSession, setLivenessSession] = useState<{ sessionId: string; region: string } | null>(null);
  const [livenessLoading, setLivenessLoading] = useState(false);
  const [livenessError, setLivenessError] = useState<string | null>(null);
  const [uploadSheet, setUploadSheet] = useState<UploadSheetState | null>(null);
  const processingResult = useRef(false);

  if (isLoading || !agreement) {
    return <ScreenLoader />;
  }

  const typedRole = role as Party["role"];
  const party = agreement.parties.find((p) => p.role === typedRole);

  if (!party) {
    return (
      <View className="flex-1 bg-surface-canvas items-center justify-center px-lg gap-xl">
        <Text className="text-xl font-semibold text-ink-primary text-center">
          Identity slot not found
        </Text>
        <Text className="text-sm text-ink-secondary text-center">
          This invite may have been changed. Ask the agreement creator to resend.
        </Text>
      </View>
    );
  }

  const frontType = identityEvidenceType(typedRole, "front");
  const backType = identityEvidenceType(typedRole, "back");
  const frontItem = items[frontType];
  const backItem = items[backType];
  const livenessPassed = party.livenessStatus === "passed";
  const livenessFailed = party.livenessStatus === "failed";
  const complete = isPartyIdentityComplete(party);

  const handleStartLiveness = async () => {
    setLivenessError(null);
    setLivenessLoading(true);
    try {
      const { session_id, region } = await createLivenessSession(agreementId, typedRole);
      setLivenessSession({ sessionId: session_id, region });
    } catch {
      setLivenessError("Could not start face check. Please try again.");
    } finally {
      setLivenessLoading(false);
    }
  };

  const handleLivenessComplete = async () => {
    if (!livenessSession || processingResult.current) return;
    processingResult.current = true;
    setLivenessSession(null);
    try {
      await submitLivenessResult(agreementId, typedRole);
      await queryClient.invalidateQueries({ queryKey: ["agreement", agreementId] });
    } catch {
      setLivenessError("Face check result could not be retrieved. Please try again.");
    } finally {
      processingResult.current = false;
    }
  };

  const handleLivenessError = (message: string) => {
    setLivenessSession(null);
    processingResult.current = false;
    setLivenessError(message);
  };

  const handleSourcePick = async (source: "camera" | "library") => {
    if (!uploadSheet) return;
    const current = uploadSheet;
    setUploadSheet(null);
    await pickImage(current.slotId, current.evidenceType, {
      source,
      cameraType: "back",
    });
  };

  return (
    <>
      <ScrollView
        className="flex-1 bg-surface-canvas"
        contentContainerClassName="px-lg py-xl gap-xl"
        contentContainerStyle={{ paddingBottom: 60 }}
      >
        <View className="gap-md rounded-3xl bg-ink-primary p-lg">
          <View className="flex-row items-start gap-md">
            <View className="h-11 w-11 items-center justify-center rounded-2xl bg-white/10">
              <ShieldCheck size={22} color="#fff" strokeWidth={1.8} />
            </View>
            <View className="flex-1 gap-xs">
              <Text className="text-[11px] font-semibold uppercase tracking-[2px] text-white/60">
                Identity verification
              </Text>
              <Text className="text-xl font-semibold text-white">
                {agreement.title}
              </Text>
              <Text className="text-sm leading-relaxed text-white/75">
                Upload your Ghana Card and complete the face check to confirm your identity as {party.displayName}.
              </Text>
            </View>
          </View>
        </View>

        <View className="gap-md rounded-2xl border border-border-subtle bg-surface-card p-lg">
          <View className="gap-xs">
            <Text className="text-sm font-semibold text-ink-primary">{party.displayName}</Text>
            <Text className="text-xs text-ink-muted">{party.idNumber}</Text>
            <Text
              className={`text-xs ${
                party.identityVerificationStatus === "verified"
                  ? "text-semantic-success"
                  : party.identityVerificationStatus === "failed" ||
                      party.identityVerificationStatus === "manual_review_required"
                    ? "text-semantic-error"
                  : "text-ink-muted"
              }`}
            >
              {buildIdentityStatusMessage(party)}
            </Text>
          </View>

          <View className="flex-row gap-sm">
            <View style={{ flex: 1 }}>
              <PhotoSlot
                label="Ghana Card front"
                required
                localUri={frontItem?.localUri || party.ghanaCardFrontViewUrl || undefined}
                status={frontItem?.uploadStatus || (party.ghanaCardFrontUploaded ? "uploaded" : "pending")}
                error={frontItem?.error}
                failedActionLabel={frontItem?.retryable === false ? "Replace" : "Retry"}
                onPress={() => {
                  if (frontItem?.uploadStatus === "failed" && frontItem.retryable !== false) {
                    void retryUpload(frontType);
                    return;
                  }
                  setUploadSheet({
                    slotId: frontType,
                    evidenceType: frontType,
                    title: "Ghana Card front",
                    body: "Add a clear image of the front of your Ghana Card.",
                    guidance:
                      "Keep all card edges visible, avoid glare, and make sure the PIN and printed details are readable.",
                  });
                }}
              />
            </View>
            <View style={{ flex: 1 }}>
              <PhotoSlot
                label="Ghana Card back"
                required
                localUri={backItem?.localUri || party.ghanaCardBackViewUrl || undefined}
                status={backItem?.uploadStatus || (party.ghanaCardBackUploaded ? "uploaded" : "pending")}
                error={backItem?.error}
                failedActionLabel={backItem?.retryable === false ? "Replace" : "Retry"}
                onPress={() => {
                  if (backItem?.uploadStatus === "failed" && backItem.retryable !== false) {
                    void retryUpload(backType);
                    return;
                  }
                  setUploadSheet({
                    slotId: backType,
                    evidenceType: backType,
                    title: "Ghana Card back",
                    body: "Add a clear image of the back of your Ghana Card.",
                    guidance:
                      "Capture the full card on a flat background and avoid blur, shadows, and cropped corners.",
                  });
                }}
              />
            </View>
          </View>

          <TouchableOpacity
            disabled={livenessLoading || livenessPassed}
            onPress={() => void handleStartLiveness()}
            className={`flex-row items-center gap-sm rounded-xl border p-md ${
              livenessPassed
                ? "border-semantic-success/30 bg-semantic-success/10"
                : livenessFailed
                  ? "border-semantic-error/30 bg-semantic-error/10"
                  : "border-border-subtle bg-surface-card"
            }`}
          >
            <View className="h-10 w-10 items-center justify-center rounded-xl bg-brand-primary/10">
              {livenessPassed ? (
                <CheckCircle2 size={20} color="#16a34a" strokeWidth={1.8} />
              ) : livenessFailed ? (
                <XCircle size={20} color="#dc2626" strokeWidth={1.8} />
              ) : (
                <ScanFace size={20} color="#2563EB" strokeWidth={1.8} />
              )}
            </View>
            <View className="flex-1">
              <Text className="text-sm font-semibold text-ink-primary">
                {livenessPassed
                  ? "Face check passed"
                  : livenessFailed
                    ? "Face check failed — tap to retry"
                    : livenessLoading
                      ? "Starting face check…"
                      : "Start face check"}
              </Text>
              {!livenessPassed && (
                <Text className="text-xs text-ink-muted">
                  {livenessLoading
                    ? "Preparing camera…"
                    : "Follow the on-screen prompts to confirm your identity"}
                </Text>
              )}
            </View>
          </TouchableOpacity>
        </View>

        {livenessError && (
          <NoticeCard variant="error" title="Face check error" body={livenessError} compact />
        )}

        {uploadError && (
          <NoticeCard variant="error" title="Upload needs attention" body={uploadError} compact />
        )}

        {complete && (
          <View className="rounded-2xl border border-semantic-success/30 bg-semantic-success/10 p-lg gap-sm items-center">
            <CheckCircle2 size={32} color="#16a34a" strokeWidth={1.8} />
            <Text className="text-base font-semibold text-semantic-success text-center">
              Identity verified
            </Text>
            <Text className="text-sm text-ink-secondary text-center leading-relaxed">
              Your Ghana Card and face have been verified. The agreement creator will be notified and can proceed.
            </Text>
          </View>
        )}

        {!complete && (
          <Text className="text-xs text-ink-muted text-center">
            Upload your Ghana Card front and back, then complete the face check. Verification runs automatically once all steps are done.
          </Text>
        )}

        <Button
          title={complete ? "Done" : "Back to home"}
          variant={complete ? "primary" : "secondary"}
          size="lg"
          onPress={() => router.replace("/(main)/home" as never)}
        />
      </ScrollView>

      {livenessSession && (
        <LivenessWebView
          sessionId={livenessSession.sessionId}
          region={livenessSession.region}
          onComplete={() => void handleLivenessComplete()}
          onError={handleLivenessError}
          onClose={() => setLivenessSession(null)}
        />
      )}

      <UploadSourceSheet
        visible={Boolean(uploadSheet)}
        onClose={() => setUploadSheet(null)}
        title={uploadSheet?.title ?? "Add photo"}
        body={uploadSheet?.body ?? "Choose how to add this photo."}
        guidance={uploadSheet?.guidance}
        onPickCamera={() => void handleSourcePick("camera")}
        onPickLibrary={() => void handleSourcePick("library")}
      />
    </>
  );
}
